from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import os
import traceback

from .intelligent_sampler import IntelligentSampler
from .ai_rule_generator import AIRuleGenerator
from .rule_applicator import RuleApplicator
from .rule_validator import RuleValidator
from .rule_manager import RuleManager
from app.fieldextractor.fieldextractor import FieldExtractor
from app.fieldextractor.strategies.ai_strategy import AIStrategy
from app.database_enhanced_rules.early_extractor import EarlyExtractor
from app.config import (
    AI_RULE_GENERATION_ENABLED, SAMPLE_SIZE_RATIO, MIN_SAMPLE_SIZE, MAX_SAMPLE_SIZE,
    MIN_CONFIDENCE_THRESHOLD_HYBRID, FALLBACK_AI_MODEL,
    MIN_VALIDATION_ENTRIES, VALIDATION_SPLIT_RATIO,
    MIN_FIELDS_EXTRACTED_THRESHOLD, AI_FALLBACK_MAX_ENTRIES, AI_FALLBACK_SAMPLE_RATIO,
    DATABASE_INTEGRATION_ENABLED, EARLY_EXTRACTOR_CONFIDENCE_THRESHOLD
)

logger = logging.getLogger(__name__)

class HybridExtractionPipeline:
    """
    Main pipeline for AI-Enhanced Hybrid Rule Generation System.
    
    Orchestrates the entire process:
    1. Intelligent sampling
    2. AI rule generation
    3. Rule application and validation
    4. Fallback to AI for low-confidence cases
    """
    
    def __init__(self, restaurant_id: str):
        self.restaurant_id = restaurant_id
        self.sampler = IntelligentSampler()
        self.ai_rule_generator = AIRuleGenerator()
        self.rule_applicator = RuleApplicator()
        self.rule_validator = RuleValidator()
        self.rule_manager = RuleManager()
        self.ai_strategy = AIStrategy()
        self.early_extractor = EarlyExtractor() if DATABASE_INTEGRATION_ENABLED else None
        
        # Configure AI fallback thresholds
        self.confidence_threshold = MIN_CONFIDENCE_THRESHOLD_HYBRID
        self.min_fields_threshold = MIN_FIELDS_EXTRACTED_THRESHOLD
        self.ai_fallback_max_entries = AI_FALLBACK_MAX_ENTRIES
        self.ai_fallback_sample_ratio = AI_FALLBACK_SAMPLE_RATIO
    
    def process_wine_list(self, wine_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a wine list using the hybrid extraction pipeline.
        """
        logger.info("[Pipeline] 🚀 Hybrid extraction pipeline started.")
        start_time = datetime.utcnow()
        logger.info(f"[Pipeline] 📊 Starting hybrid extraction for {len(wine_blocks)} wine blocks")
        try:
            # Step 1: Check for restaurant-specific rules first
            logger.info(f"[Pipeline] 🔍 Step 1: Checking for restaurant-specific rules for {self.restaurant_id}")
            restaurant_rules = self._check_restaurant_rules()
            if restaurant_rules:
                logger.info(f"[Pipeline] ✅ Found existing rules for restaurant {self.restaurant_id}, using them")
                results = self._apply_restaurant_rules(wine_blocks, restaurant_rules)
                results['metadata']['restaurant_rules_used'] = True
                logger.info("[Pipeline] ✅ Used restaurant-specific rules. Extraction complete.")
                return results
            else:
                logger.info(f"[Pipeline] ❌ No existing rules found for restaurant {self.restaurant_id}, proceeding with hybrid pipeline")

            # Step 2: Intelligent sampling (for AI parsing and rule generation)
            logger.info(f"[Pipeline] 🎯 Step 2: Performing intelligent sampling on {len(wine_blocks)} blocks")
            sample_entries = self._perform_intelligent_sampling(wine_blocks)
            logger.info(f"[Pipeline] ✅ Selected {len(sample_entries)} sample entries for rule generation")
            logger.info(f"[Pipeline] 📝 Sample entries preview: {[e.get('text','')[:50] + '...' if len(e.get('text','')) > 50 else e.get('text','') for e in sample_entries[:3]]}")

            # Step 3: Perform early database extraction (for all entries, but also for sample)
            logger.info(f"[Pipeline] 🗄️ Step 3: Performing early database extraction on {len(wine_blocks)} blocks")
            early_results = self._perform_early_database_extraction(wine_blocks)
            logger.info(f"[Pipeline] ✅ Early database extraction completed for {len(early_results)} blocks")
            if early_results:
                logger.info(f"[Pipeline] 📊 Early extraction example: {early_results[0] if early_results else 'None'}")

            # Step 4: Get initial extraction results for sample (regex, DB, NER)
            logger.info(f"[Pipeline] 🔧 Step 4: Getting initial extraction results for {len(sample_entries)} sample entries")
            initial_results = self._get_initial_extraction(sample_entries)
            logger.info(f"[Pipeline] ✅ Initial extraction for sample complete. Got {len(initial_results)} results")
            if initial_results:
                logger.info(f"[Pipeline] 📊 Initial extraction example: {initial_results[0] if initial_results else 'None'}")

            # Step 5: Get AI extraction results for sample (AI parsing, not fallback)
            logger.info(f"[Pipeline] 🤖 Step 5: Getting AI extraction results for {len(sample_entries)} sample entries")
            ai_results = self._get_ai_extraction(sample_entries)
            logger.info(f"[Pipeline] ✅ AI extraction for sample complete. Got {len(ai_results)} results")
            if ai_results:
                logger.info(f"[Pipeline] 📊 AI extraction example: {ai_results[0] if ai_results else 'None'}")

            # Step 6: Generate AI rules using all sample results
            logger.info(f"[Pipeline] 🧠 Step 6: Generating AI rules from sample data")
            if AI_RULE_GENERATION_ENABLED:
                logger.info(f"[Pipeline] ✅ AI rule generation is ENABLED")
                generated_rules = self._generate_ai_rules(sample_entries, ai_results, initial_results)
                rule_count = len(generated_rules) if isinstance(generated_rules, dict) else 0
                logger.info(f"[Pipeline] ✅ AI rule generation complete. Generated {rule_count} rules")
                if generated_rules:
                    logger.info(f"[Pipeline] 📊 Generated rules keys: {list(generated_rules.keys()) if isinstance(generated_rules, dict) else 'Not a dict'}")
            else:
                logger.info("[Pipeline] ⚠️ AI rule generation disabled, using existing rules")
                generated_rules = self.rule_manager.load_rules(self.restaurant_id)
                logger.info(f"[Pipeline] ✅ Loaded {len(generated_rules) if isinstance(generated_rules, dict) else 0} existing rules")

            # Step 7: Validate rules (if we have enough test data)
            logger.info(f"[Pipeline] ✅ Step 7: Validating generated rules against {len(wine_blocks)} total blocks")
            validation_results = self._validate_generated_rules(generated_rules, wine_blocks)
            logger.info(f"[Pipeline] ✅ Rule validation complete. Validation results: {validation_results}")

            # Step 8: Apply rules to all entries (majority of entries use rule-based extraction)
            logger.info(f"[Pipeline] ⚙️ Step 8: Applying rules to all {len(wine_blocks)} entries")
            extraction_results = self._apply_rules_to_all_entries(wine_blocks, generated_rules)
            logger.info(f"[Pipeline] ✅ Rule application to all entries complete. Got {len(extraction_results)} results")
            if extraction_results:
                logger.info(f"[Pipeline] 📊 Extraction example: {extraction_results[0] if extraction_results else 'None'}")

            # Step 9: ITERATIVE RULE GENERATION - Re-sample from failed entries and improve rules
            logger.info(f"[Pipeline] 🔄 Step 9: Starting iterative rule generation")
            improved_rules, iteration_metadata = self._perform_iterative_rule_generation(
                wine_blocks, extraction_results, generated_rules, early_results
            )
            
            if improved_rules:
                logger.info(f"[Pipeline] ✅ Iterative rule generation complete. Improved rules generated.")
                logger.info(f"[Pipeline] 📊 Iteration metadata: {iteration_metadata}")
                
                # Re-apply improved rules to all entries
                logger.info(f"[Pipeline] ⚙️ Step 9b: Re-applying improved rules to all {len(wine_blocks)} entries")
                final_extraction_results = self._apply_rules_to_all_entries(wine_blocks, improved_rules)
                logger.info(f"[Pipeline] ✅ Re-application with improved rules complete.")
                
                # Use improved rules for saving
                generated_rules = improved_rules
                extraction_results = final_extraction_results
            else:
                logger.info(f"[Pipeline] ⚠️ No improved rules generated, using original rules")

            # Step 10: Save rules to restaurant-specific storage (database only)
            if generated_rules:
                logger.info(f"[Pipeline] 💾 Step 10: Saving {len(generated_rules) if isinstance(generated_rules, dict) else 0} rules for restaurant {self.restaurant_id}")
                self._save_restaurant_rules(generated_rules, validation_results)
                logger.info(f"[Pipeline] ✅ Saved rules for restaurant {self.restaurant_id}")

            # Step 11: Prepare final results
            logger.info(f"[Pipeline] 📋 Step 11: Preparing final results")
            final_results = self._prepare_final_results(
                extraction_results, validation_results, start_time, iteration_metadata
            )
            processing_time = final_results.get('metadata', {}).get('processing_time_seconds', '?')
            logger.info(f"[Pipeline] ✅ Final results preparation complete. Processed {len(extraction_results)} entries in {processing_time}s")

            logger.info(f"[Pipeline] 🎉 Hybrid extraction completed successfully")
            return final_results
        except Exception as e:
            logger.error(f"[Pipeline] 💥 Error in hybrid extraction pipeline: {str(e)}")
            logger.error(f"[Pipeline] 💥 Traceback: {traceback.format_exc()}")
            # Fallback to pure AI extraction
            logger.info(f"[Pipeline] 🔄 Falling back to pure AI extraction")
            return self._fallback_to_ai_extraction(wine_blocks, start_time)
    
    def _check_restaurant_rules(self) -> Optional[Dict[str, Any]]:
        """Check for restaurant-specific rules."""
        try:
            saved_data = self.rule_manager.load_rules(self.restaurant_id)
            if saved_data and isinstance(saved_data, dict) and len(saved_data) > 0:
                # Check if it's the new format with metadata
                if 'rules' in saved_data and 'metadata' in saved_data:
                    rules = saved_data['rules']
                    metadata = saved_data['metadata']
                    logger.info(f"Found {len(rules) if isinstance(rules, dict) else 0} rules for restaurant {self.restaurant_id} (created: {metadata.get('created_at', 'unknown')})")
                    return rules
                else:
                    # Old format - return as is
                    logger.info(f"Found {len(saved_data)} rules for restaurant {self.restaurant_id} (old format)")
                    return saved_data
            else:
                logger.info(f"No existing rules found for restaurant {self.restaurant_id}")
                return None
        except Exception as e:
            logger.warning(f"Error checking restaurant rules: {str(e)}")
            return None
    
    def _apply_restaurant_rules(self, wine_blocks: List[Dict[str, Any]], 
                               restaurant_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply restaurant-specific rules to wine blocks."""
        extraction_results = []
        ai_fallback_count = 0
        
        logger.info(f"Applying restaurant rules to {len(wine_blocks)} wine blocks")
        
        for block in wine_blocks:
            # Apply restaurant rules
            rule_result = self.rule_applicator.apply_rules(block, restaurant_rules)
            
            # Check if fallback to AI is needed
            if self.rule_applicator.should_use_fallback(rule_result):
                try:
                    # AI strategy extract returns (fields, confidence) tuple
                    ai_fields, ai_confidence = self.ai_strategy.extract(block)
                    
                    # Ensure ai_fields is properly formatted
                    if ai_fields and isinstance(ai_fields, dict):
                        # Convert AI fields to proper format if needed
                        formatted_ai_fields = {}
                        for field_name, field_data in ai_fields.items():
                            if isinstance(field_data, dict):
                                formatted_ai_fields[field_name] = field_data
                            else:
                                # Convert simple value to proper format
                                formatted_ai_fields[field_name] = {
                                    'value': field_data,
                                    'confidence': ai_confidence,
                                    'provenance': 'ai_fallback'
                                }
                        
                        ai_result = {
                            'fields': formatted_ai_fields,
                            'confidence': ai_confidence,
                            'provenance': 'ai_fallback'
                        }
                        final_result = self.rule_applicator.merge_results(rule_result, ai_result)
                        ai_fallback_count += 1
                    else:
                        # AI extraction failed, use rule result
                        final_result = rule_result
                        
                except Exception as ai_error:
                    logger.error(f"AI fallback failed: {ai_error}")
                    final_result = rule_result
            else:
                final_result = rule_result
            
            extraction_results.append(final_result)
        
        # Log summary instead of details
        if ai_fallback_count > 0:
            logger.info(f"Applied rules with {ai_fallback_count} AI fallbacks ({ai_fallback_count/len(wine_blocks):.1%})")
        else:
            logger.info(f"Applied rules successfully - no AI fallback needed")
        
        return {
            'extraction_results': extraction_results,
            'metadata': {
                'total_entries': len(wine_blocks),
                'ai_fallback_count': ai_fallback_count,
                'ai_fallback_rate': ai_fallback_count / len(wine_blocks) if wine_blocks else 0,
                'restaurant_rules_used': True,
                'processing_method': 'restaurant_rules'
            }
        }
    
    def _perform_intelligent_sampling(self, wine_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform intelligent sampling of wine blocks."""
        logger.info(f"[Sampler] 🎯 Starting intelligent sampling for {len(wine_blocks)} wine blocks")
        
        # Calculate sample size
        sample_size = max(
            MIN_SAMPLE_SIZE,
            min(MAX_SAMPLE_SIZE, int(len(wine_blocks) * SAMPLE_SIZE_RATIO))
        )
        
        logger.info(f"[Sampler] 📊 Sample size calculated: {sample_size} (MIN: {MIN_SAMPLE_SIZE}, MAX: {MAX_SAMPLE_SIZE}, RATIO: {SAMPLE_SIZE_RATIO})")
        
        try:
            sample_entries = self.sampler.select_sample(wine_blocks, sample_size)
            logger.info(f"[Sampler] ✅ Intelligent sampling completed. Selected {len(sample_entries)} entries")
            return sample_entries
        except Exception as e:
            logger.error(f"[Sampler] 💥 Error in intelligent sampling: {str(e)}")
            logger.error(f"[Sampler] 💥 Traceback: {traceback.format_exc()}")
            # Fallback to simple random sampling
            logger.info(f"[Sampler] 🔄 Falling back to simple random sampling")
            import random
            sample_entries = random.sample(wine_blocks, min(sample_size, len(wine_blocks)))
            logger.info(f"[Sampler] ✅ Simple random sampling completed. Selected {len(sample_entries)} entries")
            return sample_entries
    
    def _get_initial_extraction(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get initial extraction results using current rules."""
        logger.info(f"[Initial] 🔧 Starting initial extraction for {len(sample_entries)} sample entries")
        
        try:
            logger.info(f"[Initial] 📞 Creating FieldExtractor for restaurant {self.restaurant_id}")
            field_extractor = FieldExtractor(restaurant_id=self.restaurant_id)
            logger.info(f"[Initial] ✅ FieldExtractor created successfully")
            
            logger.info(f"[Initial] 📞 Calling extract_batch...")
            results = field_extractor.extract_batch(sample_entries)
            logger.info(f"[Initial] ✅ extract_batch completed. Got {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"[Initial] 💥 Error in initial extraction: {str(e)}")
            logger.error(f"[Initial] 💥 Traceback: {traceback.format_exc()}")
            return []
    
    def _get_ai_extraction(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get AI extraction results for sample entries."""
        logger.info(f"[AI] 🤖 Starting AI extraction for {len(sample_entries)} sample entries")
        
        try:
            logger.info(f"[AI] 📊 Calling AI strategy extract_batch...")
            results = self.ai_strategy.extract_batch(sample_entries)
            logger.info(f"[AI] ✅ AI strategy extract_batch completed")
            
            # Ensure we have the right number of results
            if len(results) != len(sample_entries):
                logger.warning(f"[AI] ⚠️ AI extraction returned {len(results)} results for {len(sample_entries)} entries")
                # Pad with empty results if needed
                while len(results) < len(sample_entries):
                    results.append({
                        'producer_name': {
                            'value': None,
                            'confidence': 0.0,
                            'provenance': 'ai_padding'
                        }
                    })
                logger.info(f"[AI] 📊 Padded results to match expected count: {len(results)}")
            
            logger.info(f"[AI] ✅ AI extraction completed successfully. Got {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[AI] 💥 Error in AI extraction: {str(e)}")
            logger.error(f"[AI] 💥 Traceback: {traceback.format_exc()}")
            # Return empty results for all entries
            logger.info(f"[AI] 🔄 Returning empty results due to error")
            return [{
                'producer_name': {
                    'value': None,
                    'confidence': 0.0,
                    'provenance': 'ai_error'
                }
            } for _ in sample_entries]
    
    def _generate_ai_rules(self, sample_entries: List[Dict[str, Any]], 
                          ai_results: List[Dict[str, Any]], 
                          initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI rules from sample entries."""
        logger.info(f"[AIRules] 🧠 Starting AI rule generation")
        logger.info(f"[AIRules] 📊 Input: {len(sample_entries)} sample entries, {len(ai_results)} AI results, {len(initial_results)} initial results")
        
        try:
            logger.info(f"[AIRules] 📞 Calling AI rule generator...")
            rules_result = self.ai_rule_generator.generate_rules(
                sample_entries, ai_results, initial_results
            )
            
            logger.info(f"[AIRules] ✅ AI rule generator completed")
            
            # Extract rules from the result
            if isinstance(rules_result, dict):
                if 'rules' in rules_result:
                    rules = rules_result['rules']
                    logger.info(f"[AIRules] ✅ Successfully extracted {len(rules)} rule categories")
                    
                    # Save rules to restaurant-specific storage
                    if rules:
                        logger.info(f"[AIRules] 💾 Saving {len(rules)} generated rules")
                        self.rule_manager.update_rules(self.restaurant_id, rules)
                        logger.info(f"[AIRules] ✅ Rules saved to restaurant storage")
                    
                    return rules
                elif 'patterns' in rules_result:
                    # Handle chunked processing result format
                    patterns = rules_result['patterns']
                    logger.info(f"[AIRules] ✅ Successfully extracted patterns from chunked processing")
                    
                    # Convert patterns to rules format
                    rules = self._convert_patterns_to_rules(patterns)
                    if rules:
                        logger.info(f"[AIRules] 💾 Saving {len(rules)} converted rules")
                        self.rule_manager.update_rules(self.restaurant_id, rules)
                        logger.info(f"[AIRules] ✅ Rules saved to restaurant storage")
                    
                    return rules
                else:
                    logger.warning(f"[AIRules] ⚠️ Unexpected rules result format: {type(rules_result)}")
                    logger.warning(f"[AIRules] ⚠️ Rules result keys: {list(rules_result.keys()) if isinstance(rules_result, dict) else 'Not a dict'}")
                    return self._get_fallback_rules()
            else:
                logger.warning(f"[AIRules] ⚠️ Rules result is not a dict: {type(rules_result)}")
                return self._get_fallback_rules()
            
        except Exception as e:
            logger.error(f"[AIRules] 💥 Error in AI rule generation: {str(e)}")
            logger.error(f"[AIRules] 💥 Traceback: {traceback.format_exc()}")
            return self._get_fallback_rules()
    
    def _convert_patterns_to_rules(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Convert patterns from chunked processing to rules format."""
        rules = {}
        
        # Convert field patterns
        field_patterns = patterns.get('field_patterns', {})
        for field_name, pattern_data in field_patterns.items():
            if isinstance(pattern_data, dict):
                rules[field_name] = {
                    'regex_patterns': pattern_data.get('patterns', []),
                    'confidence_threshold': 0.7
                }
        
        # Convert price patterns
        price_patterns = patterns.get('price_patterns', {})
        if price_patterns:
            rules['price'] = {
                'regex_patterns': price_patterns.get('patterns', []),
                'confidence_threshold': 0.8
            }
        
        # Convert vintage patterns
        vintage_patterns = patterns.get('vintage_patterns', {})
        if vintage_patterns:
            rules['vintage'] = {
                'regex_patterns': vintage_patterns.get('patterns', []),
                'confidence_threshold': 0.8
            }
        
        return rules
    
    def _get_fallback_rules(self) -> Dict[str, Any]:
        """Get fallback rules when AI generation fails."""
        logger.info("[AIRules] 🔄 Using fallback rules due to AI generation failure")
        
        # Basic fallback rules based on common wine list patterns
        fallback_rules = {
            'vintage': {
                'regex_patterns': [
                    r'\b(19|20)\d{2}\b',  # 4-digit years
                    r'\bNV\b',  # Non-vintage
                    r'(\d{4})\s*[-\u2013]',  # Year followed by dash
                ],
                'confidence_threshold': 0.8
            },
            'price': {
                'regex_patterns': [
                    r'(\d+)\s*$',  # Number at end
                    r'[£€$¥]\s*(\d+(?:\.\d{2})?)',  # Currency symbols
                    r'(\d{2,4})\s*[A-Z]',  # Number followed by letter
                ],
                'confidence_threshold': 0.8
            },
            'producer_name': {
                'regex_patterns': [
                    r'^([A-Z][A-Za-z\s&-]+?)(?=\s+\d{4}|\s+NV|\s+\"|\s+[A-Z]|$)',
                    r'([A-Z][A-Za-z\s&-]+?)\s*[,:–-]',
                ],
                'confidence_threshold': 0.7
            },
            'grape_variety': {
                'regex_patterns': [
                    r'\b(Chardonnay|Pinot Noir|Cabernet|Merlot|Syrah|Riesling|Sauvignon Blanc)\b',
                    r'\b(Meunier|Nebbiolo|Sangiovese|Verdejo|Albarino)\b',
                ],
                'confidence_threshold': 0.7
            }
        }
        
        logger.info(f"[AIRules] ✅ Generated {len(fallback_rules)} fallback rules")
        return fallback_rules
    
    def _validate_generated_rules(self, rules: Dict[str, Any], 
                                all_entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate generated rules against test entries."""
        if not rules or len(all_entries) < MIN_VALIDATION_ENTRIES:
            return None
        
        try:
            # Split entries for validation
            validation_size = max(MIN_VALIDATION_ENTRIES, int(len(all_entries) * VALIDATION_SPLIT_RATIO))
            validation_entries = all_entries[:validation_size]
            
            logger.info(f"Validating rules against {len(validation_entries)} entries")
            validation_results = self.rule_validator.validate_rules(rules, validation_entries)
            
            # Update rules with validation adjustments
            if 'adjusted_rules' in validation_results:
                self.rule_manager.update_rules(self.restaurant_id, validation_results['adjusted_rules'])
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error in rule validation: {str(e)}")
            return None
    
    def _apply_rules_to_all_entries(self, wine_blocks: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply rules to all wine blocks and merge with early database results, skipping rules/AI if DB is high confidence."""
        logger.info("[Pipeline] Applying rules to all entries...")
        early_results = self._perform_early_database_extraction(wine_blocks)
        extraction_results = []
        ai_fallback_count = 0
        db_only_count = 0
        
        for i, block in enumerate(wine_blocks):
            logger.debug(f"[Pipeline] Processing block {i}: {block.get('text','')[:80]}")
            early_result = early_results[i] if i < len(early_results) else {}
            
            # Check if we should use database-only extraction
            if early_result.get('skip_ai'):
                logger.debug(f"[Pipeline] Block {i}: Using database-only extraction: {early_result}")
                db_fields = {}
                for field, value in early_result.items():
                    if field in ['grape_variety', 'producer', 'region', 'country'] and value:
                        conf = early_result.get('field_confidence', {}).get(field, early_result.get('confidence', 1.0))
                        db_fields[field] = {
                            'value': value if not isinstance(value, dict) else value.get('value'),
                            'confidence': conf,
                            'provenance': 'database'
                        }
                avg_conf = sum(f['confidence'] for f in db_fields.values()) / len(db_fields) if db_fields else 1.0
                extraction_results.append({
                    'fields': db_fields,
                    'confidence': avg_conf,
                    'provenance': 'database_only',
                    'fields_extracted': len(db_fields)
                })
                db_only_count += 1
                continue
            
            try:
                # Apply rules first
                rule_result = self.rule_applicator.apply_rules(block, rules)
                logger.debug(f"[Pipeline] Block {i}: Rule result: {rule_result}")
                
                # Merge with early database results
                final_result = self._merge_early_and_rule_results(rule_result, early_result)
                logger.debug(f"[Pipeline] Block {i}: After merging with early extraction: {final_result}")
                
                # Check if we need AI fallback using smarter criteria
                should_use_ai_fallback = self._should_use_ai_fallback(
                    final_result, 
                    ai_fallback_count, 
                    len(wine_blocks)
                )
                
                if should_use_ai_fallback:
                    logger.debug(f"[Pipeline] Block {i}: Using AI fallback (confidence: {final_result.get('confidence', 0.0):.2f}, fields: {len(final_result.get('fields', {}))})")
                    
                    try:
                        # AI strategy returns (fields, confidence) tuple
                        ai_fields, ai_confidence = self.ai_strategy.extract(block)
                        
                        # Ensure ai_fields is properly formatted
                        if ai_fields and isinstance(ai_fields, dict):
                            # Convert AI fields to proper format if needed
                            formatted_ai_fields = {}
                            for field_name, field_data in ai_fields.items():
                                if isinstance(field_data, dict):
                                    formatted_ai_fields[field_name] = field_data
                                else:
                                    # Convert simple value to proper format
                                    formatted_ai_fields[field_name] = {
                                        'value': field_data,
                                        'confidence': ai_confidence,
                                        'provenance': 'ai_fallback'
                                    }
                            
                            # Only use AI fallback if it provides meaningful improvements
                            should_use_ai = self._ai_provides_improvement(
                                final_result.get('fields', {}), 
                                formatted_ai_fields
                            )
                            
                            if should_use_ai:
                                ai_result = {
                                    'fields': formatted_ai_fields,
                                    'confidence': ai_confidence,
                                    'provenance': 'ai_fallback'
                                }
                                final_result = self._merge_ai_fallback_results(final_result, ai_result)
                                ai_fallback_count += 1
                                logger.debug(f"[Pipeline] Block {i}: AI fallback applied successfully")
                            else:
                                logger.debug(f"[Pipeline] Block {i}: AI fallback not needed - no meaningful improvement")
                        else:
                            logger.debug(f"[Pipeline] Block {i}: AI extraction returned no valid fields")
                            
                    except Exception as ai_error:
                        logger.error(f"[Pipeline] AI fallback failed for block {i}: {ai_error}")
                        # Continue with rule results
                else:
                    logger.debug(f"[Pipeline] Block {i}: No AI fallback needed (confidence: {final_result.get('confidence', 0.0):.2f}, fields: {len(final_result.get('fields', {}))})")
                
                extraction_results.append(final_result)
                
            except Exception as e:
                logger.error(f"[Pipeline] Error processing block {i}: {e}")
                
                # Try AI fallback as last resort
                try:
                    ai_fields, ai_confidence = self.ai_strategy.extract(block)
                    if ai_fields and isinstance(ai_fields, dict):
                        # Format AI fields properly
                        formatted_ai_fields = {}
                        for field_name, field_data in ai_fields.items():
                            if isinstance(field_data, dict):
                                formatted_ai_fields[field_name] = field_data
                            else:
                                formatted_ai_fields[field_name] = {
                                    'value': field_data,
                                    'confidence': ai_confidence,
                                    'provenance': 'ai_error_fallback'
                                }
                        
                        ai_result = {
                            'fields': formatted_ai_fields,
                            'confidence': ai_confidence,
                            'provenance': 'ai_error_fallback'
                        }
                        extraction_results.append(ai_result)
                        ai_fallback_count += 1
                        logger.debug(f"[Pipeline] Block {i}: AI error fallback: {ai_result}")
                    else:
                        # Complete fallback
                        extraction_results.append({
                            'fields': {},
                            'confidence': 0.0,
                            'provenance': 'error'
                        })
                        
                except Exception as e2:
                    logger.error(f"[Pipeline] AI fallback also failed for block {i}: {e2}")
                    extraction_results.append({
                        'fields': {},
                        'confidence': 0.0,
                        'provenance': 'error'
                    })
        
        logger.info(f"[Pipeline] Applied rules with {db_only_count} database-only, {ai_fallback_count} AI fallbacks out of {len(wine_blocks)} entries")
        return extraction_results
    
    def _merge_early_and_rule_results(self, rule_result: Dict[str, Any], early_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge early database results with rule results, prioritizing database for all fields if higher confidence."""
        merged_fields = rule_result.get('fields', {}).copy()
        # Merge all fields from early_result if they have higher confidence or are missing in rules
        for field, db_value in early_result.items():
            if isinstance(db_value, dict) and db_value.get('value') is not None:
                if field not in merged_fields or db_value.get('confidence', 0) > merged_fields[field].get('confidence', 0):
                    merged_fields[field] = db_value
        # Recalculate overall confidence
        total_confidence = 0
        field_count = 0
        for field_data in merged_fields.values():
            if isinstance(field_data, dict) and 'confidence' in field_data:
                total_confidence += field_data['confidence']
                field_count += 1
        avg_confidence = total_confidence / field_count if field_count > 0 else 0.0
        return {
            'fields': merged_fields,
            'confidence': avg_confidence,
            'provenance': 'hybrid_database_rules',
            'applied_rules': rule_result.get('applied_rules', 0),
            'fields_extracted': len(merged_fields)
        }
    
    def _merge_ai_fallback_results(self, rule_result: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge AI fallback results with rule results, prioritizing AI for missing or low-confidence fields."""
        rule_fields = rule_result.get('fields', {}).copy()
        ai_fields = ai_result.get('fields', {})
        
        # Track improvements made by AI fallback
        ai_improvements = 0
        pattern_fallbacks = 0
        
        # Merge AI fields into rule fields
        for field_name, ai_field_data in ai_fields.items():
            if isinstance(ai_field_data, dict):
                ai_value = ai_field_data.get('value')
                ai_conf = ai_field_data.get('confidence', 0.0)
                ai_provenance = ai_field_data.get('provenance', 'ai_fallback')
                
                if ai_value and ai_value != 'null' and ai_value != '':
                    rule_field = rule_fields.get(field_name, {})
                    rule_value = rule_field.get('value') if isinstance(rule_field, dict) else rule_field
                    rule_conf = rule_field.get('confidence', 0.0) if isinstance(rule_field, dict) else 0.0
                    
                    # Use AI if field is missing or AI has higher confidence
                    if not rule_value or ai_conf > rule_conf:
                        rule_fields[field_name] = {
                            'value': ai_value,
                            'confidence': ai_conf,
                            'provenance': ai_provenance
                        }
                        
                        # Track the type of improvement
                        if ai_provenance == 'ai_fallback':
                            ai_improvements += 1
                        elif ai_provenance in ['pattern_fallback', 'pattern_fallback_only']:
                            pattern_fallbacks += 1
        
        # Recalculate overall confidence
        total_confidence = 0
        field_count = 0
        for field_data in rule_fields.values():
            if isinstance(field_data, dict) and 'confidence' in field_data:
                total_confidence += field_data['confidence']
                field_count += 1
        
        avg_confidence = total_confidence / field_count if field_count > 0 else 0.0
        
        # Enhanced provenance tracking
        provenance = 'hybrid_rules_ai_fallback'
        if ai_improvements > 0 and pattern_fallbacks > 0:
            provenance = 'hybrid_rules_ai_pattern_fallback'
        elif ai_improvements > 0:
            provenance = 'hybrid_rules_ai_fallback'
        elif pattern_fallbacks > 0:
            provenance = 'hybrid_rules_pattern_fallback'
        
        return {
            'fields': rule_fields,
            'confidence': avg_confidence,
            'provenance': provenance,
            'applied_rules': rule_result.get('applied_rules', 0),
            'fields_extracted': len(rule_fields),
            'ai_improvements': ai_improvements,
            'pattern_fallbacks': pattern_fallbacks
        }
    
    def _prepare_final_results(self, extraction_results: List[Dict[str, Any]], 
                             validation_results: Optional[Dict[str, Any]], 
                             start_time: datetime, iteration_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare final results with metadata."""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Ensure extraction_results is not None
        if extraction_results is None:
            logger.error("[_prepare_final_results] extraction_results was None, using empty list")
            extraction_results = []
        
        # Calculate statistics
        total_entries = len(extraction_results)
        ai_fallback_count = sum(1 for result in extraction_results 
                              if result and result.get('provenance') == 'ai_fallback')
        
        # Calculate average confidence - handle both 'confidence' and 'overall_confidence' fields
        confidences = []
        for result in extraction_results:
            if result:
                # Check for confidence in various possible field names
                confidence = None
                if 'confidence' in result:
                    confidence = result['confidence']
                elif 'overall_confidence' in result:
                    confidence = result['overall_confidence']
                
                if confidence is not None and isinstance(confidence, (int, float)):
                    confidences.append(float(confidence))
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Add iteration metadata to final results
        final_metadata = {
            'total_entries': total_entries,
            'ai_fallback_count': ai_fallback_count,
            'ai_fallback_rate': ai_fallback_count / total_entries if total_entries > 0 else 0,
            'average_confidence': avg_confidence,
            'processing_time_seconds': processing_time,
            'validation_results': validation_results,
            'processing_method': 'hybrid_ai_rules',
            'cache_hit': False
        }
        
        if iteration_metadata:
            final_metadata.update(iteration_metadata)
        
        return {
            'extraction_results': extraction_results,
            'metadata': final_metadata
        }
    
    def _fallback_to_ai_extraction(self, wine_blocks: List[Dict[str, Any]], 
                                 start_time: datetime) -> Dict[str, Any]:
        """Fallback to pure AI extraction if hybrid pipeline fails."""
        logger.warning("Falling back to pure AI extraction")
        
        try:
            extraction_results = self.ai_strategy.extract_batch(wine_blocks)
            
            # Ensure extraction_results is not None
            if extraction_results is None:
                logger.error("[_fallback_to_ai_extraction] AI extraction returned None, creating empty results")
                extraction_results = []
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'extraction_results': extraction_results,
                'metadata': {
                    'total_entries': len(wine_blocks),
                    'ai_fallback_count': len(wine_blocks),
                    'ai_fallback_rate': 1.0,
                    'processing_time_seconds': processing_time,
                    'processing_method': 'pure_ai_fallback',
                    'cache_hit': False,
                    'error': 'Hybrid pipeline failed, used AI fallback'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in AI fallback: {str(e)}")
            return {
                'extraction_results': [],
                'metadata': {
                    'error': f"Both hybrid and AI extraction failed: {str(e)}",
                    'processing_method': 'failed',
                    'total_entries': len(wine_blocks),
                    'ai_fallback_count': 0,
                    'ai_fallback_rate': 0.0,
                    'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
                }
            }
    
    def _save_restaurant_rules(self, rules: Dict[str, Any], validation_results: Optional[Dict[str, Any]]) -> None:
        """Save rules to restaurant-specific storage."""
        try:
            rules_with_metadata = {
                'rules': rules,
                'metadata': {
                    'restaurant_id': self.restaurant_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'validation_results': validation_results,
                    'rule_count': len(rules) if isinstance(rules, dict) else 0
                }
            }
            self.rule_manager.save_rules(self.restaurant_id, rules_with_metadata)
            logger.info(f"Successfully saved {len(rules) if isinstance(rules, dict) else 0} rules for restaurant {self.restaurant_id}")
        except Exception as e:
            logger.error(f"Error saving restaurant rules: {str(e)}")
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pipeline performance."""
        return {
            'restaurant_id': self.restaurant_id,
            'ai_rule_generation_enabled': AI_RULE_GENERATION_ENABLED,
            'confidence_threshold': self.confidence_threshold,
            'sample_size_ratio': SAMPLE_SIZE_RATIO,
            'min_sample_size': MIN_SAMPLE_SIZE,
            'max_sample_size': MAX_SAMPLE_SIZE
        }
    
    def _should_use_ai_fallback(self, result: Dict[str, Any], current_ai_count: int, total_blocks: int) -> bool:
        """
        Determine if AI fallback should be used based on multiple criteria.
        
        Args:
            result: Current extraction result
            current_ai_count: Number of AI fallbacks already used
            total_blocks: Total number of blocks to process
            
        Returns:
            True if AI fallback should be used
        """
        # Check if we've hit the AI usage limit
        if current_ai_count >= self.ai_fallback_max_entries:
            logger.debug(f"[Pipeline] AI fallback limit reached ({current_ai_count}/{self.ai_fallback_max_entries})")
            return False
        
        # Check if we should sample based on ratio
        if total_blocks > 10:  # Only apply sampling for larger files
            max_ai_entries = min(self.ai_fallback_max_entries, int(total_blocks * self.ai_fallback_sample_ratio))
            if current_ai_count >= max_ai_entries:
                logger.debug(f"[Pipeline] AI sampling limit reached ({current_ai_count}/{max_ai_entries})")
                return False
        
        confidence = result.get('confidence', 0.0)
        fields = result.get('fields', {})
        fields_count = len([f for f in fields.values() if isinstance(f, dict) and f.get('value')])
        
        # Use AI fallback if:
        # 1. Confidence is very low (< 40%)
        # 2. OR confidence is low (< 60%) AND few fields extracted (< 3)
        # 3. OR no fields extracted at all
        
        if confidence < 0.4:
            logger.debug(f"[Pipeline] AI fallback triggered: Very low confidence ({confidence:.2f})")
            return True
        
        if confidence < 0.6 and fields_count < self.min_fields_threshold:
            logger.debug(f"[Pipeline] AI fallback triggered: Low confidence ({confidence:.2f}) and few fields ({fields_count})")
            return True
        
        if fields_count == 0:
            logger.debug(f"[Pipeline] AI fallback triggered: No fields extracted")
            return True
        
        return False
    
    def _ai_provides_improvement(self, current_fields: Dict[str, Any], ai_fields: Dict[str, Any]) -> bool:
        """
        Check if AI results provide meaningful improvements over current results.
        
        Args:
            current_fields: Current extracted fields
            ai_fields: AI extracted fields
            
        Returns:
            True if AI provides meaningful improvements
        """
        if not ai_fields:
            return False
        
        improvements = 0
        critical_fields = ['producer', 'vintage', 'price', 'grape_variety']
        
        for field_name, ai_field_data in ai_fields.items():
            if not isinstance(ai_field_data, dict):
                continue
                
            ai_value = ai_field_data.get('value')
            if not ai_value or ai_value in ['null', '', 'None']:
                continue
            
            current_field = current_fields.get(field_name, {})
            current_value = current_field.get('value') if isinstance(current_field, dict) else current_field
            
            # Count as improvement if:
            # 1. Field is missing in current results
            # 2. Field is critical (producer, vintage, price, grape_variety)
            # 3. Field has higher confidence
            
            if not current_value:
                improvements += 1
                if field_name in critical_fields:
                    improvements += 1  # Extra weight for critical fields
            else:
                # Check if AI has higher confidence
                ai_conf = ai_field_data.get('confidence', 0.0)
                current_conf = current_field.get('confidence', 0.0) if isinstance(current_field, dict) else 0.0
                if ai_conf > current_conf + 0.1:  # 10% improvement threshold
                    improvements += 1
        
        # Require at least 2 improvements or 1 critical field improvement
        return improvements >= 2
    
    def _perform_early_database_extraction(self, wine_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform early database extraction before rule processing."""
        logger.info(f"[EarlyDB] 🗄️ Starting early database extraction for {len(wine_blocks)} wine blocks")
        
        # Check if database integration is enabled
        if not DATABASE_INTEGRATION_ENABLED or not self.early_extractor:
            logger.info("[EarlyDB] ❌ Database integration disabled, skipping early extraction")
            return [{} for _ in wine_blocks]
        
        early_results = []
        processed_count = 0
        
        for i, block in enumerate(wine_blocks):
            try:
                # Log progress every 50 blocks
                if i % 50 == 0:
                    logger.info(f"[EarlyDB] 📊 Processing block {i}/{len(wine_blocks)} ({(i/len(wine_blocks)*100):.1f}%)")
                
                # Extract text from block
                text = block.get('text', '')
                if not text:
                    early_results.append({})
                    continue
                
                # Perform early extraction
                early_extraction = self.early_extractor.extract_wine_info(text)
                
                # Convert to standard format
                result = {}
                confidence_sum = 0
                field_count = 0
                
                # Process grape variety
                if early_extraction.get('grape_variety'):
                    grape_conf = early_extraction.get('field_confidence', {}).get('grape_variety', 0.8)
                    result['grape_variety'] = {
                        'value': early_extraction['grape_variety'],
                        'confidence': grape_conf,
                        'provenance': 'database'
                    }
                    confidence_sum += grape_conf
                    field_count += 1
                
                # Process producer
                if early_extraction.get('producer'):
                    producer_conf = early_extraction.get('field_confidence', {}).get('producer', 0.8)
                    result['producer_name'] = {
                        'value': early_extraction['producer'],
                        'confidence': producer_conf,
                        'provenance': 'database'
                    }
                    confidence_sum += producer_conf
                    field_count += 1
                
                # Process region
                if early_extraction.get('region'):
                    region_conf = early_extraction.get('field_confidence', {}).get('region', 0.8)
                    result['region'] = {
                        'value': early_extraction['region'],
                        'confidence': region_conf,
                        'provenance': 'database'
                    }
                    confidence_sum += region_conf
                    field_count += 1
                
                # Process country
                if early_extraction.get('country'):
                    country_conf = early_extraction.get('field_confidence', {}).get('country', 0.8)
                    result['country'] = {
                        'value': early_extraction['country'],
                        'confidence': country_conf,
                        'provenance': 'database'
                    }
                    confidence_sum += country_conf
                    field_count += 1
                
                # Calculate average confidence
                avg_confidence = confidence_sum / field_count if field_count > 0 else 0.0
                
                # Add overall result metadata
                result['confidence'] = avg_confidence
                result['fields_extracted'] = field_count
                
                # Determine if we should skip AI (high confidence database extraction)
                if field_count >= 2 and avg_confidence >= 0.8:
                    result['skip_ai'] = True
                    logger.debug(f"[EarlyDB] Block {i}: High confidence database extraction ({avg_confidence:.2f}), skipping AI")
                
                early_results.append(result)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"[EarlyDB] 💥 Error in early database extraction for block {i}: {e}")
                early_results.append({})
        
        logger.info(f"[EarlyDB] ✅ Early database extraction completed for {len(wine_blocks)} blocks (processed: {processed_count})")
        return early_results 

    def _perform_iterative_rule_generation(self, wine_blocks: List[Dict[str, Any]], 
                                         extraction_results: List[Dict[str, Any]], 
                                         current_rules: Dict[str, Any],
                                         early_results: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform iterative rule generation by re-sampling from failed entries.
        
        Args:
            wine_blocks: Original wine blocks
            extraction_results: Results from initial rule application
            current_rules: Current generated rules
            early_results: Early database extraction results
            
        Returns:
            Tuple of (improved_rules, iteration_metadata)
        """
        logger.info("[Iterative] 🔄 Starting iterative rule generation")
        
        iteration_metadata = {
            'iterations_performed': 0,
            'failed_entries_identified': 0,
            'failed_entries_sampled': 0,
            'rules_improved': False,
            'confidence_improvement': 0.0,
            'field_coverage_improvement': 0.0
        }
        
        # Identify failed entries (missing fields or low confidence)
        failed_entries = self._identify_failed_entries(wine_blocks, extraction_results)
        iteration_metadata['failed_entries_identified'] = len(failed_entries)
        
        if len(failed_entries) == 0:
            logger.info("[Iterative] ✅ No failed entries identified, skipping iterative generation")
            return None, iteration_metadata
        
        logger.info(f"[Iterative] 📊 Identified {len(failed_entries)} failed entries")
        
        # Check if we have enough failed entries for meaningful re-sampling
        min_failed_entries = 3
        if len(failed_entries) < min_failed_entries:
            logger.info(f"[Iterative] ⚠️ Only {len(failed_entries)} failed entries (minimum {min_failed_entries}), skipping iterative generation")
            return None, iteration_metadata
        
        # Re-sample from failed entries
        failed_sample_size = min(10, len(failed_entries))  # Cap at 10 for cost efficiency
        failed_sample = self._sample_failed_entries(failed_entries, failed_sample_size)
        iteration_metadata['failed_entries_sampled'] = len(failed_sample)
        
        logger.info(f"[Iterative] 🎯 Re-sampled {len(failed_sample)} entries from failed entries")
        
        # Get AI extraction for failed sample
        logger.info(f"[Iterative] 🤖 Getting AI extraction for {len(failed_sample)} failed entries")
        failed_ai_results = self._get_ai_extraction(failed_sample)
        
        # Get initial extraction for failed sample
        logger.info(f"[Iterative] 🔧 Getting initial extraction for {len(failed_sample)} failed entries")
        failed_initial_results = self._get_initial_extraction(failed_sample)
        
        # Generate improved rules using failed sample
        logger.info(f"[Iterative] 🧠 Generating improved rules from failed sample")
        improved_rules = self._generate_improved_rules(
            failed_sample, failed_ai_results, failed_initial_results, current_rules
        )
        
        if not improved_rules:
            logger.info("[Iterative] ⚠️ No improved rules generated")
            return None, iteration_metadata
        
        # Validate improved rules
        logger.info(f"[Iterative] ✅ Validating improved rules")
        improved_validation = self._validate_generated_rules(improved_rules, wine_blocks)
        
        # Test improved rules on a subset of failed entries
        test_subset = failed_entries[:min(5, len(failed_entries))]
        improved_results = self._apply_rules_to_all_entries(test_subset, improved_rules)
        
        # Calculate improvements
        original_avg_confidence = self._calculate_average_confidence(extraction_results)
        improved_avg_confidence = self._calculate_average_confidence(improved_results)
        confidence_improvement = improved_avg_confidence - original_avg_confidence
        
        original_field_coverage = self._calculate_field_coverage(extraction_results)
        improved_field_coverage = self._calculate_field_coverage(improved_results)
        field_coverage_improvement = improved_field_coverage - original_field_coverage
        
        iteration_metadata.update({
            'iterations_performed': 1,
            'rules_improved': True,
            'confidence_improvement': confidence_improvement,
            'field_coverage_improvement': field_coverage_improvement,
            'original_avg_confidence': original_avg_confidence,
            'improved_avg_confidence': improved_avg_confidence,
            'original_field_coverage': original_field_coverage,
            'improved_field_coverage': improved_field_coverage
        })
        
        logger.info(f"[Iterative] 📈 Improvements: Confidence +{confidence_improvement:.3f}, Field Coverage +{field_coverage_improvement:.3f}")
        
        # Only use improved rules if they show significant improvement
        min_confidence_improvement = 0.05
        min_field_coverage_improvement = 0.05
        
        if confidence_improvement >= min_confidence_improvement or field_coverage_improvement >= min_field_coverage_improvement:
            logger.info(f"[Iterative] ✅ Significant improvements detected, using improved rules")
            return improved_rules, iteration_metadata
        else:
            logger.info(f"[Iterative] ⚠️ Insufficient improvements, keeping original rules")
            iteration_metadata['rules_improved'] = False
            return None, iteration_metadata

    def _identify_failed_entries(self, wine_blocks: List[Dict[str, Any]], 
                               extraction_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify entries that failed extraction (missing fields or low confidence)."""
        failed_entries = []
        
        for i, result in enumerate(extraction_results):
            if i >= len(wine_blocks):
                continue
                
            wine_block = wine_blocks[i]
            confidence = result.get('confidence', 0.0)
            fields = result.get('fields', {})
            
            # Count extracted fields
            extracted_fields = 0
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict):
                    value = field_data.get('value')
                else:
                    value = field_data
                if value and value != 'null' and value != '':
                    extracted_fields += 1
            
            # Consider failed if:
            # 1. Very low confidence (< 0.4)
            # 2. OR low confidence (< 0.6) and few fields extracted (< 3)
            # 3. OR no fields extracted at all
            is_failed = (
                confidence < 0.4 or
                (confidence < 0.6 and extracted_fields < 3) or
                extracted_fields == 0
            )
            
            if is_failed:
                failed_entries.append(wine_block)
        
        return failed_entries

    def _sample_failed_entries(self, failed_entries: List[Dict[str, Any]], 
                             sample_size: int) -> List[Dict[str, Any]]:
        """Sample from failed entries using intelligent sampling."""
        if len(failed_entries) <= sample_size:
            return failed_entries
        
        # Use intelligent sampling on failed entries
        try:
            sample = self.sampler.select_sample(failed_entries, sample_size)
            return sample
        except Exception as e:
            logger.warning(f"[Iterative] Error in intelligent sampling of failed entries: {e}")
            # Fallback to random sampling
            import random
            return random.sample(failed_entries, sample_size)

    def _generate_improved_rules(self, failed_sample: List[Dict[str, Any]], 
                               ai_results: List[Dict[str, Any]], 
                               initial_results: List[Dict[str, Any]], 
                               current_rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate improved rules using failed sample data."""
        try:
            # Generate new rules from failed sample
            new_rules = self._generate_ai_rules(failed_sample, ai_results, initial_results)
            
            if not new_rules:
                return None
            
            # Merge new rules with current rules
            improved_rules = self._merge_rules(current_rules, new_rules)
            
            return improved_rules
            
        except Exception as e:
            logger.error(f"[Iterative] Error generating improved rules: {e}")
            return None

    def _merge_rules(self, current_rules: Dict[str, Any], new_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new rules with current rules, prioritizing new patterns."""
        merged_rules = current_rules.copy()
        
        for field_name, new_field_rules in new_rules.items():
            if field_name not in merged_rules:
                merged_rules[field_name] = new_field_rules
            else:
                # Merge field rules
                current_field_rules = merged_rules[field_name]
                
                # Merge regex patterns
                if 'regex_patterns' in new_field_rules and 'regex_patterns' in current_field_rules:
                    current_patterns = current_field_rules['regex_patterns']
                    new_patterns = new_field_rules['regex_patterns']
                    
                    # Add new patterns that don't already exist
                    for pattern in new_patterns:
                        if pattern not in current_patterns:
                            current_patterns.append(pattern)
                
                # Merge other rule types similarly
                for rule_type in ['positional_rules', 'structural_rules', 'format_rules', 'validation_rules']:
                    if rule_type in new_field_rules and rule_type in current_field_rules:
                        current_rules_list = current_field_rules[rule_type]
                        new_rules_list = new_field_rules[rule_type]
                        
                        for rule in new_rules_list:
                            if rule not in current_rules_list:
                                current_rules_list.append(rule)
        
        return merged_rules

    def _calculate_average_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate average confidence from extraction results."""
        if not results:
            return 0.0
        
        total_confidence = sum(result.get('confidence', 0.0) for result in results)
        return total_confidence / len(results)

    def _calculate_field_coverage(self, results: List[Dict[str, Any]]) -> float:
        """Calculate field coverage (percentage of entries with at least 3 fields)."""
        if not results:
            return 0.0
        
        covered_entries = 0
        for result in results:
            fields = result.get('fields', {})
            extracted_fields = 0
            
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict):
                    value = field_data.get('value')
                else:
                    value = field_data
                if value and value != 'null' and value != '':
                    extracted_fields += 1
            
            if extracted_fields >= 3:
                covered_entries += 1
        
        return covered_entries / len(results) 