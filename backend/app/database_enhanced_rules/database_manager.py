"""
Database Manager for Enhanced Rule System

This module manages local wine knowledge databases to reduce AI fallback costs.
It provides fast local lookups for grape varieties, regions, and producers.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages local wine knowledge databases for fast lookups."""
    
    def __init__(self, databases_path: str = None):
        """
        Initialize the database manager.
        
        Args:
            databases_path: Path to the databases directory
        """
        if databases_path is None:
            # Default to the databases directory in this package
            current_dir = Path(__file__).parent
            databases_path = current_dir / "databases"
        
        self.databases_path = Path(databases_path)
        self._databases = {}
        self._loaded = False
        
        logger.info(f"DatabaseManager initialized with path: {self.databases_path}")
    
    def load_databases(self) -> None:
        """Load all available databases."""
        if self._loaded:
            return
        
        try:
            # Load grape varieties database
            grape_file = self.databases_path / "grape_varieties.json"
            if grape_file.exists():
                with open(grape_file, 'r', encoding='utf-8') as f:
                    self._databases['grape_varieties'] = json.load(f)
                logger.info(f"Loaded grape varieties database: {len(self._databases['grape_varieties'])} countries")
            
            # Load producers database (producer_locations.json)
            producers_file = self.databases_path / "producer_locations.json"
            if producers_file.exists():
                with open(producers_file, 'r', encoding='utf-8') as f:
                    self._databases['producers'] = json.load(f)
                logger.info(f"Loaded producers database: {len(self._databases['producers'])} producers")
            
            # Load regions database (geo_hierarchy.json)
            regions_file = self.databases_path / "geo_hierarchy.json"
            if regions_file.exists():
                with open(regions_file, 'r', encoding='utf-8') as f:
                    self._databases['regions'] = json.load(f)
                logger.info(f"Loaded regions database: {len(self._databases['regions'])} countries")
            
            self._loaded = True
            logger.info("All databases loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading databases: {e}")
            raise
    
    def _fuzzy_match(self, text: str, choices: set, cutoff: float = 0.8) -> Tuple[Optional[str], float]:
        """
        Fuzzy match text against a set of choices.
        
        Args:
            text: Text to match
            choices: Set of choices to match against
            cutoff: Minimum similarity threshold
            
        Returns:
            Tuple of (best_match, confidence_score)
        """
        from rapidfuzz import fuzz, process
        
        if not self._loaded:
            self.load_databases()
        
        # Uses token_set_ratio for multi-word, typo-tolerant matching
        result = process.extractOne(
            text, choices, scorer=fuzz.token_set_ratio, score_cutoff=cutoff * 100
        )
        if result:
            match, score, _ = result
            confidence = score / 100.0
            return match, confidence
        return None, 0.0
    
    def _fuzzy_match_in_text(self, text: str, choices: set, cutoff: float = 0.8) -> Tuple[Optional[str], float]:
        """
        Try to find the best fuzzy match in the text.
        
        Args:
            text: Text to search in
            choices: Set of choices to match against
            cutoff: Minimum similarity threshold
            
        Returns:
            Tuple of (best_match, confidence_score)
        """
        return self._fuzzy_match(text, choices, cutoff)
    
    def extract_fields(self, block: Dict[str, Any], cutoff: float = 0.8) -> Tuple[Dict[str, Any], float]:
        """
        Extract fields from a wine block using database lookups.
        This method provides the same interface as DatabaseStrategy.extract()
        
        Args:
            block: Wine block containing text
            cutoff: Minimum confidence threshold
            
        Returns:
            Tuple of (extracted_fields, overall_confidence)
        """
        if not self._loaded:
            self.load_databases()
        
        text = block.get('text', '')
        extracted = {}
        confidence = 0.0
        
        # Get all available choices
        producer_names = set(self._databases.get('producers', {}).keys())
        country_names = set(self._databases.get('regions', {}).keys())
        
        # Get grape variety names
        grape_names = set()
        grape_db = self._databases.get('grape_varieties', {})
        for country_data in grape_db.values():
            if isinstance(country_data, list):
                grape_names.update(country_data)
            elif isinstance(country_data, dict):
                for region_data in country_data.values():
                    if isinstance(region_data, list):
                        grape_names.update(region_data)
        
        # Producer extraction
        producer, prod_conf = self._fuzzy_match_in_text(text, producer_names, cutoff)
        if producer:
            extracted['producer_name'] = {'value': producer, 'confidence': prod_conf, 'provenance': 'database'}
            confidence += prod_conf * 0.25
            
            # Try to get country/region/subregion from producer db
            locations = self._databases.get('producers', {}).get(producer, [])
            if locations:
                loc = locations[0]  # Use the first location for now
                if loc.get('country'):
                    extracted['country'] = {'value': loc['country'], 'confidence': prod_conf, 'provenance': 'database'}
                    confidence += prod_conf * 0.15
                if loc.get('region'):
                    extracted['region'] = {'value': loc['region'], 'confidence': prod_conf, 'provenance': 'database'}
                    confidence += prod_conf * 0.1
                if loc.get('subregion'):
                    extracted['sub_region'] = {'value': loc['subregion'], 'confidence': prod_conf, 'provenance': 'database'}
                    confidence += prod_conf * 0.05
        
        # Grape variety extraction
        grape, grape_conf = self._fuzzy_match_in_text(text, grape_names, cutoff)
        if grape:
            extracted['grape_variety'] = {'value': grape, 'confidence': grape_conf, 'provenance': 'database'}
            confidence += grape_conf * 0.2
        
        # Country extraction
        country, country_conf = self._fuzzy_match_in_text(text, country_names, cutoff)
        if country:
            extracted['country'] = {'value': country, 'confidence': country_conf, 'provenance': 'database'}
            confidence += country_conf * 0.1
        
        # Region/Subregion extraction
        regions_db = self._databases.get('regions', {})
        for country_name, regions in regions_db.items():
            if isinstance(regions, dict):
                region_names = set(regions.keys())
                region, region_conf = self._fuzzy_match_in_text(text, region_names, cutoff)
                if region:
                    extracted['region'] = {'value': region, 'confidence': region_conf, 'provenance': 'database'}
                    confidence += region_conf * 0.05
                    
                    # Check for subregions
                    subregions = set(regions[region]) if isinstance(regions[region], list) else set()
                    subregion, subregion_conf = self._fuzzy_match_in_text(text, subregions, cutoff)
                    if subregion:
                        extracted['sub_region'] = {'value': subregion, 'confidence': subregion_conf, 'provenance': 'database'}
                        confidence += subregion_conf * 0.05
        
        # Normalize confidence
        confidence = min(confidence, 1.0)
        return extracted, confidence

    def get_grape_varieties(self, country: str = None, region: str = None) -> List[str]:
        """
        Get grape varieties for a specific country/region.
        
        Args:
            country: Country name (optional)
            region: Region name (optional)
            
        Returns:
            List of grape variety names
        """
        if not self._loaded:
            self.load_databases()
        
        grape_db = self._databases.get('grape_varieties', {})
        
        if not country:
            # Return all international varieties
            return grape_db.get('International', [])
        
        if country not in grape_db:
            return []
        
        country_data = grape_db[country]
        
        if not region:
            # Return all varieties for the country
            varieties = []
            if isinstance(country_data, list):
                varieties.extend(country_data)
            elif isinstance(country_data, dict):
                for region_name, region_varieties in country_data.items():
                    if isinstance(region_varieties, list):
                        varieties.extend(region_varieties)
            return list(set(varieties))  # Remove duplicates
        
        # Return varieties for specific region
        if isinstance(country_data, dict) and region in country_data:
            region_data = country_data[region]
            if isinstance(region_data, list):
                return region_data
        
        return []
    
    def get_producers(self, country: str = None, region: str = None, sub_region: str = None) -> List[str]:
        """
        Get producers for a specific location.
        
        Args:
            country: Country name (optional)
            region: Region name (optional)
            sub_region: Sub-region name (optional)
            
        Returns:
            List of producer names
        """
        if not self._loaded:
            self.load_databases()
        
        producers_db = self._databases.get('producers', {})
        
        if not country:
            # Return all producer names (keys of the dictionary)
            return list(producers_db.keys())
        
        # For the producer_locations.json structure, we need to filter by country
        matching_producers = []
        for producer_name, locations in producers_db.items():
            for location in locations:
                if location.get('country') == country:
                    if not region or location.get('region') == region:
                        if not sub_region or location.get('subregion') == sub_region:
                            matching_producers.append(producer_name)
                            break  # Found a match for this producer
        
        return list(set(matching_producers))
    
    def get_regions(self, country: str = None) -> List[str]:
        """
        Get regions for a specific country.
        
        Args:
            country: Country name (optional)
            
        Returns:
            List of region names
        """
        if not self._loaded:
            self.load_databases()
        
        regions_db = self._databases.get('regions', {})
        
        if not country:
            # Return all regions (flattened)
            all_regions = []
            for country_data in regions_db.values():
                if isinstance(country_data, dict):
                    all_regions.extend(country_data.keys())
                elif isinstance(country_data, list):
                    all_regions.extend(country_data)
            return list(set(all_regions))
        
        if country not in regions_db:
            return []
        
        country_data = regions_db[country]
        
        if isinstance(country_data, dict):
            return list(country_data.keys())
        elif isinstance(country_data, list):
            return country_data
        
        return []
    
    def search_grape_variety(self, query: str, threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Search for grape varieties using fuzzy matching.
        
        Args:
            query: Search query
            threshold: Minimum similarity threshold
            
        Returns:
            List of (variety_name, similarity_score) tuples
        """
        from rapidfuzz import fuzz, process
        
        if not self._loaded:
            self.load_databases()
        
        # Get all grape varieties
        all_varieties = []
        grape_db = self._databases.get('grape_varieties', {})
        
        for country_data in grape_db.values():
            if isinstance(country_data, list):
                all_varieties.extend(country_data)
            elif isinstance(country_data, dict):
                for region_data in country_data.values():
                    if isinstance(region_data, list):
                        all_varieties.extend(region_data)
        
        # Remove duplicates
        all_varieties = list(set(all_varieties))
        
        # Perform fuzzy search
        results = process.extract(
            query, 
            all_varieties, 
            scorer=fuzz.token_sort_ratio,
            limit=10
        )
        
        # Filter by threshold - rapidfuzz returns (name, score, index)
        return [(name, score) for name, score, _ in results if score >= threshold * 100]
    
    def search_producer(self, query: str, threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Search for producers using fuzzy matching.
        
        Args:
            query: Search query
            threshold: Minimum similarity threshold
            
        Returns:
            List of (producer_name, similarity_score) tuples
        """
        from rapidfuzz import fuzz, process
        
        if not self._loaded:
            self.load_databases()
        
        # Get all producer names (keys of the dictionary)
        producers_db = self._databases.get('producers', {})
        all_producers = list(producers_db.keys())
        
        # Perform fuzzy search
        results = process.extract(
            query, 
            all_producers, 
            scorer=fuzz.token_sort_ratio,
            limit=10
        )
        
        # Filter by threshold - rapidfuzz returns (name, score, index)
        return [(name, score) for name, score, _ in results if score >= threshold * 100]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded databases."""
        if not self._loaded:
            self.load_databases()
        
        stats = {}
        
        # Grape varieties stats
        grape_db = self._databases.get('grape_varieties', {})
        grape_count = 0
        for country_data in grape_db.values():
            if isinstance(country_data, list):
                grape_count += len(country_data)
            elif isinstance(country_data, dict):
                for region_data in country_data.values():
                    if isinstance(region_data, list):
                        grape_count += len(region_data)
        
        stats['grape_varieties'] = {
            'countries': len(grape_db),
            'total_varieties': grape_count
        }
        
        # Producers stats
        producers_db = self._databases.get('producers', {})
        producer_count = len(producers_db)
        
        # Count unique countries in producer locations
        unique_countries = set()
        for locations in producers_db.values():
            for location in locations:
                if location.get('country'):
                    unique_countries.add(location['country'])
        
        stats['producers'] = {
            'countries': len(unique_countries),
            'total_producers': producer_count
        }
        
        # Regions stats
        regions_db = self._databases.get('regions', {})
        region_count = 0
        for country_data in regions_db.values():
            if isinstance(country_data, dict):
                region_count += len(country_data)
            elif isinstance(country_data, list):
                region_count += len(country_data)
        
        stats['regions'] = {
            'countries': len(regions_db),
            'total_regions': region_count
        }
        
        return stats

# Global instance for easy access
@lru_cache(maxsize=1)
def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return DatabaseManager() 