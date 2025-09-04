"""
Confidence Calculator Module

This module provides improved confidence calculation methods for better arbitration
decisions across different extraction strategies and field types.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Integrate with contracts
from app.contracts import (
    ConfidenceCalculator as ContractConfidenceCalculator,
    ConfidenceTier,
    ConfidenceThresholds,
)

logger = logging.getLogger(__name__)

@dataclass
class ConfidenceFactors:
    """Factors that influence confidence calculation."""
    base_confidence: float = 0.0
    field_type_boost: float = 0.0
    strategy_boost: float = 0.0
    validation_boost: float = 0.0
    agreement_boost: float = 0.0
    context_boost: float = 0.0
    quality_penalty: float = 0.0

class ConfidenceCalculator(ContractConfidenceCalculator):
    """Advanced confidence calculator for wine field extraction."""
    
    def __init__(self):
        super().__init__()
        # Field-specific confidence weights
        self.field_weights = {
            'vintage': 1.2,      # High importance, well-defined patterns
            'price': 1.1,        # High importance, numeric validation
            'producer_name': 1.0, # Standard importance
            'wine_name': 0.9,    # Variable importance
            'region': 1.1,       # High importance, database validation
            'country': 1.0,      # Standard importance
            'grape_variety': 0.9, # Variable importance
            'designation': 0.8,  # Lower importance
            'bottle_size': 0.7,  # Lower importance
            'type': 0.8,         # Lower importance
            'sub_region': 0.9    # Variable importance
        }
        
        # Strategy-specific confidence adjustments
        self.strategy_adjustments = {
            'database': 1.2,     # Database matches are highly reliable
            'regex': 1.0,        # Standard reliability
            'ner': 0.9,          # NER can be less reliable
            'ai': 0.8,           # AI is fallback, lower confidence
            'rule': 1.1,         # Rules are reliable when well-defined
            'pattern': 0.95      # Pattern matching is moderately reliable
        }
        
        # Validation confidence boosts
        self.validation_boosts = {
            'format_validation': 0.1,
            'range_validation': 0.15,
            'database_validation': 0.2,
            'ner_validation': 0.1,
            'cross_strategy_agreement': 0.15
        }
    
    # Sync helper used across the codebase
    def calculate_field_confidence_sync(self, 
                                 field_name: str, 
                                 value: str, 
                                 strategy: str, 
                                 base_confidence: float,
                                 validation_results: Optional[Dict[str, Any]] = None,
                                 context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate comprehensive confidence for a field extraction (sync).
        """
        factors = ConfidenceFactors(base_confidence=base_confidence)
        
        # Apply field type boost
        field_weight = self.field_weights.get(field_name, 1.0)
        factors.field_type_boost = (field_weight - 1.0) * 0.1
        
        # Apply strategy boost
        strategy_adjustment = self.strategy_adjustments.get(strategy, 1.0)
        factors.strategy_boost = (strategy_adjustment - 1.0) * 0.1
        
        # Apply validation boosts
        if validation_results:
            factors.validation_boost = self._calculate_validation_boost(validation_results)
        
        # Apply context boost
        if context:
            factors.context_boost = self._calculate_context_boost(field_name, value, context)
        
        # Apply quality penalty
        factors.quality_penalty = self._calculate_quality_penalty(field_name, value)
        
        # Calculate final confidence
        final_confidence = (
            factors.base_confidence +
            factors.field_type_boost +
            factors.strategy_boost +
            factors.validation_boost +
            factors.context_boost -
            factors.quality_penalty
        )
        
        # Ensure confidence is within bounds
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        logger.debug(
            f"Confidence calculation for {field_name}: base={factors.base_confidence:.3f}, "
            f"field_boost={factors.field_type_boost:.3f}, strategy_boost={factors.strategy_boost:.3f}, "
            f"validation_boost={factors.validation_boost:.3f}, context_boost={factors.context_boost:.3f}, "
            f"quality_penalty={factors.quality_penalty:.3f}, final={final_confidence:.3f}"
        )
        
        return final_confidence
    
    # Contract-compliant async
    async def calculate_field_confidence(self, 
                                       field_data: Dict[str, Any],
                                       context: Optional[Dict[str, Any]] = None) -> float:  # type: ignore[override]
        field_name = field_data.get('field_name') or field_data.get('name') or ''
        value = field_data.get('value', '')
        strategy = field_data.get('strategy', '')
        base_confidence = float(field_data.get('confidence', field_data.get('base_confidence', 0.0)))
        validation_results = field_data.get('validation_results')
        ctx = context or field_data.get('context')
        return self.calculate_field_confidence_sync(
            field_name=field_name,
            value=value,
            strategy=strategy,
            base_confidence=base_confidence,
            validation_results=validation_results,
            context=ctx
        )

    # Sync helper for agreement
    def calculate_agreement_confidence_sync(self, 
                                     field_name: str, 
                                     strategy_results: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate confidence boost when multiple strategies agree on a field (sync).
        """
        agreement_details = {
            'strategies_agreeing': [],
            'agreement_count': 0,
            'confidence_values': {},
            'value_agreement': False,
            'boost_factor': 1.0
        }
        
        agreeing_strategies = []
        confidence_values = {}
        
        # Check which strategies found this field
        for strategy, result in strategy_results.items():
            if isinstance(result, dict) and 'fields' in result:
                fields = result['fields']
                if field_name in fields:
                    field_data = fields[field_name]
                    if isinstance(field_data, dict) and 'value' in field_data:
                        value = field_data.get('value')
                        confidence = field_data.get('confidence', 0.0)
                        
                        if value and value not in ['null', '', 'None']:
                            agreeing_strategies.append(strategy)
                            confidence_values[strategy] = confidence
                            agreement_details['confidence_values'][strategy] = confidence
        
        agreement_details['strategies_agreeing'] = agreeing_strategies
        agreement_details['agreement_count'] = len(agreeing_strategies)
        
        if len(agreeing_strategies) > 1:
            # Calculate boost factor based on agreement count
            base_boost = 1.0 + (0.1 * (len(agreeing_strategies) - 1))
            agreement_details['boost_factor'] = min(base_boost, 1.5)  # Cap at 50% boost
            
            agreement_confidence = sum(confidence_values.values()) / len(confidence_values.values())
            agreement_confidence *= agreement_details['boost_factor']
            
            logger.debug(
                f"Agreement confidence for {field_name}: {len(agreeing_strategies)} strategies agree, "
                f"boost_factor={agreement_details['boost_factor']:.3f}, final={agreement_confidence:.3f}"
            )
            
            return min(agreement_confidence, 1.0), agreement_details
        
        return 0.0, agreement_details

    # Contract-compliant async agreement
    async def calculate_agreement_confidence(self, 
                                           strategy_results: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:  # type: ignore[override]
        # Attempt to infer field name from provided results
        field_name = ''
        if strategy_results and isinstance(strategy_results[0], dict):
            field_name = strategy_results[0].get('field_name') or strategy_results[0].get('name') or ''
        # Convert list form into the dict format expected by the sync method when possible
        merged: Dict[str, Any] = {}
        for entry in strategy_results:
            strategy = entry.get('strategy')
            fields = entry.get('fields')
            if strategy and fields:
                merged[strategy] = {'fields': fields}
        if not field_name or not merged:
            return 0.0, {'strategies_agreeing': [], 'agreement_count': 0, 'confidence_values': {}, 'value_agreement': False, 'boost_factor': 1.0}
        return self.calculate_agreement_confidence_sync(field_name, merged)

    # Contract-compliant overall confidence
    async def calculate_overall_confidence(self, 
                                         field_confidences: Dict[str, float],
                                         context: Optional[Dict[str, Any]] = None) -> float:  # type: ignore[override]
        return self.calculate_overall_confidence_sync(field_confidences, None)

    # Sync helper overall
    def calculate_overall_confidence_sync(self, 
                                        field_confidences: Dict[str, float], 
                                        field_weights: Optional[Dict[str, float]] = None) -> float:
        values = field_confidences
        if not values:
            return 0.0
        weights = field_weights or self.field_weights
        total_weighted_confidence = 0.0
        total_weight = 0.0
        for field_name, confidence in values.items():
            weight = weights.get(field_name, 1.0)
            total_weighted_confidence += confidence * weight
            total_weight += weight
        if total_weight == 0:
            return 0.0
        overall_confidence = total_weighted_confidence / total_weight
        logger.debug(
            f"Overall confidence calculation: {len(values)} fields, "
            f"total_weighted_confidence={total_weighted_confidence:.3f}, "
            f"total_weight={total_weight:.3f}, overall={overall_confidence:.3f}"
        )
        return overall_confidence

    async def get_confidence_metadata(self, field_name: str, confidence: float) -> Dict[str, Any]:  # type: ignore[override]
        tier = ConfidenceThresholds.get_tier(confidence)
        return {
            'field': field_name,
            'confidence': confidence,
            'tier': tier.value
        }

    def _calculate_validation_boost(self, validation_results: Dict[str, Any]) -> float:
        """Calculate confidence boost from validation results."""
        total_boost = 0.0
        for validation_type, boost in self.validation_boosts.items():
            if validation_results.get(validation_type, False):
                total_boost += boost
        return min(total_boost, 0.3)  # Cap validation boost at 30%
    
    def _calculate_context_boost(self, field_name: str, value: str, context: Dict[str, Any]) -> float:
        """Calculate confidence boost from context information."""
        boost = 0.0
        # Check for context consistency
        if field_name == 'vintage' and 'year' in context:
            try:
                year = int(value)
                context_year = int(context['year'])
                if abs(year - context_year) <= 1:  # Within 1 year
                    boost += 0.05
            except (ValueError, TypeError):
                pass
        # Check for region consistency (placeholder)
        if field_name == 'region' and 'country' in context:
            pass
        return boost
    
    def _calculate_quality_penalty(self, field_name: str, value: str) -> float:
        """Calculate quality penalty based on field characteristics."""
        penalty = 0.0
        if not value or value in ['null', '']:
            penalty += 0.3
        # Field-specific quality checks
        if field_name == 'vintage':
            if not re.match(r'^(19|20)\d{2}$|^NV$', value):
                penalty += 0.2
        elif field_name == 'price':
            if not re.match(r'^\d+(?:\.\d{2})?$', value):
                penalty += 0.2
        elif field_name == 'region':
            if len(value) < 2:  # Very short region names are suspicious
                penalty += 0.1
        return penalty
    
    def normalize_confidence(self, confidence: float, strategy: str, field_name: str) -> float:
        """
        Normalize confidence scores across strategies and fields.
        """
        # Apply strategy normalization
        strategy_factor = self.strategy_adjustments.get(strategy, 1.0)
        normalized = confidence / strategy_factor
        # Apply field normalization
        field_factor = self.field_weights.get(field_name, 1.0)
        normalized = normalized / field_factor
        # Ensure within bounds
        return max(0.0, min(1.0, normalized))
    
    def should_use_fallback(self, 
                          rule_confidence: float, 
                          ai_confidence: float, 
                          field_name: str,
                          threshold: float = 0.6) -> bool:
        """
        Determine if AI fallback should be used based on confidence comparison.
        """
        # If rule confidence is below threshold, use AI
        if rule_confidence < threshold:
            return True
        # If AI confidence is significantly higher, use AI
        if ai_confidence > rule_confidence + 0.2:
            return True
        # For certain fields, prefer AI even with similar confidence
        ai_preferred_fields = ['wine_name', 'producer_name', 'grape_variety']
        if field_name in ai_preferred_fields and ai_confidence > rule_confidence:
            return True
        return False 