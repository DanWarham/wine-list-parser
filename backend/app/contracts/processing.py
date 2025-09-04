"""
Processing pipeline contracts and interfaces.

This module defines the contracts for PDF processing, text processing,
and the overall processing pipeline orchestration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
import logging
from pathlib import Path

class ProcessingStage(Enum):
    """Enumeration of processing pipeline stages."""
    UPLOAD = "upload"
    PROCESSING = "processing"
    EXTRACTION = "extraction"
    PREPROCESSING = "preprocessing"
    METADATA_EXTRACTION = "metadata_extraction"
    TEXT_PROCESSING = "text_processing"
    FIELD_EXTRACTION = "field_extraction"
    VALIDATION = "validation"
    STORAGE = "storage"
    COMPLETED = "completed"
    # Setup workflow specific stages
    SETUP_INIT = "setup_init"
    RESTAURANT_CONFIG = "restaurant_config"
    RULESET_CONFIG = "ruleset_config"
    WINE_LIST_UPLOAD = "wine_list_upload"
    QUALITY_ASSESSMENT = "quality_assessment"
    OPTIMIZATION = "optimization"

class ProcessingStatus(Enum):
    """Enumeration of processing status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProcessingResult:
    """Standardized result structure for processing operations."""
    
    def __init__(self, 
                 success: bool,
                 data: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 errors: Optional[List[str]] = None,
                 warnings: Optional[List[str]] = None):
        self.success = success
        self.data = data or {}
        self.metadata = metadata or {}
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            'success': self.success,
            'data': self.data,
            'metadata': self.metadata,
            'errors': self.errors,
            'warnings': self.warnings
        }

class PDFProcessor(ABC):
    """
    Contract for PDF processing operations.
    
    Defines how PDF files should be processed, including text extraction,
    metadata extraction, and preprocessing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process_pdf(self, 
                         file_path: Union[str, Path], 
                         config: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process a PDF file and extract text and metadata.
        
        Args:
            file_path: Path to the PDF file
            config: Optional processing configuration
            
        Returns:
            ProcessingResult with extracted text and metadata
        """
        pass
    
    @abstractmethod
    async def extract_text(self, 
                          file_path: Union[str, Path], 
                          config: Optional[Dict[str, Any]] = None) -> str:
        """Extract text content from PDF."""
        pass
    
    @abstractmethod
    async def extract_metadata(self, 
                              file_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        pass
    
    @abstractmethod
    async def validate_pdf(self, 
                          file_path: Union[str, Path]) -> bool:
        """Validate that the file is a valid PDF."""
        pass

class TextProcessor(ABC):
    """
    Contract for text processing operations.
    
    Defines how extracted text should be processed, cleaned, and normalized
    before field extraction.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def preprocess(self, 
                        text: str, 
                        config: Optional[Dict[str, Any]] = None) -> str:
        """
        Preprocess text before extraction.
        
        Args:
            text: Raw extracted text
            config: Optional preprocessing configuration
            
        Returns:
            Preprocessed text
        """
        pass
    
    @abstractmethod
    async def segment_text(self, 
                          text: str, 
                          config: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Segment text into processable blocks.
        
        Args:
            text: Preprocessed text
            config: Optional segmentation configuration
            
        Returns:
            List of text segments
        """
        pass
    
    @abstractmethod
    async def clean_text(self, 
                        text: str, 
                        config: Optional[Dict[str, Any]] = None) -> str:
        """Clean and normalize text."""
        pass
    
    @abstractmethod
    async def detect_language(self, 
                             text: str) -> str:
        """Detect the language of the text."""
        pass

class ProcessingPipeline(ABC):
    """
    Contract for processing pipeline orchestration.
    
    Defines how the entire processing workflow should be orchestrated,
    from PDF upload to final field extraction.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stages: List[ProcessingStage] = []
    
    @abstractmethod
    async def process(self, 
                     input_data: Dict[str, Any], 
                     config: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Execute the complete processing pipeline.
        
        Args:
            input_data: Input data for processing
            config: Optional pipeline configuration
            
        Returns:
            ProcessingResult with final results
        """
        pass
    
    @abstractmethod
    async def add_stage(self, 
                        stage: ProcessingStage, 
                        processor: Any) -> None:
        """Add a processing stage to the pipeline."""
        pass
    
    @abstractmethod
    async def remove_stage(self, 
                          stage: ProcessingStage) -> None:
        """Remove a processing stage from the pipeline."""
        pass
    
    @abstractmethod
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and configuration."""
        pass
    
    @abstractmethod
    async def validate_pipeline(self) -> bool:
        """Validate that the pipeline is properly configured."""
        pass

class ProcessingMonitor(ABC):
    """
    Contract for processing monitoring operations.
    
    Defines how processing progress should be tracked and reported.
    """
    
    @abstractmethod
    async def start_monitoring(self, 
                              process_id: str) -> None:
        """Start monitoring a processing operation."""
        pass
    
    @abstractmethod
    async def update_progress(self, 
                             process_id: str, 
                             stage: ProcessingStage, 
                             progress: float) -> None:
        """Update processing progress for a stage."""
        pass
    
    @abstractmethod
    async def log_event(self, 
                        process_id: str, 
                        event: str, 
                        details: Optional[Dict[str, Any]] = None) -> None:
        """Log a processing event."""
        pass
    
    @abstractmethod
    async def get_progress(self, 
                          process_id: str) -> Dict[str, Any]:
        """Get current progress for a processing operation."""
        pass
    
    @abstractmethod
    async def stop_monitoring(self, 
                             process_id: str) -> None:
        """Stop monitoring a processing operation."""
        pass

class ProcessingConfig(ABC):
    """
    Contract for processing configuration management.
    
    Defines how processing configurations should be managed and validated.
    """
    
    @abstractmethod
    async def get_config(self, 
                         config_type: str, 
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get configuration for a specific processing type."""
        pass
    
    @abstractmethod
    async def update_config(self, 
                           config_type: str, 
                           config: Dict[str, Any], 
                           context: Optional[Dict[str, Any]] = None) -> None:
        """Update configuration for a specific processing type."""
        pass
    
    @abstractmethod
    async def validate_config(self, 
                             config: Dict[str, Any]) -> bool:
        """Validate a processing configuration."""
        pass
    
    @abstractmethod
    async def get_default_config(self, 
                                config_type: str) -> Dict[str, Any]:
        """Get default configuration for a processing type."""
        pass
