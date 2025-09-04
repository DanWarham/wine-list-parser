"""
Database Manager for Enhanced Rule System

This module manages local wine knowledge databases to reduce AI fallback costs.
It provides fast local lookups for grape varieties, regions, and producers.
"""

import json
import os
import logging
import re
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
            # Load grape varieties database (enhanced_grape_varieties.json)
            grape_file = self.databases_path / "enhanced_grape_varieties.json"
            if grape_file.exists():
                with open(grape_file, 'r', encoding='utf-8') as f:
                    self._databases['grape_varieties'] = json.load(f)
                logger.info(f"Loaded enhanced grape varieties database: {len(self._databases['grape_varieties'])} countries")
            else:
                raise FileNotFoundError(f"Enhanced grape varieties database not found at {grape_file}")
            
            # Load producers database (enhanced_producer_locations.json)
            producers_file = self.databases_path / "enhanced_producer_locations.json"
            if producers_file.exists():
                with open(producers_file, 'r', encoding='utf-8') as f:
                    self._databases['producers'] = json.load(f)
                logger.info(f"Loaded enhanced producers database: {len(self._databases['producers'])} producers")
            else:
                raise FileNotFoundError(f"Enhanced producers database not found at {producers_file}")
            
            # Load regions database (enhanced_geo_hierarchy.json)
            regions_file = self.databases_path / "enhanced_geo_hierarchy.json"
            if regions_file.exists():
                with open(regions_file, 'r', encoding='utf-8') as f:
                    self._databases['regions'] = json.load(f)
                logger.info(f"Loaded enhanced regions database: {len(self._databases['regions'])} countries")
            else:
                raise FileNotFoundError(f"Enhanced regions database not found at {regions_file}")
            
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
        # First try exact word boundary matches
        words = text.split()
        for word in words:
            # Clean the word
            clean_word = re.sub(r'[^\w\s]', '', word).strip()
            if clean_word in choices:
                return clean_word, 1.0
        
        # Then try fuzzy matching with word boundaries
        for choice in choices:
            # Look for the choice as a whole word in the text
            pattern = r'\b' + re.escape(choice) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                return choice, 0.95
        
        # Finally try fuzzy matching
        return self._fuzzy_match(text, choices, cutoff)
    
    def extract_fields(self, block: Dict[str, Any], cutoff: float = 0.6) -> Tuple[Dict[str, Any], float]:
        """
        Extract wine fields from text block using enhanced databases and improved patterns.
        """
        text = block.get('text', '').strip()
        if not text:
            return {}, 0.0

        extracted_fields = {}
        total_confidence = 0.0
        field_count = 0

        # Enhanced regex patterns for specific wine list formats
        wine_list_patterns = {
            'vintage': [
                r'^(\d{4})\s+',  # VINTAGE at start
                r'\b(19|20)\d{2}\b',  # Any 4-digit year
                r'NV\b',  # Non-vintage
                r'(\d{4})\s*[-\u2013]',  # Year followed by dash
                r'(\d{4})\s*[|]',  # Year followed by pipe
                r'(\d{4})\s*[A-Z]',  # Year followed by capital letter
                r'Vintage:\s*(\d{4}|NV)',  # With label
                r'Year:\s*(\d{4}|NV)',  # With label
                r'(\d{4})\s*[£€$¥]',  # Year before currency
                r'(\d{4})\s*ml',  # Year before ml
                r'(\d{4})\s*[A-Z][a-z]+',  # Year before grape variety
            ],
            'price': [
                # More specific price patterns to avoid vintage confusion
                r'(\d{2,3})\s*$',  # 2-3 digit number at end (likely price)
                r'[£€$¥]\s*(\d+(?:\.\d{2})?)',  # Currency symbols
                r'(\d+)\s*[A-Z][a-z]+\s*$',  # Number before grape variety at end
                r'(\d+)\s*[|]\s*[A-Z]',  # Number before pipe followed by capital
                r'(\d+)\s*[-–]\s*[A-Z]',  # Number before dash followed by capital
                r'Price:\s*(\d+)',  # With label
                r'(\d{2,3})\s*[A-Z][A-Za-z\s&-]+\s*$',  # Number before producer at end
                # Avoid 4-digit numbers that are likely vintages
                r'(?<!19|20)(\d{2,3})\b(?!\d)',  # 2-3 digits not preceded by 19/20
            ],
            'producer_name': [
                # Pattern 1: Producer after region separator (most common) - FIXED
                r'\|\s*([A-Z][A-Za-z\s&-]+?)(?:\s+\d{2,3})?\s*$',
                # Pattern 2: Producer before price at end - FIXED
                r'([A-Z][A-Za-z\s&-]+?)\s+(\d{2,3})\s*$',
                # Pattern 3: Producer with common prefixes - FIXED
                r'(Domaine|Château|Maison|Cave|Cantina|Bodega|Weingut|Tenuta)\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d{2,3})?\s*$',
                # Pattern 4: Producer with quotes - FIXED
                r'([A-Z][A-Za-z\s&-]+?)\s*[\'"]',
                # Pattern 5: Producer before vintage - FIXED
                r'([A-Z][A-Za-z\s&-]+?)\s+(19|20)\d{2}',
                # Pattern 6: Producer at start of line - FIXED
                r'^([A-Z][A-Za-z\s&-]+?)(?=\s+\d{4}|\s+NV|\s+"|\s+[A-Z]|$)',
                # Pattern 7: Producer with common suffixes - FIXED
                r'([A-Z][A-Za-z\s&-]+?)\s+(Reserve|Grand|Premier|Vieilles|Vignes|Brut|Sec|Demi-Sec)',
                # Pattern 8: Producer after grape variety - FIXED
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\|\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d{2,3})?\s*$',
                # Pattern 9: Producer with multiple words - IMPROVED
                r'([A-Z][A-Za-z\s&-]{3,}?)(?=\s+\d{2,3}\s*$|\s+\d{4}|\s+NV)',
                # Pattern 10: Producer with ampersand - IMPROVED
                r'([A-Z][A-Za-z\s&]+?)\s+(?=\d{2,3}\s*$|\d{4})',
                # Pattern 11: Producer with "de" or "du" - IMPROVED
                r'([A-Z][A-Za-z\s]+(?:de|du)\s+[A-Z][A-Za-z\s]+?)(?=\s+\d{2,3}\s*$|\s+\d{4})',
                # Pattern 12: Producer with "Dr." prefix - NEW
                r'(Dr\.\s+[A-Z][A-Za-z\s]+?)(?=\s+\d{2,3}\s*$|\s+\d{4})',
                # Pattern 13: Producer with "&" in name - NEW
                r'([A-Z][A-Za-z\s]+&[A-Za-z\s]+?)(?=\s+\d{2,3}\s*$|\s+\d{4})',
            ],
            'wine_name': [
                # Pattern 1: Quoted wine names
                r'[\'"]([^\'"]+)[\'"]',
                # Pattern 2: Wine name after vintage
                r'(19|20)\d{2}\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\|)',
                # Pattern 3: Wine name with common suffixes - IMPROVED
                r'([A-Z][A-Za-z\s&-]+?)\s+(Reserve|Grand|Premier|Vieilles|Vignes|Brut|Sec|Demi-Sec|Grand Cru|Premier Cru)',
                # Pattern 4: Wine name between grape and region
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z][A-Za-z\s&-]+?)\s+\|\s+[A-Z]',
                # Pattern 5: Wine name with designation - IMPROVED
                r'([A-Z][A-Za-z\s&-]+?)\s+(Grand Cru|Premier Cru|Village|Regional|Reserve)',
                # Pattern 6: Wine name in parentheses
                r'\(([A-Za-z\s&-]+?)\)',
                # Pattern 7: Wine name after grape variety - NEW
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z][A-Za-z\s&-]+?)(?=\s+\|)',
            ],
            'grape_variety': [
                r'\b(Chardonnay|Pinot Noir|Cabernet Sauvignon|Merlot|Syrah|Riesling|Sauvignon Blanc)\b',
                r'\b(Meunier|Nebbiolo|Sangiovese|Verdejo|Albarino|Tempranillo|Grenache)\b',
                r'\b(Pinot Grigio|Pinot Gris|Chenin Blanc|Viognier|Marsanne|Roussanne)\b',
                r'\b(Malbec|Carmenère|Petit Verdot|Cabernet Franc|Barbera|Dolcetto)\b',
                r'\b(Mourvèdre|Cinsault|Carignan|Grenache Blanc|Rolle|Vermentino)\b',
                r'\b(Aligoté|Gamay|Pinot Blanc|Auxerrois|Muscat|Gewürztraminer)\b',
            ]
        }

        # Apply wine list format patterns first with priority handling
        # Handle vintage and price patterns with disambiguation
        vintage_matches = []
        price_matches = []
        
        # Collect all vintage matches
        for pattern in wine_list_patterns['vintage']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                vintage_matches.append({
                    'value': value,
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': pattern
                })
        
        # Collect all price matches
        for pattern in wine_list_patterns['price']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                price_matches.append({
                    'value': value,
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': pattern
                })
        
        # Enhanced disambiguation: vintage vs price
        for vintage_match in vintage_matches:
            value = vintage_match['value']
            # Skip if this looks like a price (2-3 digits, likely price)
            if value.isdigit() and len(value) <= 3 and int(value) < 1000:
                continue
            # Skip if it's a 4-digit year that's too recent (likely not a vintage)
            if value.isdigit() and len(value) == 4 and int(value) > 2024:
                continue
            # This is likely a vintage
            if value == 'NV':
                extracted_fields['vintage'] = {'value': 'NV', 'confidence': 0.9, 'provenance': 'regex'}
            else:
                extracted_fields['vintage'] = {'value': value, 'confidence': 0.9, 'provenance': 'regex'}
            total_confidence += 0.9
            field_count += 1
            break
        
        # Enhanced price handling (avoid conflicts with vintage)
        for price_match in price_matches:
            value = price_match['value']
            # Skip if this conflicts with an already extracted vintage
            if 'vintage' in extracted_fields:
                vintage_value = extracted_fields['vintage']['value']
                if value == vintage_value:
                    continue
            
            # Enhanced price validation
            if value.isdigit():
                price_int = int(value)
                # Skip if it's likely a vintage (4 digits, reasonable year range)
                if len(value) == 4 and 1900 <= price_int <= 2024:
                    continue
                # Skip if it's too small to be a realistic price
                if price_int < 10:
                    continue
                # Skip if it's too large to be a realistic price (over 1000)
                if price_int > 1000:
                    continue
            
            # This is likely a price
            extracted_fields['price'] = {'value': value, 'confidence': 0.9, 'provenance': 'regex'}
            total_confidence += 0.9
            field_count += 1
            break
        
        # Apply other patterns
        for field, patterns in wine_list_patterns.items():
            if field in ['vintage', 'price']:  # Already handled above
                continue
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    if field == 'grape_variety':
                        # Clean up grape variety
                        clean_value = value.strip().replace('  ', ' ')
                        extracted_fields[field] = {'value': clean_value, 'confidence': 0.9, 'provenance': 'regex'}
                    elif field == 'wine_name':
                        # Map wine_name to cuvee field for database compatibility
                        extracted_fields['cuvee'] = {'value': value.strip(), 'confidence': 0.9, 'provenance': 'regex'}
                        # Also keep wine_name for compatibility
                        extracted_fields[field] = {'value': value.strip(), 'confidence': 0.9, 'provenance': 'regex'}
                    elif field == 'producer_name':
                        # Map producer_name to producer field for database compatibility
                        extracted_fields['producer'] = {'value': value.strip(), 'confidence': 0.9, 'provenance': 'regex'}
                        # Also keep producer_name for compatibility
                        extracted_fields[field] = {'value': value.strip(), 'confidence': 0.9, 'provenance': 'regex'}
                    else:
                        extracted_fields[field] = {'value': value.strip(), 'confidence': 0.9, 'provenance': 'regex'}
                    total_confidence += 0.9
                    field_count += 1
                    break

        # Continue with existing database matching for fields not found by regex
        if not self._loaded:
            self.load_databases()
        
        # Get all available choices
        producer_names = set(self._databases.get('producers', {}).keys())
        country_names = set(self._databases.get('regions', {}).keys())
        
        # Get grape variety names (including individual varieties for blends)
        grape_names = set()
        grape_db = self._databases.get('grape_varieties', {})
        for country_data in grape_db.values():
            if isinstance(country_data, list):
                grape_names.update(country_data)
            elif isinstance(country_data, dict):
                for region_data in country_data.values():
                    if isinstance(region_data, list):
                        grape_names.update(region_data)
        
        # Enhanced producer extraction with multiple strategies
        if 'producer_name' not in extracted_fields and 'producer' not in extracted_fields:
            producer = None
            prod_conf = 0.0
            
            # Strategy 1: Try enhanced regex patterns first
            producer_patterns = [
                r'\|\s*([A-Z][A-Za-z\s&-]+?)(?:\s+\d{2,3})?\s*$',  # After region separator
                r'([A-Z][A-Za-z\s&-]+?)\s+(\d{2,3})\s*$',  # Before price
                r'(Domaine|Château|Maison|Cave|Cantina|Bodega|Weingut|Tenuta)\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d{2,3})?\s*$',  # With prefix
                r'(Dr\.\s+[A-Z][A-Za-z\s]+?)(?=\s+\d{2,3}\s*$|\s+\d{4})',  # Dr. prefix
                r'([A-Z][A-Za-z\s]+&[A-Za-z\s]+?)(?=\s+\d{2,3}\s*$|\s+\d{4})',  # & in name
            ]
            
            for pattern in producer_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) > 1:
                        producer = ' '.join([g for g in match.groups() if g])
                    else:
                        producer = match.group(1)
                    prod_conf = 0.9
                    break
            
            # Strategy 2: Try database matching if regex failed
            if not producer:
                producer, prod_conf = self._fuzzy_match_in_text(text, producer_names, cutoff)
            
            if producer:
                # Map producer_name to producer field for database compatibility
                extracted_fields['producer'] = {'value': producer, 'confidence': prod_conf, 'provenance': 'enhanced_regex' if prod_conf == 0.9 else 'database'}
                # Also keep producer_name for compatibility with other systems
                extracted_fields['producer_name'] = {'value': producer, 'confidence': prod_conf, 'provenance': 'enhanced_regex' if prod_conf == 0.9 else 'database'}
                total_confidence += prod_conf
                field_count += 1
                
                # Try to get country/region/subregion from producer db
                locations = self._databases.get('producers', {}).get(producer, [])
                if locations:
                    loc = locations[0]  # Use the first location for now
                    if loc.get('country') and 'country' not in extracted_fields:
                        extracted_fields['country'] = {'value': loc['country'], 'confidence': prod_conf, 'provenance': 'database'}
                        total_confidence += prod_conf
                        field_count += 1
                    if loc.get('region') and 'region' not in extracted_fields:
                        extracted_fields['region'] = {'value': loc['region'], 'confidence': prod_conf, 'provenance': 'database'}
                        total_confidence += prod_conf
                        field_count += 1
                    if loc.get('subregion') and 'subregion' not in extracted_fields:
                        extracted_fields['subregion'] = {'value': loc['subregion'], 'confidence': prod_conf, 'provenance': 'database'}
                        total_confidence += prod_conf
                        field_count += 1
        
        # Grape variety extraction - try blends first, then individual varieties
        if 'grape_variety' not in extracted_fields:
            grape = None
            grape_conf = 0.0
            
            # Try to extract grape blends by looking for multiple varieties first
            blend_patterns = [
                r'\b(Pinot\s+Noir\s*/\s*Pinot\s+Blanc)\b',
                r'\b(Chardonnay\s*/\s*Meunier\s*/\s*Pinot\s+Noir)\b',
                r'\b(Pinot\s+Noir\s*/\s*Chardonnay)\b',
                r'\b(Chardonnay\s*/\s*Meunier)\b',
                r'\b(Pinot\s+Noir\s*/\s*Chardonnay\s*/\s*Meunier)\b'
            ]
            
            for pattern in blend_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    blend = match.group(1)
                    grape = blend
                    grape_conf = 0.8
                    break
            
            # If no blend found, try individual varieties
            if not grape:
                grape, grape_conf = self._fuzzy_match_in_text(text, grape_names, cutoff)
            
            if grape:
                extracted_fields['grape_variety'] = {'value': grape, 'confidence': grape_conf, 'provenance': 'database_blend' if '/' in grape else 'database'}
                total_confidence += grape_conf
                field_count += 1
        
        # Country extraction
        if 'country' not in extracted_fields:
            country, country_conf = self._fuzzy_match_in_text(text, country_names, cutoff)
            if country:
                extracted_fields['country'] = {'value': country, 'confidence': country_conf, 'provenance': 'database'}
                total_confidence += country_conf
                field_count += 1
        
        # Region/Subregion extraction with enhanced matching
        if 'region' not in extracted_fields:
            regions_db = self._databases.get('regions', {})
            
            # Try to extract specific French regions that might not be in the database
            french_region_patterns = [
                r'\b(Riceys\s+sur\s+Marnes)\b',
                r'\b(Mareuil-sur-Aÿ)\b',
                r'\b(Mareuil-Sur-Aÿ)\b',
                r'\b(Côte\s+des\s+Blancs)\b',
                r'\b(Côtes\s+des\s+Blancs)\b',
                r'\b(Montagne\s+de\s+Reims)\b',
                r'\b(Marne\s+Valley)\b',
                r'\b(Grand\s+Cru\s+\w+)\b',
                r'\b(1er\s+Cru\s+\w+)\b'
            ]
            
            for pattern in french_region_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    region = match.group(1)
                    extracted_fields['region'] = {'value': region, 'confidence': 0.8, 'provenance': 'database_pattern'}
                    total_confidence += 0.8
                    field_count += 1
                    break
            
            # Try database matching for regions
            for country_name, regions in regions_db.items():
                if isinstance(regions, dict):
                    region_names = set(regions.keys())
                    region, region_conf = self._fuzzy_match_in_text(text, region_names, cutoff)
                    if region:
                        extracted_fields['region'] = {'value': region, 'confidence': region_conf, 'provenance': 'database'}
                        total_confidence += region_conf
                        field_count += 1
                        
                        # Check for subregions
                        if 'subregion' not in extracted_fields:
                            subregions = set(regions[region]) if isinstance(regions[region], list) else set()
                            subregion, subregion_conf = self._fuzzy_match_in_text(text, subregions, cutoff)
                            if subregion:
                                extracted_fields['subregion'] = {'value': subregion, 'confidence': subregion_conf, 'provenance': 'database'}
                                total_confidence += subregion_conf
                                field_count += 1
                        break
        
        # Calculate average confidence
        avg_confidence = total_confidence / field_count if field_count > 0 else 0.0
        return extracted_fields, avg_confidence

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