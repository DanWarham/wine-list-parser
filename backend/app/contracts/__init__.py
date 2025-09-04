"""
Contracts package for the wine list parser application.

This package provides the core interfaces and contracts that ensure
consistent behavior across all application components.
"""

# Base contracts
from .base import (
    BaseService,
    ServiceFactory,
    DataProcessor,
    Configurable,
    Auditable
)

# Extraction contracts
from .extraction import (
    ExtractionStrategy,
    ExtractionResult,
    FieldExtractor,
    TextProcessor as ExtractionTextProcessor,
    ExtractionPipeline,
    StrategySelector
)

# Confidence contracts
from .confidence import (
    ConfidenceTier,
    ConfidenceThresholds,
    FieldConfidence,
    ConfidenceCalculator,
    ConfidenceValidator,
    ConfidenceAdjuster,
    ConfidenceThresholdManager
)

# Processing contracts
from .processing import (
    ProcessingStage,
    ProcessingStatus,
    ProcessingResult,
    PDFProcessor,
    TextProcessor,
    ProcessingPipeline,
    ProcessingMonitor,
    ProcessingConfig
)

# Re-export commonly used types
__all__ = [
    # Base contracts
    'BaseService',
    'ServiceFactory', 
    'DataProcessor',
    'Configurable',
    'Auditable',
    
    # Extraction contracts
    'ExtractionStrategy',
    'ExtractionResult',
    'FieldExtractor',
    'ExtractionTextProcessor',
    'ExtractionPipeline',
    'StrategySelector',
    
    # Confidence contracts
    'ConfidenceTier',
    'ConfidenceThresholds',
    'FieldConfidence',
    'ConfidenceCalculator',
    'ConfidenceValidator',
    'ConfidenceAdjuster',
    'ConfidenceThresholdManager',
    
    # Processing contracts
    'ProcessingStage',
    'ProcessingStatus',
    'ProcessingResult',
    'PDFProcessor',
    'TextProcessor',
    'ProcessingPipeline',
    'ProcessingMonitor',
    'ProcessingConfig'
]
