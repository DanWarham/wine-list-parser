from typing import List, Dict, Any, Optional, Tuple
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class IntelligentSampler:
    """
    Intelligent sampling system for wine list entries.
    
    Selects diverse samples based on:
    - Regex failures (40% priority)
    - Wine type diversity (30% priority) 
    - Price range diversity (20% priority)
    - Regional diversity (10% priority)
    """
    
    def __init__(self):
        # Wine type categories
        self.wine_types = {
            'red': ['red', 'rouge', 'tinto', 'rosso', 'rotwein'],
            'white': ['white', 'blanc', 'blanco', 'bianco', 'weisswein'],
            'sparkling': ['sparkling', 'champagne', 'cremant', 'prosecco', 'cava'],
            'dessert': ['dessert', 'sauternes', 'port', 'sherry', 'madeira'],
            'rose': ['rose', 'rosado', 'rosato', 'rosé']
        }
        
        # Price ranges (in GBP)
        self.price_ranges = {
            'low': (0, 30),
            'medium': (30, 80),
            'high': (80, 200),
            'premium': (200, float('inf'))
        }
        
        # Common wine regions for diversity
        self.wine_regions = [
            'bordeaux', 'burgundy', 'champagne', 'rhone', 'loire',
            'tuscany', 'piedmont', 'veneto', 'rioja', 'ribera',
            'napa', 'sonoma', 'barossa', 'marlborough', 'mosel'
        ]

    def select_sample(self, entries: List[Dict[str, Any]], sample_size: int = 15) -> List[Dict[str, Any]]:
        """
        Select intelligent sample from wine list entries.
        
        Args:
            entries: List of wine entry dictionaries
            sample_size: Target sample size (default 15)
            
        Returns:
            List of selected entries with diversity metadata
        """
        # Filter out None entries
        valid_entries = [entry for entry in entries if entry is not None]
        
        if len(valid_entries) == 0:
            logger.warning("No valid entries provided to select_sample")
            return []
        
        if len(valid_entries) <= sample_size:
            logger.info(f"Total entries ({len(valid_entries)}) <= sample size ({sample_size}), returning all entries")
            return valid_entries
        
        logger.info(f"Selecting {sample_size} entries from {len(valid_entries)} total entries")
        
        # Step 1: Identify regex failures (40% priority)
        regex_failures = self._identify_regex_failures(valid_entries)
        regex_sample_size = int(sample_size * 0.4)
        selected_regex = self._select_regex_failures(regex_failures, regex_sample_size)
        
        # Step 2: Select diverse wine types (30% priority)
        remaining_entries = [e for e in valid_entries if e not in selected_regex]
        wine_type_sample_size = int(sample_size * 0.3)
        selected_wine_types = self._select_wine_type_diversity(remaining_entries, wine_type_sample_size)
        
        # Step 3: Select price range diversity (20% priority)
        remaining_entries = [e for e in remaining_entries if e not in selected_wine_types]
        price_sample_size = int(sample_size * 0.2)
        selected_price = self._select_price_diversity(remaining_entries, price_sample_size)
        
        # Step 4: Select regional diversity (10% priority)
        remaining_entries = [e for e in remaining_entries if e not in selected_price]
        region_sample_size = sample_size - len(selected_regex) - len(selected_wine_types) - len(selected_price)
        selected_regions = self._select_regional_diversity(remaining_entries, region_sample_size)
        
        # Combine all selections
        selected_sample = selected_regex + selected_wine_types + selected_price + selected_regions
        
        # Add diversity metadata
        for entry in selected_sample:
            if entry is not None:  # Double-check for None values
                entry['_sampling_metadata'] = {
                    'diversity_score': self._calculate_diversity_score(entry),
                    'selection_reason': self._get_selection_reason(entry, selected_regex, selected_wine_types, selected_price, selected_regions)
                }
        
        logger.info(f"Selected {len(selected_sample)} entries with diversity breakdown: "
                   f"regex_failures={len(selected_regex)}, wine_types={len(selected_wine_types)}, "
                   f"price_ranges={len(selected_price)}, regions={len(selected_regions)}")
        
        return selected_sample

    def _identify_regex_failures(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify entries that failed regex extraction."""
        failures = []
        
        for entry in entries:
            if entry is None:
                logger.warning("Found None entry in _identify_regex_failures, skipping")
                continue
                
            text = entry.get('text', '')
            if not text:
                continue
                
            # Check if key fields are missing or have low confidence
            missing_fields = []
            low_confidence_fields = []
            
            for field in ['producer_name', 'wine_name', 'vintage', 'price']:
                field_data = entry.get(field, {})
                if isinstance(field_data, dict):
                    value = field_data.get('value')
                    confidence = field_data.get('confidence', 0)
                else:
                    value = field_data
                    confidence = 0.8  # Assume default confidence for direct values
                
                if not value:
                    missing_fields.append(field)
                elif confidence < 0.6:
                    low_confidence_fields.append(field)
            
            # Consider it a failure if missing key fields or low confidence
            if len(missing_fields) >= 2 or len(low_confidence_fields) >= 2:
                entry['_regex_failure_reason'] = {
                    'missing_fields': missing_fields,
                    'low_confidence_fields': low_confidence_fields
                }
                failures.append(entry)
        
        return failures

    def _select_regex_failures(self, failures: List[Dict[str, Any]], target_size: int) -> List[Dict[str, Any]]:
        """Select diverse regex failures."""
        if len(failures) <= target_size:
            return failures
        
        # Sort by failure severity (more missing fields = higher priority)
        failures.sort(key=lambda x: len(x.get('_regex_failure_reason', {}).get('missing_fields', [])), reverse=True)
        
        return failures[:target_size]

    def _select_wine_type_diversity(self, entries: List[Dict[str, Any]], target_size: int) -> List[Dict[str, Any]]:
        """Select entries with diverse wine types."""
        # Filter out None entries
        valid_entries = [entry for entry in entries if entry is not None]
        
        if len(valid_entries) <= target_size:
            return valid_entries
        
        # Categorize entries by wine type
        categorized = defaultdict(list)
        uncategorized = []
        
        for entry in valid_entries:
            text = entry.get('text', '').lower()
            wine_type = self._classify_wine_type(text)
            
            if wine_type:
                categorized[wine_type].append(entry)
            else:
                uncategorized.append(entry)
        
        # Select balanced sample across wine types
        selected = []
        wine_types = list(categorized.keys())
        
        if wine_types:
            # Distribute target size across wine types
            per_type = max(1, target_size // len(wine_types))
            
            for wine_type in wine_types:
                type_entries = categorized[wine_type][:per_type]
                selected.extend(type_entries)
                
                if len(selected) >= target_size:
                    break
            
            # Fill remaining slots with uncategorized entries
            remaining_slots = target_size - len(selected)
            if remaining_slots > 0 and uncategorized:
                selected.extend(uncategorized[:remaining_slots])
        
        return selected[:target_size]

    def _select_price_diversity(self, entries: List[Dict[str, Any]], target_size: int) -> List[Dict[str, Any]]:
        """Select entries with diverse price ranges."""
        # Filter out None entries
        valid_entries = [entry for entry in entries if entry is not None]
        
        if len(valid_entries) <= target_size:
            return valid_entries
        
        # Categorize entries by price range
        categorized = defaultdict(list)
        uncategorized = []
        
        for entry in valid_entries:
            price = self._extract_price(entry)
            if price is not None:
                price_range = self._classify_price_range(price)
                categorized[price_range].append(entry)
            else:
                uncategorized.append(entry)
        
        # Select balanced sample across price ranges
        selected = []
        price_ranges = list(categorized.keys())
        
        if price_ranges:
            per_range = max(1, target_size // len(price_ranges))
            
            for price_range in price_ranges:
                range_entries = categorized[price_range][:per_range]
                selected.extend(range_entries)
                
                if len(selected) >= target_size:
                    break
            
            # Fill remaining slots
            remaining_slots = target_size - len(selected)
            if remaining_slots > 0 and uncategorized:
                selected.extend(uncategorized[:remaining_slots])
        
        return selected[:target_size]

    def _select_regional_diversity(self, entries: List[Dict[str, Any]], target_size: int) -> List[Dict[str, Any]]:
        """Select entries with diverse wine regions."""
        # Filter out None entries
        valid_entries = [entry for entry in entries if entry is not None]
        
        if len(valid_entries) <= target_size:
            return valid_entries
        
        # Categorize entries by region
        categorized = defaultdict(list)
        uncategorized = []
        
        for entry in valid_entries:
            text = entry.get('text', '').lower()
            region = self._identify_region(text)
            
            if region:
                categorized[region].append(entry)
            else:
                uncategorized.append(entry)
        
        # Select balanced sample across regions
        selected = []
        regions = list(categorized.keys())
        
        if regions:
            per_region = max(1, target_size // len(regions))
            
            for region in regions:
                region_entries = categorized[region][:per_region]
                selected.extend(region_entries)
                
                if len(selected) >= target_size:
                    break
            
            # Fill remaining slots
            remaining_slots = target_size - len(selected)
            if remaining_slots > 0 and uncategorized:
                selected.extend(uncategorized[:remaining_slots])
        
        return selected[:target_size]

    def _classify_wine_type(self, text: str) -> Optional[str]:
        """Classify wine type from text."""
        text_lower = text.lower()
        
        for wine_type, keywords in self.wine_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return wine_type
        
        return None

    def _extract_price(self, entry: Dict[str, Any]) -> Optional[float]:
        """Extract price from entry."""
        # Try to get price from extracted fields
        price_data = entry.get('price', {})
        if isinstance(price_data, dict):
            price_value = price_data.get('value')
        else:
            price_value = price_data
        
        if price_value:
            # Extract numeric value
            price_match = re.search(r'(\d+(?:\.\d{2})?)', str(price_value))
            if price_match:
                return float(price_match.group(1))
        
        # Fallback: extract from text
        text = entry.get('text', '')
        price_match = re.search(r'(\d+(?:\.\d{2})?)', text)
        if price_match:
            return float(price_match.group(1))
        
        return None

    def _classify_price_range(self, price: float) -> str:
        """Classify price into range category."""
        for range_name, (min_price, max_price) in self.price_ranges.items():
            if min_price <= price < max_price:
                return range_name
        return 'premium'

    def _identify_region(self, text: str) -> Optional[str]:
        """Identify wine region from text."""
        text_lower = text.lower()
        
        for region in self.wine_regions:
            if region in text_lower:
                return region
        
        return None

    def _calculate_diversity_score(self, entry: Dict[str, Any]) -> float:
        """Calculate diversity score for an entry."""
        score = 0.0
        text = entry.get('text', '').lower()
        
        # Wine type diversity
        wine_type = self._classify_wine_type(text)
        if wine_type:
            score += 0.3
        
        # Price diversity
        price = self._extract_price(entry)
        if price is not None:
            score += 0.2
        
        # Regional diversity
        region = self._identify_region(text)
        if region:
            score += 0.1
        
        # Regex failure bonus
        if '_regex_failure_reason' in entry:
            score += 0.4
        
        return min(1.0, score)

    def _get_selection_reason(self, entry: Dict[str, Any], 
                            regex_selected: List[Dict], 
                            wine_type_selected: List[Dict],
                            price_selected: List[Dict],
                            region_selected: List[Dict]) -> str:
        """Get the reason why this entry was selected."""
        if entry in regex_selected:
            return "regex_failure"
        elif entry in wine_type_selected:
            return "wine_type_diversity"
        elif entry in price_selected:
            return "price_diversity"
        elif entry in region_selected:
            return "regional_diversity"
        else:
            return "fallback"

    def get_sampling_statistics(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about the sampling process."""
        total_entries = len(entries)
        
        # Analyze wine type distribution
        wine_type_counts = defaultdict(int)
        for entry in entries:
            wine_type = self._classify_wine_type(entry.get('text', ''))
            if wine_type:
                wine_type_counts[wine_type] += 1
        
        # Analyze price distribution
        price_range_counts = defaultdict(int)
        for entry in entries:
            price = self._extract_price(entry)
            if price is not None:
                price_range = self._classify_price_range(price)
                price_range_counts[price_range] += 1
        
        # Analyze regional distribution
        region_counts = defaultdict(int)
        for entry in entries:
            region = self._identify_region(entry.get('text', ''))
            if region:
                region_counts[region] += 1
        
        # Analyze regex failures
        regex_failures = self._identify_regex_failures(entries)
        
        return {
            'total_entries': total_entries,
            'wine_type_distribution': dict(wine_type_counts),
            'price_range_distribution': dict(price_range_counts),
            'regional_distribution': dict(region_counts),
            'regex_failures_count': len(regex_failures),
            'regex_failure_rate': len(regex_failures) / total_entries if total_entries > 0 else 0
        } 