from typing import List, Dict, Any, Optional
from .rule_manager import RuleManager
from .hybrid_extraction_pipeline import HybridExtractionPipeline
from app.fieldextractor.fieldextractor import FieldExtractor
from app.fieldextractor.strategies.regex_strategy import RegexStrategy
from app.fieldextractor.strategies.ai_strategy import AIStrategy
from app.config import AI_RULE_GENERATION_ENABLED
import logging

logger = logging.getLogger(__name__)

class RuleLearner:
    def __init__(self, restaurant_id: str):
        self.restaurant_id = restaurant_id
        self.rule_manager = RuleManager()
        self.ai_strategy = AIStrategy()
        self.regex_strategy = RegexStrategy()
        # Only use hybrid pipeline
        self.hybrid_pipeline = None
        if AI_RULE_GENERATION_ENABLED:
            try:
                self.hybrid_pipeline = HybridExtractionPipeline(restaurant_id)
                logger.info(f"Initialized hybrid pipeline for restaurant {restaurant_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid pipeline: {str(e)}")

    def analyze_entries(self, entries: List[Dict[str, Any]], sample_size: int = 3) -> Dict[str, Any]:
        """Analyze entries and generate rules using the AI Hybrid Rule Generation System only."""
        try:
            logger.info(f"Starting rule learning for restaurant {self.restaurant_id} with {len(entries)} entries")
            if self.hybrid_pipeline and AI_RULE_GENERATION_ENABLED:
                logger.info("Using AI Hybrid Rule Generation System")
                return self._analyze_entries_hybrid(entries)
            else:
                logger.error("Hybrid pipeline not available or not enabled.")
                return {"summary": "Hybrid pipeline not available", "new_rules": []}
        except Exception as e:
            logger.error(f"Error in rule learning: {str(e)}")
            return {"summary": f"Error in rule learning: {str(e)}", "new_rules": []}

    def _analyze_entries_hybrid(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            wine_blocks = self._convert_entries_to_blocks(entries)
            
            # Enhanced analysis with cross-strategy coordination
            analysis_results = self._perform_enhanced_analysis(wine_blocks)
            
            # Use hybrid pipeline for rule generation
            pipeline_results = self.hybrid_pipeline.process_wine_list(wine_blocks)
            metadata = pipeline_results.get('metadata', {})
            
            # Combine analysis results with pipeline results
            summary = {
                'total_entries': metadata.get('total_entries', len(entries)),
                'ai_fallback_count': metadata.get('ai_fallback_count', 0),
                'ai_fallback_rate': metadata.get('ai_fallback_rate', 0),
                'average_confidence': metadata.get('average_confidence', 0),
                'processing_time_seconds': metadata.get('processing_time_seconds', 0),
                'ai_enhanced': True,
                'processing_method': metadata.get('processing_method', 'hybrid_ai_rules'),
                'rules_generated': 1 if metadata.get('processing_method') == 'hybrid_ai_rules' else 0,
                'cross_strategy_analysis': analysis_results.get('cross_strategy_analysis', {}),
                'database_coverage': analysis_results.get('database_coverage', 0),
                'ner_coverage': analysis_results.get('ner_coverage', 0),
                'strategy_agreement_rate': analysis_results.get('strategy_agreement_rate', 0)
            }
            
            current_rules = self.rule_manager.load_rules(self.restaurant_id)
            return {
                'summary': summary,
                'new_rules': current_rules,
                'pipeline_results': pipeline_results,
                'hybrid_system_used': True,
                'enhanced_analysis': analysis_results
            }
        except Exception as e:
            logger.error(f"Error in hybrid analysis: {str(e)}")
            return {"summary": f"Error in hybrid analysis: {str(e)}", "new_rules": []}
    
    def _perform_enhanced_analysis(self, wine_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform enhanced analysis with cross-strategy coordination."""
        try:
            from app.database_enhanced_rules.database_manager import DatabaseManager
            from app.database_enhanced_rules.early_extractor import EarlyExtractor
            from app.fieldextractor.strategies.ner_strategy import NERStrategy
            
            # Initialize strategies
            db_manager = DatabaseManager()
            early_extractor = EarlyExtractor(db_manager)
            ner_strategy = NERStrategy()
            
            # Collect results from all strategies
            strategy_results = {
                'database': [],
                'ner': [],
                'regex': [],
                'ai': []
            }
            
            # Analyze each block with all strategies
            for block in wine_blocks:
                text = block.get('text', '')
                if not text:
                    continue
                
                # Database extraction
                try:
                    db_result = early_extractor.extract_wine_info(text)
                    strategy_results['database'].append(db_result)
                except Exception as e:
                    logger.warning(f"Database extraction failed: {e}")
                    strategy_results['database'].append({})
                
                # NER extraction
                try:
                    ner_fields, ner_conf = ner_strategy.extract(block)
                    strategy_results['ner'].append({
                        'fields': ner_fields,
                        'confidence': ner_conf,
                        'provenance': 'ner'
                    })
                except Exception as e:
                    logger.warning(f"NER extraction failed: {e}")
                    strategy_results['ner'].append({'fields': {}, 'confidence': 0.0})
                
                # Regex extraction
                try:
                    regex_fields, regex_conf = self.regex_strategy.extract(block)
                    strategy_results['regex'].append({
                        'fields': regex_fields,
                        'confidence': regex_conf,
                        'provenance': 'regex'
                    })
                except Exception as e:
                    logger.warning(f"Regex extraction failed: {e}")
                    strategy_results['regex'].append({'fields': {}, 'confidence': 0.0})
                
                # AI extraction
                try:
                    ai_fields, ai_conf = self.ai_strategy.extract(block)
                    strategy_results['ai'].append({
                        'fields': ai_fields,
                        'confidence': ai_conf,
                        'provenance': 'ai'
                    })
                except Exception as e:
                    logger.warning(f"AI extraction failed: {e}")
                    strategy_results['ai'].append({'fields': {}, 'confidence': 0.0})
            
            # Analyze cross-strategy patterns
            cross_strategy_analysis = self._analyze_cross_strategy_patterns(strategy_results)
            
            # Calculate coverage metrics
            coverage_metrics = self._calculate_coverage_metrics(strategy_results)
            
            # Generate strategy-specific insights
            strategy_insights = self._generate_strategy_insights(strategy_results)
            
            return {
                'cross_strategy_analysis': cross_strategy_analysis,
                'coverage_metrics': coverage_metrics,
                'strategy_insights': strategy_insights,
                'database_coverage': coverage_metrics.get('database_coverage', 0),
                'ner_coverage': coverage_metrics.get('ner_coverage', 0),
                'strategy_agreement_rate': cross_strategy_analysis.get('agreement_rate', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {e}")
            return {
                'cross_strategy_analysis': {},
                'coverage_metrics': {},
                'strategy_insights': {},
                'database_coverage': 0,
                'ner_coverage': 0,
                'strategy_agreement_rate': 0
            }
    
    def _analyze_cross_strategy_patterns(self, strategy_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze patterns across different strategies."""
        analysis = {
            'agreement_rate': 0.0,
            'field_agreement': {},
            'strategy_strengths': {},
            'conflict_patterns': [],
            'synergy_opportunities': []
        }
        
        # Calculate agreement rates for each field
        fields_to_analyze = ['producer_name', 'region', 'country', 'grape_variety', 'vintage', 'price']
        
        for field in fields_to_analyze:
            agreements = 0
            total_blocks = len(strategy_results['database'])
            
            for i in range(total_blocks):
                field_found_by = []
                
                # Check which strategies found this field
                for strategy, results in strategy_results.items():
                    if i < len(results):
                        result = results[i]
                        if strategy == 'database':
                            if result.get(field) or result.get('producer') or result.get('region') or result.get('country'):
                                field_found_by.append(strategy)
                        else:
                            fields = result.get('fields', {})
                            if field in fields and fields[field].get('value'):
                                field_found_by.append(strategy)
                
                if len(field_found_by) > 1:
                    agreements += 1
            
            agreement_rate = agreements / total_blocks if total_blocks > 0 else 0.0
            analysis['field_agreement'][field] = agreement_rate
        
        # Calculate overall agreement rate
        total_agreements = sum(analysis['field_agreement'].values())
        analysis['agreement_rate'] = total_agreements / len(fields_to_analyze) if fields_to_analyze else 0.0
        
        # Analyze strategy strengths
        for strategy, results in strategy_results.items():
            total_confidence = 0.0
            total_fields = 0
            
            for result in results:
                if strategy == 'database':
                    # Count database fields
                    for field in ['producer', 'region', 'country', 'grape_variety']:
                        if result.get(field):
                            total_confidence += result.get('confidence', 0.0)
                            total_fields += 1
                else:
                    fields = result.get('fields', {})
                    for field_data in fields.values():
                        if isinstance(field_data, dict) and 'confidence' in field_data:
                            total_confidence += field_data['confidence']
                            total_fields += 1
            
            avg_confidence = total_confidence / total_fields if total_fields > 0 else 0.0
            analysis['strategy_strengths'][strategy] = {
                'average_confidence': avg_confidence,
                'total_fields_extracted': total_fields
            }
        
        return analysis
    
    def _calculate_coverage_metrics(self, strategy_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate coverage metrics for each strategy."""
        metrics = {}
        
        total_blocks = len(strategy_results['database'])
        
        for strategy, results in strategy_results.items():
            covered_blocks = 0
            
            for result in results:
                if strategy == 'database':
                    # Check if database found any useful information
                    if (result.get('producer') or result.get('region') or 
                        result.get('country') or result.get('grape_variety')):
                        covered_blocks += 1
                else:
                    fields = result.get('fields', {})
                    if fields:  # If any fields were extracted
                        covered_blocks += 1
            
            coverage_rate = covered_blocks / total_blocks if total_blocks > 0 else 0.0
            metrics[f'{strategy}_coverage'] = coverage_rate
        
        return metrics
    
    def _generate_strategy_insights(self, strategy_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Generate insights about strategy performance."""
        insights = {
            'recommended_strategy_order': [],
            'database_effectiveness': {},
            'ner_effectiveness': {},
            'regex_effectiveness': {},
            'ai_effectiveness': {}
        }
        
        # Analyze database effectiveness
        db_insights = self._analyze_database_effectiveness(strategy_results['database'])
        insights['database_effectiveness'] = db_insights
        
        # Analyze NER effectiveness
        ner_insights = self._analyze_ner_effectiveness(strategy_results['ner'])
        insights['ner_effectiveness'] = ner_insights
        
        # Generate recommended strategy order
        insights['recommended_strategy_order'] = self._generate_strategy_order(insights)
        
        return insights
    
    def _analyze_database_effectiveness(self, db_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze database strategy effectiveness."""
        analysis = {
            'producer_match_rate': 0.0,
            'region_match_rate': 0.0,
            'country_match_rate': 0.0,
            'grape_variety_match_rate': 0.0,
            'high_confidence_matches': 0,
            'total_blocks': len(db_results)
        }
        
        if not db_results:
            return analysis
        
        producer_matches = sum(1 for r in db_results if r.get('producer'))
        region_matches = sum(1 for r in db_results if r.get('region'))
        country_matches = sum(1 for r in db_results if r.get('country'))
        grape_matches = sum(1 for r in db_results if r.get('grape_variety'))
        high_conf_matches = sum(1 for r in db_results if r.get('confidence', 0) > 0.8)
        
        analysis['producer_match_rate'] = producer_matches / len(db_results)
        analysis['region_match_rate'] = region_matches / len(db_results)
        analysis['country_match_rate'] = country_matches / len(db_results)
        analysis['grape_variety_match_rate'] = grape_matches / len(db_results)
        analysis['high_confidence_matches'] = high_conf_matches
        
        return analysis
    
    def _analyze_ner_effectiveness(self, ner_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze NER strategy effectiveness."""
        analysis = {
            'entity_types_found': {},
            'average_confidence': 0.0,
            'total_entities': 0,
            'total_blocks': len(ner_results)
        }
        
        if not ner_results:
            return analysis
        
        total_confidence = 0.0
        total_entities = 0
        entity_counts = {}
        
        for result in ner_results:
            fields = result.get('fields', {})
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict) and 'confidence' in field_data:
                    total_confidence += field_data['confidence']
                    total_entities += 1
                    
                    # Count entity types (simplified mapping)
                    if field_name in ['producer_name']:
                        entity_type = 'ORG'
                    elif field_name in ['region', 'country']:
                        entity_type = 'GPE'
                    elif field_name in ['wine_name']:
                        entity_type = 'PRODUCT'
                    elif field_name in ['vintage']:
                        entity_type = 'DATE'
                    else:
                        entity_type = 'MISC'
                    
                    entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        analysis['entity_types_found'] = entity_counts
        analysis['average_confidence'] = total_confidence / total_entities if total_entities > 0 else 0.0
        analysis['total_entities'] = total_entities
        
        return analysis
    
    def _generate_strategy_order(self, insights: Dict[str, Any]) -> List[str]:
        """Generate recommended strategy order based on insights."""
        # Default order
        default_order = ['database', 'ner', 'regex', 'ai']
        
        # Adjust based on database effectiveness
        db_effectiveness = insights.get('database_effectiveness', {})
        if db_effectiveness.get('high_confidence_matches', 0) > 0:
            # Database is effective, keep it first
            pass
        else:
            # Database not effective, move it down
            default_order.remove('database')
            default_order.append('database')
        
        # Adjust based on NER effectiveness
        ner_effectiveness = insights.get('ner_effectiveness', {})
        if ner_effectiveness.get('total_entities', 0) > 0:
            # NER found entities, keep it high
            pass
        else:
            # NER not effective, move it down
            default_order.remove('ner')
            default_order.append('ner')
        
        return default_order

    def _convert_entries_to_blocks(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        wine_blocks = []
        for entry in entries:
            text = entry.get('text', '')
            if not text:
                text = self._reconstruct_text_from_fields(entry)
            if text:
                wine_blocks.append({'text': text, 'original_entry': entry})
        return wine_blocks

    def _reconstruct_text_from_fields(self, entry: Dict[str, Any]) -> str:
        parts = []
        producer = entry.get('producer_name') or entry.get('producer')
        if producer:
            if isinstance(producer, dict):
                producer = producer.get('value', '')
            parts.append(str(producer))
        wine_name = entry.get('wine_name') or entry.get('cuvee')
        if wine_name:
            if isinstance(wine_name, dict):
                wine_name = wine_name.get('value', '')
            parts.append(str(wine_name))
        vintage = entry.get('vintage')
        if vintage:
            if isinstance(vintage, dict):
                vintage = vintage.get('value', '')
            parts.append(str(vintage))
        region = entry.get('region')
        if region:
            if isinstance(region, dict):
                region = region.get('value', '')
            parts.append(str(region))
        price = entry.get('price')
        if price:
            if isinstance(price, dict):
                price = price.get('value', '')
            parts.append(str(price))
        return ' '.join(parts)

    def get_learning_statistics(self) -> Dict[str, Any]:
        stats = {
            'restaurant_id': self.restaurant_id,
            'hybrid_pipeline_available': self.hybrid_pipeline is not None,
            'ai_rule_generation_enabled': AI_RULE_GENERATION_ENABLED
        }
        if self.hybrid_pipeline:
            stats.update(self.hybrid_pipeline.get_pipeline_statistics())
        return stats 