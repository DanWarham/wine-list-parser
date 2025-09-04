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
        Extract wine information from text using DatabaseManager's unified matching system.
        
        Args:
            wine_text: Raw wine text to extract from
            
        Returns:
            Dictionary with extracted fields and confidence scores
        """
        # Use DatabaseManager's working extract_fields method
        extracted_fields, confidence = self.db_manager.extract_fields(
            {'text': wine_text}, 
            cutoff=self.confidence_threshold
        )
        
        # Map to EarlyExtractor's expected format
        result = self._map_extracted_fields(extracted_fields, confidence)
        
        # Determine if we should skip AI processing
        if result['confidence'] >= self.confidence_threshold:
            result['skip_ai'] = True
            logger.info(f"High confidence database extraction ({result['confidence']:.2f}), skipping AI")
        else:
            result['skip_ai'] = False
            logger.info(f"Low confidence database extraction ({result['confidence']:.2f}), will use AI fallback")
        
        return result
    
    def _map_extracted_fields(self, extracted_fields: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """
        Map DatabaseManager's extracted fields to EarlyExtractor's expected format.
        
        Args:
            extracted_fields: Fields extracted by DatabaseManager
            confidence: Overall confidence score
            
        Returns:
            Mapped result in EarlyExtractor format
        """
        result = {
            'grape_variety': None,
            'producer': None,
            'region': None,
            'country': None,
            'confidence': confidence,
            'extraction_method': 'database',
            'field_confidence': {}
        }
        
        # Map grape variety
        if 'grape_variety' in extracted_fields:
            grape_data = extracted_fields['grape_variety']
            if isinstance(grape_data, dict) and grape_data.get('value'):
                result['grape_variety'] = grape_data['value']
                result['field_confidence']['grape_variety'] = grape_data.get('confidence', 0.9)
        
        # Map producer (check both producer and producer_name fields)
        producer_value = None
        producer_confidence = 0.0
        
        if 'producer' in extracted_fields:
            producer_data = extracted_fields['producer']
            if isinstance(producer_data, dict) and producer_data.get('value'):
                producer_value = producer_data['value']
                producer_confidence = producer_data.get('confidence', 0.9)
        elif 'producer_name' in extracted_fields:
            producer_data = extracted_fields['producer_name']
            if isinstance(producer_data, dict) and producer_data.get('value'):
                producer_value = producer_data['value']
                producer_confidence = producer_data.get('confidence', 0.9)
        
        if producer_value:
            result['producer'] = producer_value
            result['field_confidence']['producer'] = producer_confidence
        
        # Map region
        if 'region' in extracted_fields:
            region_data = extracted_fields['region']
            if isinstance(region_data, dict) and region_data.get('value'):
                result['region'] = region_data['value']
                result['field_confidence']['region'] = region_data.get('confidence', 0.9)
        
        # Map country
        if 'country' in extracted_fields:
            country_data = extracted_fields['country']
            if isinstance(country_data, dict) and country_data.get('value'):
                result['country'] = country_data['value']
                result['field_confidence']['country'] = country_data.get('confidence', 0.9)
        
        # Log successful matches
        if result['grape_variety']:
            logger.info(f"🎯 GRAPE VARIETY MATCH: '{result['grape_variety']}' (conf: {result['field_confidence'].get('grape_variety', 0):.2f})")
        
        if result['producer']:
            logger.info(f"🏭 PRODUCER MATCH: '{result['producer']}' (conf: {result['field_confidence'].get('producer', 0):.2f})")
        
        if result['region']:
            logger.info(f"🗺️  REGION MATCH: '{result['region']}' (conf: {result['field_confidence'].get('region', 0):.2f})")
        
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