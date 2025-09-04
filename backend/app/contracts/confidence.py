"""
Confidence calculation contracts and interfaces.

This module defines the contracts for the 3-tier confidence system,
ensuring consistent confidence calculation across all extraction strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
import logging

class ConfidenceTier(Enum):
    """Three-tier confidence classification system."""
    HIGH = "high"      # 0.8 - 1.0: Reliable extraction, minimal human review needed
    MEDIUM = "medium"  # 0.5 - 0.79: Moderate confidence, some human review recommended
    LOW = "low"        # 0.0 - 0.49: Low confidence, significant human review required

class ConfidenceThresholds:
    """Standard confidence thresholds for the 3-tier system."""
    
    HIGH_THRESHOLD = 0.8    # Minimum for HIGH tier
    MEDIUM_THRESHOLD = 0.5  # Minimum for MEDIUM tier
    LOW_THRESHOLD = 0.0     # Minimum for LOW tier
    
    @classmethod
    def get_tier(cls, confidence: float) -> ConfidenceTier:
        """Determine confidence tier based on confidence score."""
        if confidence >= cls.HIGH_THRESHOLD:
            return ConfidenceTier.HIGH
        elif confidence >= cls.MEDIUM_THRESHOLD:
            return ConfidenceTier.MEDIUM
        else:
            return ConfidenceTier.LOW

class FieldConfidence:
    """Confidence information for a specific field."""
    
    def __init__(self, 
                 value: Any,
                 confidence: float,
                 strategy: str,
                 metadata: Optional[Dict[str, Any]] = None):
        self.value = value
        self.confidence = confidence
        self.strategy = strategy
        self.metadata = metadata or {}
        self.tier = ConfidenceThresholds.get_tier(confidence)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'value': self.value,
            'confidence': self.confidence,
            'tier': self.tier.value,
            'strategy': self.strategy,
            'metadata': self.metadata
        }

class ConfidenceCalculator(ABC):
    """
    Contract for confidence calculation operations.
    
    All confidence calculation implementations must follow this interface
    to ensure consistent confidence scoring across the system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def calculate_field_confidence(self, 
                                       field_data: Dict[str, Any],
                                       context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate confidence score for a single field.
        
        Args:
            field_data: Field data including value, strategy, and metadata
            context: Optional context information (e.g., field type, restaurant_id)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    async def calculate_overall_confidence(self, 
                                         field_confidences: Dict[str, float],
                                         context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate overall confidence score from multiple field confidences.
        
        Args:
            field_confidences: Dictionary mapping field names to confidence scores
            context: Optional context information
            
        Returns:
            Overall confidence score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    async def calculate_agreement_confidence(self, 
                                           strategy_results: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate confidence boost when multiple strategies agree on a field.
        
        Args:
            strategy_results: List of results from different strategies
            
        Returns:
            Tuple of (agreement_confidence, agreement_details)
        """
        pass
    
    @abstractmethod
    async def get_confidence_metadata(self, 
                                    field_name: str, 
                                    confidence: float) -> Dict[str, Any]:
        """Get metadata explaining the confidence calculation."""
        pass

class ConfidenceValidator(ABC):
    """
    Contract for confidence validation operations.
    
    Ensures confidence scores are valid and within expected ranges.
    """
    
    @abstractmethod
    async def validate_confidence(self, confidence: float) -> bool:
        """Validate that confidence score is within valid range (0.0 - 1.0)."""
        pass
    
    @abstractmethod
    async def validate_field_confidences(self, 
                                       field_confidences: Dict[str, float]) -> Dict[str, bool]:
        """Validate confidence scores for multiple fields."""
        pass
    
    @abstractmethod
    async def get_validation_errors(self, 
                                   field_confidences: Dict[str, float]) -> List[str]:
        """Get list of validation errors for field confidences."""
        pass

class ConfidenceAdjuster(ABC):
    """
    Contract for confidence adjustment operations.
    
    Defines how confidence scores should be adjusted based on various factors.
    """
    
    @abstractmethod
    async def adjust_for_strategy(self, 
                                 confidence: float, 
                                 strategy: str) -> float:
        """Adjust confidence based on extraction strategy."""
        pass
    
    @abstractmethod
    async def adjust_for_field_type(self, 
                                   confidence: float, 
                                   field_type: str) -> float:
        """Adjust confidence based on field type."""
        pass
    
    @abstractmethod
    async def adjust_for_context(self, 
                                confidence: float, 
                                context: Dict[str, Any]) -> float:
        """Adjust confidence based on extraction context."""
        pass
    
    @abstractmethod
    async def apply_confidence_boosters(self, 
                                       confidence: float, 
                                       boosters: List[str]) -> float:
        """Apply confidence boosters (e.g., multiple strategy agreement)."""
        pass

class ConfidenceThresholdManager(ABC):
    """
    Contract for managing confidence thresholds.
    
    Allows dynamic adjustment of confidence thresholds based on
    performance metrics and user preferences.
    """
    
    @abstractmethod
    async def get_thresholds(self, 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get current confidence thresholds for the given context."""
        pass
    
    @abstractmethod
    async def update_thresholds(self, 
                               thresholds: Dict[str, float], 
                               context: Optional[Dict[str, Any]] = None) -> None:
        """Update confidence thresholds."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self, 
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get performance metrics for current threshold settings."""
        pass
    
    @abstractmethod
    async def suggest_threshold_adjustments(self, 
                                          performance_metrics: Dict[str, Any]) -> Dict[str, float]:
        """Suggest threshold adjustments based on performance metrics."""
        pass
