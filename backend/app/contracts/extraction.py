"""
Extraction strategy contracts and interfaces.

This module defines the contracts for all extraction strategies,
ensuring consistent behavior across different extraction methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import logging

class ExtractionStrategy(Enum):
    """Enumeration of available extraction strategies."""
    DATABASE = "database"
    NER = "ner"
    REGEX = "regex"
    AI = "ai"
    HYBRID = "hybrid"

class ExtractionResult:
    """Standardized result structure for extraction operations."""
    
    def __init__(self, 
                 fields: Dict[str, Any],
                 confidence: float,
                 strategy: ExtractionStrategy,
                 metadata: Optional[Dict[str, Any]] = None):
        self.fields = fields
        self.confidence = confidence
        self.strategy = strategy
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            'fields': self.fields,
            'confidence': self.confidence,
            'strategy': self.strategy.value,
            'metadata': self.metadata
        }

class FieldExtractor(ABC):
    """
    Contract for field extraction strategies.
    
    All extraction strategies must implement this interface to ensure
    consistent behavior and result formatting.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strategy_type: ExtractionStrategy = None
    
    @abstractmethod
    async def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """
        Extract fields from text using the specific strategy.
        
        Args:
            text: Input text to extract fields from
            context: Optional context information (e.g., restaurant_id, wine_list_format)
            
        Returns:
            ExtractionResult with extracted fields and confidence scores
        """
        pass
    
    @abstractmethod
    async def get_supported_fields(self) -> List[str]:
        """Get list of field names this strategy can extract."""
        pass
    
    @abstractmethod
    async def get_strategy_metadata(self) -> Dict[str, Any]:
        """Get metadata about the extraction strategy."""
        pass
    
    @abstractmethod
    async def validate_input(self, text: str) -> bool:
        """Validate input text before extraction."""
        pass

class TextProcessor(ABC):
    """
    Contract for text processing operations.
    
    Defines how text should be processed before and after extraction.
    """
    
    @abstractmethod
    async def preprocess(self, text: str) -> str:
        """Preprocess text before extraction."""
        pass
    
    @abstractmethod
    async def postprocess(self, text: str) -> str:
        """Postprocess text after extraction."""
        pass
    
    @abstractmethod
    async def normalize(self, text: str) -> str:
        """Normalize text to standard format."""
        pass

class ExtractionPipeline(ABC):
    """
    Contract for extraction pipeline orchestration.
    
    Defines how multiple extraction strategies should be combined
    and how results should be merged.
    """
    
    @abstractmethod
    async def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[ExtractionResult]:
        """
        Process text through multiple extraction strategies.
        
        Args:
            text: Input text to process
            context: Optional context information
            
        Returns:
            List of ExtractionResult from different strategies
        """
        pass
    
    @abstractmethod
    async def merge_results(self, results: List[ExtractionResult]) -> ExtractionResult:
        """
        Merge multiple extraction results into a single result.
        
        Args:
            results: List of extraction results to merge
            
        Returns:
            Merged ExtractionResult
        """
        pass
    
    @abstractmethod
    async def get_pipeline_config(self) -> Dict[str, Any]:
        """Get current pipeline configuration."""
        pass
    
    @abstractmethod
    async def update_pipeline_config(self, config: Dict[str, Any]) -> None:
        """Update pipeline configuration."""
        pass

class StrategySelector(ABC):
    """
    Contract for strategy selection logic.
    
    Defines how the system chooses which extraction strategies
    to use for different types of content.
    """
    
    @abstractmethod
    async def select_strategies(self, 
                               text: str, 
                               context: Optional[Dict[str, Any]] = None) -> List[ExtractionStrategy]:
        """
        Select appropriate extraction strategies for the given text and context.
        
        Args:
            text: Input text to analyze
            context: Optional context information
            
        Returns:
            List of ExtractionStrategy to use
        """
        pass
    
    @abstractmethod
    async def get_strategy_priority(self, strategy: ExtractionStrategy) -> float:
        """Get priority score for a strategy (higher = more preferred)."""
        pass
    
    @abstractmethod
    async def update_strategy_weights(self, weights: Dict[ExtractionStrategy, float]) -> None:
        """Update strategy selection weights based on performance."""
        pass
