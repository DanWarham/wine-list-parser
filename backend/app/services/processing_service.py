"""
Processing Service for handling PDF file operations and wine list extraction.
This service consolidates all PDF processing logic to eliminate duplication.
"""

import logging
import tempfile
import os
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.pdf_processing.extractor import PDFExtractor, ExtractionConfig, ExtractionStrategy
from app.pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
from app.pdf_processing.metadata import PDFMetadataExtractor
from app.pdf_processing.categorizer import PDFBlockCategorizer
from app.pdf_processing.header_associator import HeaderWineAssociator
from app.fieldextractor.fieldextractor import FieldExtractor
from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline
from app.contracts.processing import PDFProcessor, ProcessingResult
from app.exceptions import PDFProcessingError
from app.models import UploadFile

logger = logging.getLogger(__name__)


class ProcessingService(BaseService, PDFProcessor):
    """Service for handling PDF processing operations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.extractor = PDFExtractor()
        self.preprocessor = PDFPreprocessor()
        self.metadata_extractor = PDFMetadataExtractor()
        self.field_extractor = FieldExtractor()
        # Pipeline now constructed per-restaurant inside processing call where needed
    
    async def process_pdf_file(self, file: UploadFile, restaurant_id: str, 
                              extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a PDF file and extract wine entries."""
        try:
            # Save uploaded file temporarily
            temp_file_path = await self._save_uploaded_file(file)
            
            try:
                # Process the PDF
                wine_entries, processing_data = await self._process_pdf(
                    temp_file_path, restaurant_id, extraction_config
                )
                
                return {
                    'wine_entries': wine_entries,
                    'processing_data': processing_data,
                    'success': True
                }
                
            finally:
                # Cleanup temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Failed to process PDF file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process PDF file: {str(e)}"
            )
    
    async def _save_uploaded_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary location."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        return temp_file.name
    
    async def _process_pdf(self, file_path: str, restaurant_id: str, 
                          extraction_config: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict], Dict]:
        """Process PDF file and extract wine entries."""
        try:
            # Configure extraction
            config = extraction_config or {}
            extraction_config = ExtractionConfig(
                strategy=config.get('strategy', ExtractionStrategy.HYBRID),
                confidence_threshold=config.get('confidence_threshold', 0.7)
            )
            
            # Extract text blocks first
            text_blocks = self.extractor.extract_text_blocks(file_path)
            
            # Preprocess extracted text
            preprocessing_config = PreprocessingConfig()
            preprocessed_blocks = self.preprocessor.preprocess(text_blocks)
            
            # Categorize text blocks
            categorizer = PDFBlockCategorizer()
            categorized_blocks = categorizer.categorize(preprocessed_blocks)
            
            # Analyze wine list structure with header association
            header_associator = HeaderWineAssociator()
            structure_analysis = header_associator.analyze_wine_list_structure(categorized_blocks)
            
            # Extract metadata
            metadata = self.metadata_extractor.extract_metadata(file_path)
            
            # Process through hybrid pipeline (per-restaurant instance)
            hybrid_pipeline = HybridExtractionPipeline(restaurant_id=restaurant_id)
            wine_entries = hybrid_pipeline.process_wine_list(preprocessed_blocks)
            if isinstance(wine_entries, dict) and 'extraction_results' in wine_entries:
                wine_entries_list = wine_entries['extraction_results']
            else:
                wine_entries_list = wine_entries
            
            # Enhance wine entries with header association
            enhanced_wine_entries = self._enhance_wine_entries_with_headers(
                wine_entries_list, structure_analysis
            )
            
            processing_data = {
                'metadata': metadata,
                'structure_analysis': structure_analysis,
                'steps_status': {
                    'preprocessing': 'completed',
                    'extraction': 'completed',
                    'categorization': 'completed',
                    'header_association': 'completed',
                    'processing': 'completed'
                },
                'extraction_stats': {
                    'total_blocks': len(text_blocks),
                    'categorized_blocks': len(categorized_blocks),
                    'headers_found': len(structure_analysis.get('headers', [])),
                    'wine_entries_found': len(enhanced_wine_entries),
                    'wines_with_headers': structure_analysis.get('summary', {}).get('wines_with_headers', 0)
                }
            }
            
            return enhanced_wine_entries, processing_data
            
        except PDFProcessingError as e:
            logger.error(f"PDF processing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during PDF processing: {e}")
            raise PDFProcessingError(f"Failed to process PDF: {e}")
    
    def _enhance_wine_entries_with_headers(self, wine_entries: List[Dict], 
                                          structure_analysis: Dict[str, Any]) -> List[Dict]:
        """Enhance wine entries with header association information."""
        headers = structure_analysis.get('headers', [])
        header_map = {h.get('text', ''): h for h in headers}
        
        enhanced_entries = []
        for entry in wine_entries:
            enhanced_entry = entry.copy()
            
            # Find associated header based on text similarity or position
            associated_header = self._find_associated_header(entry, headers)
            if associated_header:
                enhanced_entry['associated_header'] = {
                    'text': associated_header.get('text'),
                    'type': associated_header.get('header_type'),
                    'level': associated_header.get('level'),
                    'confidence': associated_header.get('confidence')
                }
            
            enhanced_entries.append(enhanced_entry)
        
        return enhanced_entries
    
    def _find_associated_header(self, wine_entry: Dict, headers: List[Dict]) -> Optional[Dict]:
        """Find the most likely associated header for a wine entry."""
        wine_text = wine_entry.get('text', '').lower()
        
        # Look for headers that appear before this wine entry
        # This is a simplified approach - in practice, you'd use position data
        for header in headers:
            header_text = header.get('text', '').lower()
            
            # Check if header text appears in wine text (indicating region/type match)
            if header_text in wine_text:
                return header
            
            # Check for common wine-producing regions
            wine_regions = ['burgundy', 'bordeaux', 'champagne', 'alsace', 'loire', 'rhone',
                           'tuscany', 'piedmont', 'veneto', 'rioja', 'ribera', 'priorat',
                           'napa', 'sonoma', 'oregon', 'washington', 'barossa', 'mclaren']
            
            for region in wine_regions:
                if region in header_text and region in wine_text:
                    return header
        
        return None
    
    async def extract_metadata_only(self, file: UploadFile) -> Dict[str, Any]:
        """Extract only metadata from PDF file without processing content."""
        try:
            temp_file_path = await self._save_uploaded_file(file)
            
            try:
                metadata = self.metadata_extractor.extract_metadata(temp_file_path)
                return {
                    'metadata': metadata,
                    'success': True
                }
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract metadata: {str(e)}"
            )
    
    async def validate_pdf_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate PDF file format and basic structure."""
        try:
            temp_file_path = await self._save_uploaded_file(file)
            
            try:
                # Basic validation
                if not file.filename.lower().endswith('.pdf'):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File must be a PDF"
                    )
                
                # Check file size (max 50MB)
                file_size = os.path.getsize(temp_file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File size must be less than 50MB"
                    )
                
                # Try to extract basic metadata to validate PDF structure
                metadata = self.metadata_extractor.extract_metadata(temp_file_path)
                
                return {
                    'valid': True,
                    'file_size': file_size,
                    'metadata': metadata,
                    'message': 'PDF file is valid'
                }
                
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to validate PDF file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to validate PDF file: {str(e)}"
            )

    # Implement PDFProcessor contract methods
    async def process_pdf(self, file_path: str, config: Optional[Dict[str, Any]] = None) -> ProcessingResult:  # type: ignore[override]
        try:
            # Preprocess/extract as per our pipeline but without restaurant context
            text_blocks = self.extractor.extract_text_blocks(file_path)
            preprocessing_config = PreprocessingConfig()
            preprocessed_blocks = self.preprocessor.preprocess(text_blocks)
            metadata = self.metadata_extractor.extract_metadata(file_path)
            return ProcessingResult(success=True, data={
                'text_blocks': preprocessed_blocks,
            }, metadata=metadata)
        except Exception as e:
            logger.error(f"process_pdf error: {e}")
            return ProcessingResult(success=False, errors=[str(e)])

    async def extract_text(self, file_path: str, config: Optional[Dict[str, Any]] = None) -> str:  # type: ignore[override]
        # Flatten blocks to text for this contract method
        blocks = self.extractor.extract_text_blocks(file_path)
        pages = []
        for page in blocks:
            lines = [line.get('text', '') for line in page if isinstance(line, dict)]
            pages.append('\n'.join(lines))
        return '\n\n'.join(pages)

    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:  # type: ignore[override]
        return self.metadata_extractor.extract_metadata(file_path)

    async def validate_pdf(self, file_path: str) -> bool:  # type: ignore[override]
        try:
            _ = self.metadata_extractor.extract_metadata(file_path)
            return True
        except Exception:
            return False
