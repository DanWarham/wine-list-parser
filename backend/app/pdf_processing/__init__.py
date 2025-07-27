"""
PDF Processing Module

This module handles all PDF-related operations including extraction, preprocessing,
and text analysis. It provides a modular and extensible pipeline for processing
PDF documents with support for both text-based and OCR-based extraction.
"""

from .extractor import PDFExtractor, ExtractionStrategy
from .preprocessor import PDFPreprocessor
from .metadata import PDFMetadataExtractor
from .exceptions import PDFProcessingError

__all__ = [
    'PDFExtractor',
    'ExtractionStrategy',
    'PDFPreprocessor',
    'PDFMetadataExtractor',
    'PDFProcessingError'
] 