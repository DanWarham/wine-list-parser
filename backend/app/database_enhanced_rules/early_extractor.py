"""
Early Extractor for Database-Enhanced Rule System

This module performs early database lookups to extract wine information
before falling back to AI/rule processing, reducing costs and improving efficiency.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class EarlyExtractor:
    """Performs early extraction using local databases before AI/rule processing."""
    
    def __init__(self, database_manager: DatabaseManager = None):
        """
        Initialize the early extractor.
        
        Args:
            database_manager: Database manager instance (optional)
        """
        self.db_manager = database_manager or DatabaseManager()
        self.confidence_threshold = 0.6  # Will be updated from config
        self._update_config_threshold()
        
        logger.info("EarlyExtractor initialized")
    
    def _update_config_threshold(self):
        """Update confidence threshold from config."""
        try:
            from app.config import EARLY_EXTRACTOR_CONFIDENCE_THRESHOLD
            self.confidence_threshold = EARLY_EXTRACTOR_CONFIDENCE_THRESHOLD
            logger.info(f"Updated confidence threshold to {self.confidence_threshold}")
        except ImportError:
            logger.warning("Could not import config, using default threshold")
    
    def extract_wine_info(self, wine_text: str) -> Dict[str, Any]:
        """
        Extract wine information from text using local databases.
        
        Args:
            wine_text: Raw wine text to extract from
            
        Returns:
            Dictionary with extracted fields and confidence scores
        """
        result = {
            'grape_variety': None,
            'producer': None,
            'region': None,
            'country': None,
            'confidence': 0.0,
            'extraction_method': 'database',
            'field_confidence': {}
        }
        
        # Normalize text for better matching
        normalized_text = self._normalize_text(wine_text)
        
        # Extract grape variety
        grape_result = self._extract_grape_variety(normalized_text)
        if grape_result:
            result['grape_variety'] = grape_result['name']
            result['field_confidence']['grape_variety'] = grape_result['confidence']
        
        # Extract producer
        producer_result = self._extract_producer(normalized_text)
        if producer_result:
            result['producer'] = producer_result['name']
            result['field_confidence']['producer'] = producer_result['confidence']
        
        # Extract region/country
        region_result = self._extract_region(normalized_text)
        if region_result:
            result['region'] = region_result['region']
            result['country'] = region_result['country']
            result['field_confidence']['region'] = region_result['confidence']
            result['field_confidence']['country'] = region_result['confidence']
        
        # Calculate overall confidence
        confidences = list(result['field_confidence'].values())
        if confidences:
            result['confidence'] = sum(confidences) / len(confidences)
        
        # Determine if we should skip AI processing
        if result['confidence'] >= self.confidence_threshold:
            result['skip_ai'] = True
            logger.info(f"High confidence database extraction ({result['confidence']:.2f}), skipping AI")
        else:
            result['skip_ai'] = False
            logger.info(f"Low confidence database extraction ({result['confidence']:.2f}), will use AI fallback")
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better matching."""
        import re
        
        # Convert to lowercase but preserve accents
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Keep accents and special characters for region matching
        # Only remove punctuation that might interfere with matching
        text = re.sub(r'[^\w\s\u00e0-\u00ff]', ' ', text)
        
        return text.strip()
    
    def _extract_grape_variety(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract grape variety from text."""
        # Search for grape varieties in the text
        search_results = self.db_manager.search_grape_variety(text, threshold=0.6)  # Lower threshold
        
        if not search_results:
            return None
        
        # Get the best match
        best_match, score = search_results[0]
        
        # Check if the grape variety appears in the text
        if best_match.lower() in text:
            logger.info(f"🎯 GRAPE VARIETY MATCH: '{best_match}' (score: {score:.2f}) in text: '{text[:100]}...'")
            return {
                'name': best_match,
                'confidence': score / 100.0
            }
        
        return None
    
    def _extract_producer(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract producer from text."""
        # Search for producers in the text
        search_results = self.db_manager.search_producer(text, threshold=0.6)  # Lower threshold
        
        if not search_results:
            return None
        
        # Get the best match
        best_match, score = search_results[0]
        
        # Check if the producer appears in the text
        if best_match.lower() in text:
            logger.info(f"🏭 PRODUCER MATCH: '{best_match}' (score: {score:.2f}) in text: '{text[:100]}...'")
            # Get additional location info for the producer
            producer_info = self._get_producer_info(best_match)
            
            return {
                'name': best_match,
                'confidence': score / 100.0,
                'locations': producer_info.get('locations', [])
            }
        
        return None
    
    def _get_producer_info(self, producer_name: str) -> Dict[str, Any]:
        """Get additional information about a producer."""
        producers_db = self.db_manager._databases.get('producers', {})
        
        if producer_name in producers_db:
            return {
                'name': producer_name,
                'locations': producers_db[producer_name]
            }
        
        return {'name': producer_name, 'locations': []}
    
    def _extract_region(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract region and country from text."""
        # This is a simplified implementation
        # In practice, you might want more sophisticated region matching
        
        regions_db = self.db_manager._databases.get('regions', {})
        
        for country, regions in regions_db.items():
            if isinstance(regions, dict):
                for region in regions.keys():
                    if region.lower() in text:
                        logger.info(f"🗺️  REGION MATCH: '{region}' (country: '{country}') in text: '{text[:100]}...'")
                        return {
                            'region': region,
                            'country': country,
                            'confidence': 0.9
                        }
            elif isinstance(regions, list):
                for region in regions:
                    if region.lower() in text:
                        logger.info(f"🗺️  REGION MATCH: '{region}' (country: '{country}') in text: '{text[:100]}...'")
                        return {
                            'region': region,
                            'country': country,
                            'confidence': 0.9
                        }
        
        return None
    
    def batch_extract(self, wine_texts: List[str]) -> List[Dict[str, Any]]:
        """
        Extract wine information from multiple texts.
        
        Args:
            wine_texts: List of wine texts to extract from
            
        Returns:
            List of extraction results
        """
        results = []
        
        for i, wine_text in enumerate(wine_texts):
            try:
                result = self.extract_wine_info(wine_text)
                results.append(result)
                
                if i % 100 == 0:
                    logger.info(f"Processed {i}/{len(wine_texts)} wine entries")
                    
            except Exception as e:
                logger.error(f"Error extracting from wine text {i}: {e}")
                # Add empty result for failed extraction
                results.append({
                    'grape_variety': None,
                    'producer': None,
                    'region': None,
                    'country': None,
                    'confidence': 0.0,
                    'extraction_method': 'error',
                    'field_confidence': {},
                    'skip_ai': False
                })
        
        return results
    
    def get_extraction_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about extraction results."""
        total = len(results)
        if total == 0:
            return {}
        
        # Count successful extractions
        successful = sum(1 for r in results if r['confidence'] > 0)
        high_confidence = sum(1 for r in results if r['confidence'] >= self.confidence_threshold)
        skipped_ai = sum(1 for r in results if r.get('skip_ai', False))
        
        # Count field extractions
        grape_extracted = sum(1 for r in results if r.get('grape_variety'))
        producer_extracted = sum(1 for r in results if r.get('producer'))
        region_extracted = sum(1 for r in results if r.get('region'))
        
        # Calculate average confidence
        avg_confidence = sum(r['confidence'] for r in results) / total
        
        return {
            'total_entries': total,
            'successful_extractions': successful,
            'high_confidence_extractions': high_confidence,
            'ai_skipped': skipped_ai,
            'ai_fallback_rate': (total - skipped_ai) / total,
            'grape_variety_extracted': grape_extracted,
            'producer_extracted': producer_extracted,
            'region_extracted': region_extracted,
            'average_confidence': avg_confidence
        } 