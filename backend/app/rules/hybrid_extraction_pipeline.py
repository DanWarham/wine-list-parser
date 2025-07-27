from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import os

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
    MIN_VALIDATION_ENTRIES, VALIDATION_SPLIT_RATIO
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
        self.early_extractor = EarlyExtractor()
        
        # Configure confidence threshold
        self.confidence_threshold = MIN_CONFIDENCE_THRESHOLD_HYBRID
    
    def process_wine_list(self, wine_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a wine list using the hybrid extraction pipeline.
        
        Args:
            wine_blocks: List of wine text blocks
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        logger.info("[Pipeline] Hybrid extraction pipeline started.")
        start_time = datetime.utcnow()
        logger.info(f"Starting hybrid extraction for {len(wine_blocks)} wine blocks")
        
        try:
            # Step 1: Check for restaurant-specific rules first
            restaurant_rules = self._check_restaurant_rules()
            if restaurant_rules:
                logger.info(f"Found existing rules for restaurant {self.restaurant_id}, using them")
                results = self._apply_restaurant_rules(wine_blocks, restaurant_rules)
                results['metadata']['restaurant_rules_used'] = True
                logger.info("[Pipeline] Used restaurant-specific rules. Extraction complete.")
                return results
            
            # Step 2: Intelligent sampling
            sample_entries = self._perform_intelligent_sampling(wine_blocks)
            logger.info(f"[Pipeline] Selected {len(sample_entries)} sample entries for rule generation: {[e.get('raw_text','')[:60] for e in sample_entries]}")
            
            # Step 3: Perform early database extraction
            early_results = self._perform_early_database_extraction(wine_blocks)
            logger.info(f"[Pipeline] Early database extraction completed. Example: {early_results[0] if early_results else 'None'}")
            
            # Step 4: Get initial extraction results for sample
            initial_results = self._get_initial_extraction(sample_entries)
            logger.info(f"[Pipeline] Initial extraction for sample complete. Example: {initial_results[0] if initial_results else 'None'}")
            
            # Step 5: Get AI extraction results for sample
            ai_results = self._get_ai_extraction(sample_entries)
            logger.info(f"[Pipeline] AI extraction for sample complete. Example: {ai_results[0] if ai_results else 'None'}")
            
            # Step 6: Generate AI rules
            if AI_RULE_GENERATION_ENABLED:
                generated_rules = self._generate_ai_rules(sample_entries, ai_results, initial_results)
                logger.info(f"[Pipeline] AI rule generation complete. Rule count: {len(generated_rules) if generated_rules else 0}")
            else:
                logger.info("[Pipeline] AI rule generation disabled, using existing rules")
                generated_rules = self.rule_manager.load_rules(self.restaurant_id)
            
            # Step 7: Validate rules (if we have enough test data)
            validation_results = self._validate_generated_rules(generated_rules, wine_blocks)
            logger.info(f"[Pipeline] Rule validation complete. Validation results: {validation_results}")
            
            # Step 8: Apply rules to all entries
            extraction_results = self._apply_rules_to_all_entries(wine_blocks, generated_rules)
            logger.info(f"[Pipeline] Rule application to all entries complete. Example: {extraction_results[0] if extraction_results else 'None'}")
            
            # Step 9: Save rules to restaurant-specific storage (database only)
            if generated_rules:
                self._save_restaurant_rules(generated_rules, validation_results)
                logger.info(f"[Pipeline] Saved rules for restaurant {self.restaurant_id}")
            
            # Step 10: Prepare final results
            final_results = self._prepare_final_results(
                extraction_results, validation_results, start_time
            )
            logger.info(f"[Pipeline] Final results preparation complete. Processed {len(extraction_results)} entries in {final_results.get('processing_time', '?')}s")

            logger.info(f"[Pipeline] Hybrid extraction completed successfully")
            return final_results
            
        except Exception as e:
            logger.error(f"[Pipeline] Error in hybrid extraction pipeline: {str(e)}")
            # Fallback to pure AI extraction
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
                # AI strategy extract returns (fields, confidence) tuple
                ai_fields, ai_confidence = self.ai_strategy.extract(block)
                
                # Ensure ai_fields is a dict and convert to expected format
                if ai_fields is None:
                    ai_fields = {}
                
                if not isinstance(ai_fields, dict):
                    ai_fields = {}
                
                # Convert ai_fields to the expected format with confidence scores
                formatted_ai_fields = {}
                for field_name, field_value in ai_fields.items():
                    if field_value is not None:
                        formatted_ai_fields[field_name] = {
                            'value': field_value,
                            'confidence': ai_confidence,
                            'provenance': 'ai_fallback'
                        }
                
                ai_result = {
                    'fields': formatted_ai_fields,
                    'overall_confidence': ai_confidence,
                    'provenance': 'ai_fallback'
                }
                final_result = self.rule_applicator.merge_results(rule_result, ai_result)
                ai_fallback_count += 1
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
        # Calculate sample size
        sample_size = max(
            MIN_SAMPLE_SIZE,
            min(MAX_SAMPLE_SIZE, int(len(wine_blocks) * SAMPLE_SIZE_RATIO))
        )
        
        return self.sampler.select_sample(wine_blocks, sample_size)
    
    def _get_initial_extraction(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get initial extraction results using current rules."""
        try:
            field_extractor = FieldExtractor(restaurant_id=self.restaurant_id)
            return field_extractor.extract_batch(sample_entries)
        except Exception as e:
            logger.error(f"Error in initial extraction: {str(e)}")
            return []
    
    def _get_ai_extraction(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get AI extraction results for sample entries."""
        try:
            results = self.ai_strategy.extract_batch(sample_entries)
            # Ensure we have the right number of results
            if len(results) != len(sample_entries):
                logger.warning(f"AI extraction returned {len(results)} results for {len(sample_entries)} entries")
                # Pad with empty results if needed
                while len(results) < len(sample_entries):
                    results.append({
                        'producer_name': {
                            'value': None,
                            'confidence': 0.0,
                            'provenance': 'ai_padding'
                        }
                    })
            return results
        except Exception as e:
            logger.error(f"Error in AI extraction: {str(e)}")
            # Return empty results for all entries
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
        try:
            logger.info("Generating AI rules from sample entries")
            rules_result = self.ai_rule_generator.generate_rules(
                sample_entries, ai_results, initial_results
            )
            
            if 'error' in rules_result:
                logger.error(f"Error generating AI rules: {rules_result['error']}")
                return {}
            
            # Save rules to restaurant-specific storage
            if rules_result.get('rules'):
                self.rule_manager.update_rules(self.restaurant_id, rules_result['rules'])
            
            return rules_result.get('rules', {})
            
        except Exception as e:
            logger.error(f"Error in AI rule generation: {str(e)}")
            return {}
    
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
            logger.debug(f"[Pipeline] Processing block {i}: {block.get('raw_text','')[:80]}")
            early_result = early_results[i] if i < len(early_results) else {}
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
                rule_result = self.rule_applicator.apply_rules(block, rules)
                logger.debug(f"[Pipeline] Block {i}: Rule result: {rule_result}")
                final_result = self._merge_early_and_rule_results(rule_result, early_result)
                logger.debug(f"[Pipeline] Block {i}: After merging with early extraction: {final_result}")
                if final_result['confidence'] < self.confidence_threshold:
                    logger.debug(f"[Pipeline] Block {i}: Low confidence ({final_result['confidence']:.2f}), using AI fallback")
                    ai_fields, ai_confidence = self.ai_strategy.extract(block)
                    if ai_fields and ai_confidence > final_result['confidence']:
                        ai_result = {
                            'fields': ai_fields,
                            'confidence': ai_confidence,
                            'provenance': 'ai_fallback'
                        }
                        final_result = ai_result
                        ai_fallback_count += 1
                        logger.debug(f"[Pipeline] Block {i}: AI fallback result: {ai_result}")
                extraction_results.append(final_result)
            except Exception as e:
                logger.error(f"[Pipeline] Error processing block {i}: {e}")
                try:
                    ai_fields, ai_confidence = self.ai_strategy.extract(block)
                    ai_result = {
                        'fields': ai_fields,
                        'confidence': ai_confidence,
                        'provenance': 'ai_fallback'
                    }
                    extraction_results.append(ai_result)
                    ai_fallback_count += 1
                    logger.debug(f"[Pipeline] Block {i}: AI fallback after error: {ai_result}")
                except Exception as e2:
                    logger.error(f"[Pipeline] AI fallback also failed for block {i}: {e2}")
                    extraction_results.append({'fields': {}, 'confidence': 0.0, 'provenance': 'error'})
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
    
    def _prepare_final_results(self, extraction_results: List[Dict[str, Any]], 
                             validation_results: Optional[Dict[str, Any]], 
                             start_time: datetime) -> Dict[str, Any]:
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
        
        # Calculate average confidence
        confidences = []
        for result in extraction_results:
            if result and 'overall_confidence' in result:
                confidences.append(result['overall_confidence'])
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'extraction_results': extraction_results,
            'metadata': {
                'total_entries': total_entries,
                'ai_fallback_count': ai_fallback_count,
                'ai_fallback_rate': ai_fallback_count / total_entries if total_entries > 0 else 0,
                'average_confidence': avg_confidence,
                'processing_time_seconds': processing_time,
                'validation_results': validation_results,
                'processing_method': 'hybrid_ai_rules',
                'cache_hit': False
            }
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
    
    def _perform_early_database_extraction(self, wine_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform early database extraction before rule processing."""
        logger.info("[Pipeline] Performing early database extraction...")
        
        early_results = []
        for block in wine_blocks:
            try:
                # Extract text from block
                text = block.get('text', '')
                if not text:
                    early_results.append({})
                    continue
                
                # Perform early extraction
                early_extraction = self.early_extractor.extract_wine_info(text)
                
                # Convert to standard format
                result = {}
                if early_extraction.get('grape_variety'):
                    result['grape_variety'] = {
                        'value': early_extraction['grape_variety'],
                        'confidence': early_extraction['field_confidence'].get('grape_variety', 0.0),
                        'provenance': 'database'
                    }
                
                if early_extraction.get('producer'):
                    result['producer_name'] = {
                        'value': early_extraction['producer'],
                        'confidence': early_extraction['field_confidence'].get('producer', 0.0),
                        'provenance': 'database'
                    }
                
                if early_extraction.get('region'):
                    result['region'] = {
                        'value': early_extraction['region'],
                        'confidence': early_extraction['field_confidence'].get('region', 0.0),
                        'provenance': 'database'
                    }
                
                if early_extraction.get('country'):
                    result['country'] = {
                        'value': early_extraction['country'],
                        'confidence': early_extraction['field_confidence'].get('country', 0.0),
                        'provenance': 'database'
                    }
                
                early_results.append(result)
                
            except Exception as e:
                logger.error(f"Error in early database extraction: {e}")
                early_results.append({})
        
        logger.info(f"[Pipeline] Early database extraction completed for {len(wine_blocks)} blocks")
        return early_results 