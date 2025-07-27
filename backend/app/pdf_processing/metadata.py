"""
PDF metadata extraction module for extracting and processing document metadata.
"""

import fitz  # PyMuPDF
from typing import Dict, Any, Optional, List
import re
from datetime import datetime
import logging
import os

from .exceptions import MetadataExtractionError

logger = logging.getLogger(__name__)

class PDFMetadataExtractor:
    """Extract metadata from PDF files."""
    
    def _open_pdf(self, pdf_path: str) -> fitz.Document:
        """Open PDF file and return document object."""
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
    
    def _extract_content_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract content-related metadata from PDF."""
        has_images = False
        has_text = False
        # Table and form detection not implemented, default to False
        has_tables = False
        has_forms = False
        
        for page in doc:
            if page.get_images():
                has_images = True
            if page.get_text():
                has_text = True
        
        return {
            'has_text': has_text,
            'has_images': has_images,
            'has_tables': has_tables,
            'has_forms': has_forms
        }
    
    def _parse_pdf_date(self, date_str: str) -> datetime:
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
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
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
            metadata.update(self._extract_content_metadata(doc))
            return metadata
        except Exception as e:
            raise MetadataExtractionError(f"Failed to extract metadata: {str(e)}")
    
    def _get_permissions(self, doc: fitz.Document) -> Dict[str, bool]:
        """Get PDF permissions."""
        return {
            'print': doc.permissions & 0x4 != 0,
            'copy': doc.permissions & 0x10 != 0,
            'edit': doc.permissions & 0x8 != 0,
            'annotate': doc.permissions & 0x20 != 0,
            'form_fill': doc.permissions & 0x100 != 0,
            'extract': doc.permissions & 0x200 != 0,
            'assemble': doc.permissions & 0x400 != 0,
            'print_high': doc.permissions & 0x800 != 0
        }
    
    def _detect_compression(self, doc: fitz.Document) -> List[str]:
        """Detect compression methods used in PDF."""
        compression = []
        for page in doc:
            if page.is_compressed:
                compression.append('page')
            if page.is_compressed_xref:
                compression.append('xref')
            if page.is_compressed_obj:
                compression.append('object')
        return list(set(compression))
    
    def _has_images(self, doc: fitz.Document) -> bool:
        """Check if PDF contains images."""
        for page in doc:
            if page.get_images():
                return True
        return False
    
    def _has_tables(self, doc: fitz.Document) -> bool:
        """Check if PDF contains tables."""
        # This is a simplified check - in reality, you'd need more sophisticated table detection
        return False
    
    def _has_forms(self, doc: fitz.Document) -> bool:
        """Check if PDF contains forms."""
        return bool(doc.get_form_fields())
    
    def _has_links(self, doc: fitz.Document) -> bool:
        """Check if PDF contains links."""
        for page in doc:
            if page.get_links():
                return True
        return False
    
    def _has_annotations(self, doc: fitz.Document) -> bool:
        """Check if PDF contains annotations."""
        for page in doc:
            if page.annots():
                return True
        return False
    
    def _is_scanned(self, doc: fitz.Document) -> bool:
        """Check if PDF is scanned."""
        # This is a simplified check - in reality, you'd need more sophisticated detection
        return False
    
    def _estimate_content_pages(self, doc: fitz.Document) -> int:
        """Estimate number of content pages (excluding blank pages)."""
        content_pages = 0
        for page in doc:
            text = page.get_text()
            if text.strip():
                content_pages += 1
        return content_pages 