"""
PDF text preprocessing module for cleaning and normalizing extracted text.
"""

import re
from typing import List, Dict, Any, Optional, Union
import logging
from dataclasses import dataclass
import unicodedata

from .exceptions import PreprocessingError

logger = logging.getLogger(__name__)

logger.info("[PDFPreprocessor] Module loaded.")

@dataclass
class PreprocessingConfig:
    """Configuration for text preprocessing."""
    remove_headers: bool = False
    remove_footers: bool = True
    normalize_whitespace: bool = True
    remove_special_chars: bool = False
    normalize_unicode: bool = True
    min_line_length: int = 3
    max_line_length: int = 1000

class PDFPreprocessor:
    """Handles preprocessing of extracted PDF text."""
    
    def __init__(self, config: Optional[PreprocessingConfig] = None):
        logger.info("[PDFPreprocessor] __init__ called.")
        self.config = config or PreprocessingConfig()
    
    def preprocess(self, extracted_data: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """Preprocess extracted text data."""
        logger.info("[PDFPreprocessor] Starting preprocessing")
        
        processed_pages = []
        for page_num, page_lines in enumerate(extracted_data):
            processed_page = self._preprocess_page(page_lines, page_num)
            processed_pages.append(processed_page)
        
        logger.info(f"[PDFPreprocessor] Completed preprocessing - {len(processed_pages)} pages")
        return processed_pages
    
    def _preprocess_page(self, page_lines: List[Dict[str, Any]], page_num: int) -> List[Dict[str, Any]]:
        """Preprocess a single page."""
        processed_lines = []
        for line in page_lines:
            processed_line = self._preprocess_text(line)
            if processed_line:
                processed_lines.append(processed_line)
        return processed_lines
    
    def _preprocess_text(self, line: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Preprocess a single text line."""
        text = line.get('text', '')
        if not text.strip():
            return None
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            return None
        
        # Update the line with cleaned text
        line['text'] = cleaned_text
        return line
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
            
        # Normalize unicode
        if self.config.normalize_unicode:
            text = unicodedata.normalize('NFKC', text)
        
        # Remove special characters
        if self.config.remove_special_chars:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
        
        # Check line length
        if len(text) <= self.config.min_line_length or len(text) >= self.config.max_line_length:
            return ""
            
        return text
    
    def _remove_headers_footers(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove headers and footers from page blocks."""
        if not blocks:
            return blocks
            
        # Calculate page height
        page_height = max(block['bbox'][3] for block in blocks)
        
        # Define header and footer regions (top and bottom 10% of page)
        header_threshold = page_height * 0.1
        footer_threshold = page_height * 0.9
        
        filtered_blocks = []
        for block in blocks:
            y_pos = block['bbox'][1]
            
            # Skip if in header region and headers should be removed
            if self.config.remove_headers and y_pos < header_threshold:
                continue
                
            # Skip if in footer region and footers should be removed
            if self.config.remove_footers and y_pos > footer_threshold:
                continue
                
            filtered_blocks.append(block)
            
        return filtered_blocks 