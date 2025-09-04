"""
PDF text extraction module with support for multiple extraction strategies.
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import logging
import re
from datetime import datetime
import os

from .exceptions import PDFExtractionError, OCRProcessingError

logger = logging.getLogger(__name__)

logger.info("[PDFExtractor] Module loaded.")

class ExtractionStrategy(Enum):
    """Available strategies for PDF text extraction."""
    TEXT = "text"  # Direct text extraction
    OCR = "ocr"    # OCR-based extraction
    HYBRID = "hybrid"  # Try text first, fallback to OCR

@dataclass
class ExtractionConfig:
    """Configuration for PDF extraction."""
    strategy: ExtractionStrategy = ExtractionStrategy.HYBRID
    dpi: int = 300
    ocr_lang: str = "eng+fra"
    min_confidence: float = 0.5

class PDFExtractor:
    """Handles PDF text extraction with support for multiple strategies."""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        logger.info("[PDFExtractor] __init__ called.")
        self.config = config or ExtractionConfig()
    
    def extract_text_blocks(self, pdf_path: str) -> List[List[Dict[str, Any]]]:
        """Extract text blocks from PDF pages."""
        logger.info(f"[PDFExtractor] Processing {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            pages = []
            
            # Extract text from pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_lines = self._extract_page(page, page_num)
                pages.append(page_lines)
            
            logger.info(f"[PDFExtractor] Completed processing {pdf_path} - {len(doc)} pages")
            
            return pages
            
        except Exception as e:
            logger.error(f"[PDFExtractor] Exception in extract_text_blocks: {e}")
            raise PDFExtractionError(f"Failed to extract PDF text: {str(e)}")
    
    def _extract_page(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        if self.config.strategy in [ExtractionStrategy.TEXT, ExtractionStrategy.HYBRID]:
            try:
                blocks = page.get_text("blocks")
                if blocks and any(block[4].strip() for block in blocks):
                    result = self._process_text_blocks(blocks, page_num)
                    return result
            except Exception as e:
                logger.warning(f"Text extraction failed for page {page_num + 1}: {str(e)}")
                
        if self.config.strategy in [ExtractionStrategy.OCR, ExtractionStrategy.HYBRID]:
            try:
                result = self._extract_with_ocr(page, page_num)
                return result
            except Exception as e:
                raise OCRProcessingError(f"OCR failed for page {page_num + 1}: {str(e)}")
                
        return []
    
    def _process_text_blocks(self, blocks: List[tuple], page_num: int) -> List[Dict[str, Any]]:
        """Process text blocks from direct text extraction."""
        page_lines = []
        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            if text.strip():
                page_lines.append({
                    "text": text.strip(),
                    "bbox": [x0, y0, x1, y1],
                    "page": page_num + 1,
                    "source": "text",
                    "confidence": 1.0
                })
        return page_lines
    
    def _extract_with_ocr(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        pix = page.get_pixmap(dpi=self.config.dpi)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        
        # Get OCR data with confidence scores
        ocr_data = pytesseract.image_to_data(
            img, 
            lang=self.config.ocr_lang,
            output_type=pytesseract.Output.DICT
        )
        
        page_lines = []
        for i in range(len(ocr_data['text'])):
            if ocr_data['text'][i].strip():
                confidence = float(ocr_data['conf'][i]) / 100.0
                if confidence >= self.config.min_confidence:
                    page_lines.append({
                        "text": ocr_data['text'][i].strip(),
                        "bbox": [
                            ocr_data['left'][i],
                            ocr_data['top'][i],
                            ocr_data['left'][i] + ocr_data['width'][i],
                            ocr_data['top'][i] + ocr_data['height'][i]
                        ],
                        "page": page_num + 1,
                        "source": "ocr",
                        "confidence": confidence
                    })
        return page_lines 