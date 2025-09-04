"""
Contracts exports for easy access from the main app level.

This file provides convenient access to all contracts without
needing to import from the contracts package directly.
"""

# Re-export all contracts for easy access
from .contracts import *

# Convenience imports for commonly used contracts
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
