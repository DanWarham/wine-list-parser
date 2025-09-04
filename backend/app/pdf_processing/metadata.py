"""
PDF metadata extraction module.
"""

import fitz  # PyMuPDF
from typing import Dict, Any, Optional
from datetime import datetime
import os
import logging

from .exceptions import MetadataExtractionError

logger = logging.getLogger(__name__)

class PDFMetadataExtractor:
    """Extracts basic metadata from PDF files."""
    
    def _open_pdf(self, pdf_path: str) -> fitz.Document:
        """Open PDF file."""
        try:
            return fitz.open(pdf_path)
        except Exception as e:
            raise MetadataExtractionError(f"Failed to open PDF: {str(e)}")
    
    def _extract_basic_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract basic metadata from PDF."""
        metadata = {}
        for key in ['title', 'author', 'subject', 'keywords', 'creator', 'producer']:
            metadata[key] = doc.metadata.get(key, '')
        return metadata
    
    def _extract_technical_metadata(self, doc: fitz.Document, pdf_path: str) -> Dict[str, Any]:
        """Extract technical metadata from PDF."""
        return {
            'page_count': len(doc),
            'file_size': os.path.getsize(pdf_path),
            'creation_date': self._parse_pdf_date(doc.metadata.get('creationDate')),
            'modification_date': self._parse_pdf_date(doc.metadata.get('modDate'))
        }
    
    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse PDF date string to datetime object."""
        if not date_str or not date_str.startswith('D:'):
            return None
            
        try:
            # Remove 'D:' prefix and parse
            date_str = date_str[2:]
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(date_str[8:10])
            minute = int(date_str[10:12])
            second = int(date_str[12:14])
            
            return datetime(year, month, day, hour, minute, second)
        except (ValueError, IndexError):
            return None
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing extracted metadata

        Raises:
            MetadataExtractionError: If metadata extraction fails
        """
        try:
            doc = self._open_pdf(pdf_path)
            metadata = self._extract_basic_metadata(doc)
            metadata.update(self._extract_technical_metadata(doc, pdf_path))
            return metadata
        except Exception as e:
            raise MetadataExtractionError(f"Failed to extract metadata: {str(e)}") 