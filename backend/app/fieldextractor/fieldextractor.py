from typing import List, Dict, Any, Optional
from .strategies.regex_strategy import RegexStrategy
from .strategies.ner_strategy import NERStrategy
from .strategies.ai_strategy import AIStrategy
from app.database_enhanced_rules.database_manager import DatabaseManager
from app.rules.rule_manager import RuleManager
from app.rules.confidence_calculator import ConfidenceCalculator
import logging

logger = logging.getLogger(__name__)

# Define the fields to be extracted based on wine list standard plus additional fields
FIELDS_TO_EXTRACT = [
    # Producer information
    'producer_title',  # Title of producer or owner of wine
    'producer_name',   # Producer or owner of wine
    
    # Wine information
    'wine_name',       # Name of wine (brand and/or grape and/or technical term)
    'grape_variety',   # Grape variety (additional field)
    'vintage',         # Vintage year or NV
    
    # Geographic information
    'country',         # Country of origin
    'region',          # Region of origin
    'sub_region',      # Sub-region of origin
    'site',           # Site within sub-region
    'parcel',         # Parcel within site
    
    # Wine characteristics
    'colour',         # Colour of product
    'type',           # Beverage type
    'sub_type',       # Subcategory of type
    
    # Classification information
    'designation',    # Officially assigned status
    'classification', # Officially declared quality level
    
    # Additional fields
    'price'           # Price of the wine
]

class FieldExtractor:
    def __init__(self, strategies: Optional[List[str]] = None, restaurant_id: Optional[str] = None):
        self.strategies = strategies or ['database', 'regex', 'ner', 'ai']  # Database first
        self.restaurant_id = restaurant_id
        # Only create RuleManager if we have a restaurant_id and it's not a test ID
        if restaurant_id and not restaurant_id.startswith('test-'):
            try:
                self.rule_manager = RuleManager()
            except Exception as e:
                logger.warning(f"Failed to initialize RuleManager for restaurant {restaurant_id}: {e}")
                self.rule_manager = None
        else:
            self.rule_manager = None
        self.database_manager = DatabaseManager() if 'database' in self.strategies else None
        self.regex_strategy = RegexStrategy() if 'regex' in self.strategies else None
        self.ner_strategy = NERStrategy() if 'ner' in self.strategies else None
        self.ai_strategy = AIStrategy() if 'ai' in self.strategies else None  # Enable AI strategy
        
        # Initialize confidence calculator
        self.confidence_calculator = ConfidenceCalculator()

    def extract(self, block: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[FieldExtractor] Field extraction started for block.")
        if block is None:
            return {}
        extracted_fields = {}
        # Load restaurant-specific rules if available
        restaurant_rules = None
        if self.restaurant_id and self.rule_manager:
            try:
                restaurant_rules = self.rule_manager.load_rules(self.restaurant_id)
            except Exception as e:
                logger.warning(f"Failed to load rules for restaurant {self.restaurant_id}: {e}")
                restaurant_rules = None

        # Get results from all strategies first
        strategy_results = {}
        
        # 1. Database strategy (highest priority for geographic fields)
        if self.database_manager:
            db_fields, db_conf = self.database_manager.extract_fields(block)
            strategy_results['database'] = {'fields': db_fields, 'confidence': db_conf}
            logger.debug(f"[FieldExtractor] Database extraction confidence: {db_conf}")

        # 2. NER strategy
        if self.ner_strategy:
            ner_fields, ner_conf = self.ner_strategy.extract(block)
            strategy_results['ner'] = {'fields': ner_fields, 'confidence': ner_conf}
            logger.debug(f"[FieldExtractor] NER extraction confidence: {ner_conf}")

        # 3. Regex strategy
        if self.regex_strategy:
            regex_fields, regex_conf = self.regex_strategy.extract(block, restaurant_rules)
            strategy_results['regex'] = {'fields': regex_fields, 'confidence': regex_conf}
            logger.debug(f"[FieldExtractor] Regex extraction confidence: {regex_conf}")

        # 4. AI strategy (fallback)
        if self.ai_strategy:
            ai_fields, ai_conf = self.ai_strategy.extract(block)
            strategy_results['ai'] = {'fields': ai_fields, 'confidence': ai_conf}
            logger.debug(f"[FieldExtractor] AI extraction confidence: {ai_conf}")

        # Intelligent field merging with cross-strategy validation
        extracted_fields = self._merge_strategy_results(strategy_results, restaurant_rules)
        
        if extracted_fields is None:
            extracted_fields = {}
        
        # Calculate overall confidence using the new confidence calculator
        if extracted_fields:
            field_confidences = {}
            for field_name, field_data in extracted_fields.items():
                if isinstance(field_data, dict) and 'confidence' in field_data:
                    field_confidences[field_name] = field_data['confidence']
            overall_confidence = self.confidence_calculator.calculate_overall_confidence_sync(field_confidences)
            extracted_fields['confidence'] = overall_confidence
        
        logger.info("Field extraction complete for block.")
        return extracted_fields
    
    def _merge_strategy_results(self, strategy_results: Dict[str, Any], restaurant_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge results from multiple strategies with cross-validation."""
        merged_fields = {}
        
        # Define field priorities and strategy preferences
        field_priorities = {
            'producer_name': ['database', 'ner', 'regex', 'ai'],
            'region': ['database', 'ner', 'regex', 'ai'],
            'country': ['database', 'ner', 'regex', 'ai'],
            'grape_variety': ['database', 'ner', 'regex', 'ai'],
            'vintage': ['regex', 'ner', 'ai'],
            'price': ['regex', 'ner', 'ai'],
            'wine_name': ['ner', 'regex', 'ai'],
            'designation': ['regex', 'ner', 'ai'],
            'type': ['regex', 'ner', 'ai']
        }
        
        # Process each field with intelligent merging
        for field_name, strategy_order in field_priorities.items():
            field_result = self._get_best_field_result(field_name, strategy_results, strategy_order)
            if field_result:
                merged_fields[field_name] = field_result
        
        # Apply cross-strategy confidence boosters
        merged_fields = self._apply_cross_strategy_boosters(merged_fields, strategy_results)
        
        return merged_fields
    
    def _get_best_field_result(self, field_name: str, strategy_results: Dict[str, Any], 
                              strategy_order: List[str]) -> Optional[Dict[str, Any]]:
        """Get the best result for a field based on strategy priority and confidence."""
        best_result = None
        best_confidence = 0.0
        best_strategy = None
        
        for strategy in strategy_order:
            if strategy not in strategy_results:
                continue
                
            strategy_data = strategy_results[strategy]
            fields = strategy_data.get('fields', {})
            
            if field_name in fields:
                field_data = fields[field_name]
                if isinstance(field_data, dict) and 'value' in field_data:
                    base_confidence = field_data.get('confidence', 0.0)
                    value = field_data.get('value', '')
                    
                    # Use the new confidence calculator (sync)
                    calculated_confidence = self.confidence_calculator.calculate_field_confidence_sync(
                        field_name=field_name,
                        value=value,
                        strategy=strategy,
                        base_confidence=base_confidence,
                        validation_results=field_data.get('validation_results'),
                        context=field_data.get('context')
                    )
                    
                    # Lower threshold for database strategy to allow better fallback
                    if strategy == 'database' and calculated_confidence < 0.3:
                        continue  # Skip low-confidence database results
                    
                    if calculated_confidence > best_confidence:
                        best_result = field_data.copy()
                        best_result['confidence'] = calculated_confidence
                        best_result['provenance'] = strategy
                        best_confidence = calculated_confidence
                        best_strategy = strategy
        
        return best_result
    
    def _adjust_confidence_for_strategy(self, confidence: float, strategy: str, 
                                      field_name: str, field_data: Dict[str, Any]) -> float:
        """Adjust confidence based on strategy and field characteristics."""
        adjusted_confidence = confidence
        
        # Database strategy gets confidence boost for geographic fields
        if strategy == 'database' and field_name in ['region', 'country', 'producer_name', 'grape_variety']:
            adjusted_confidence *= 1.2
        
        # NER strategy gets confidence boost for entity fields
        if strategy == 'ner' and field_name in ['producer_name', 'region', 'country', 'wine_name']:
            adjusted_confidence *= 1.1
        
        # Regex strategy gets confidence boost for structured fields
        if strategy == 'regex' and field_name in ['vintage', 'price', 'designation']:
            adjusted_confidence *= 1.15
        
        # AI strategy gets confidence reduction (used as fallback)
        if strategy == 'ai':
            adjusted_confidence *= 0.9
        
        return min(adjusted_confidence, 1.0)
    
    def _apply_cross_strategy_boosters(self, merged_fields: Dict[str, Any], 
                                     strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Apply confidence boosters when multiple strategies agree on a field."""
        for field_name, field_data in merged_fields.items():
            # Use the new confidence calculator for agreement confidence (sync)
            agreement_confidence, agreement_details = self.confidence_calculator.calculate_agreement_confidence_sync(
                field_name, strategy_results
            )
            
            if agreement_confidence > 0.0:
                # Apply agreement boost
                field_data['confidence'] = min(field_data['confidence'] + agreement_confidence * 0.1, 1.0)
                field_data['strategy_agreement'] = agreement_details['agreement_count']
                field_data['cross_strategy_boosted'] = True
                field_data['agreement_details'] = agreement_details
                
                logger.debug(f"[FieldExtractor] Applied cross-strategy boost to {field_name}: "
                           f"{agreement_details['agreement_count']} strategies agree, "
                           f"boost={agreement_confidence:.3f}")
        
        return merged_fields

    def extract_batch(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("[FieldExtractor] Field extraction batch started.")
        results = []
        for i, block in enumerate(blocks):
            if block is None:
                results.append({})
                continue
            try:
                result = self.extract(block)
                if result is None:
                    result = {}
                results.append(result)
            except Exception as e:
                logger.error(f"Error extracting block {i}: {e}")
                results.append({})
        logger.info("Field extraction batch complete.")
        return results
