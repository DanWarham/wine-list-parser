"""
Custom exceptions for PDF processing operations.
"""

class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass

class PDFExtractionError(PDFProcessingError):
    """Raised when there's an error during PDF text extraction."""
    pass

class OCRProcessingError(PDFProcessingError):
    """Raised when there's an error during OCR processing."""
    pass

class MetadataExtractionError(PDFProcessingError):
    """Raised when there's an error extracting PDF metadata."""
    pass

class PreprocessingError(PDFProcessingError):
    """Raised when there's an error during text preprocessing."""
    pass 