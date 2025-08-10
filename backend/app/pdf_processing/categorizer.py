import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

logger.info("[PDFBlockCategorizer] Module loaded.")

class CategorizerConfig:
    def __init__(self,
                 header_patterns=None,
                 subheader_patterns=None,
                 wine_exclusion_patterns=None,
                 wine_terms=None,
                 region_terms=None):
        self.header_patterns = header_patterns or [r'^[A-Z\s\-]+$', r'^CHAMPAGNE$', r'^ROS[ÉE]$', r'^MAGNUMS?$']
        self.subheader_patterns = subheader_patterns or [r'^[A-Z][a-z]+,?\s+[A-Z][a-z]+']
        self.wine_exclusion_patterns = wine_exclusion_patterns or [
            r'by\s+the\s+glass', r'wine\s+pairing', r'beer', r'cocktail', r'spirit', r'liquor', r'whiskey', r'vodka', r'gin', r'rum', r'tequila']
        self.wine_terms = wine_terms or [
            'wine', 'chateau', 'domaine', 'estate', 'vineyard', 'cellar',
            'pinot', 'chardonnay', 'cabernet', 'merlot', 'syrah', 'grenache',
            'sauvignon', 'blanc', 'noir', 'rouge', 'rose', 'sparkling',
            'champagne', 'burgundy', 'bordeaux', 'italy', 'spain', 'france',
            'germany', 'australia', 'usa', 'new zealand', 'chile', 'argentina']
        self.region_terms = region_terms or [
            'burgundy', 'bordeaux', 'champagne', 'alsace', 'loire', 'rhone',
            'tuscany', 'piedmont', 'veneto', 'rioja', 'ribera', 'priorat',
            'napa', 'sonoma', 'oregon', 'washington', 'barossa', 'mclaren',
            'margaret river', 'marlborough', 'central otago']

class PDFBlockCategorizer:
    def __init__(self, config: Optional[CategorizerConfig] = None):
        logger.info("[PDFBlockCategorizer] __init__ called.")
        self.config = config or CategorizerConfig()

    def categorize(self, preprocessed_data: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Categorize preprocessed text into wine list entries."""
        logger.info("[PDFBlockCategorizer] Starting categorization")
        
        wine_blocks = []
        for page_num, page_lines in enumerate(preprocessed_data):
            page_blocks = self._categorize_page(page_lines, page_num)
            wine_blocks.extend(page_blocks)
        
        logger.info(f"[PDFBlockCategorizer] Completed categorization - {len(preprocessed_data)} pages, {len(wine_blocks)} blocks")
        return wine_blocks
    
    def _categorize_page(self, page_lines: List[Dict[str, Any]], page_num: int) -> List[Dict[str, Any]]:
        """Categorize a single page into wine blocks."""
        wine_blocks = []
        current_block = []
        
        for line in page_lines:
            text = line.get('text', '')
            if self._is_wine_line(text):
                if current_block:
                    # Process the current block before starting a new one
                    wine_blocks.extend(self._process_wine_block(current_block, page_num))
                    current_block = []
                current_block.append(text)
            elif current_block:
                current_block.append(text)
        
        # Process the last block if it exists
        if current_block:
            wine_blocks.extend(self._process_wine_block(current_block, page_num))
        
        return wine_blocks

    def _process_wine_block(self, text_lines: List[str], page_num: int) -> List[Dict[str, Any]]:
        """Process a wine block, potentially splitting it into multiple entries."""
        # Join all lines into a single text block
        combined_text = ' '.join(text_lines)
        
        # Check if this block contains multiple wine entries
        if self._is_multi_entry_block(combined_text):
            # Split into individual entries
            entries = self._segment_multi_entries(combined_text)
            wine_blocks = []
            
            for entry in entries:
                if self._is_valid_wine_entry(entry):
                    wine_blocks.append(self._create_wine_block([entry], page_num))
            
            return wine_blocks
        else:
            # Single entry, return as is
            return [self._create_wine_block(text_lines, page_num)]

    def _is_multi_entry_block(self, text: str) -> bool:
        """Determine if a text block contains multiple wine entries."""
        # Count bullet points that are likely entry separators
        bullet_count = text.count('•')
        
        # Look for patterns that indicate multiple entries
        # Pattern: Producer • Wine Name - Type - Vintage • Price
        # Multiple entries will have this pattern repeated
        
        # Check for multiple producer names (all caps followed by bullet)
        producer_pattern = r'[A-Z][A-Z\s\-&\.]+?\s*•'
        producer_matches = len(re.findall(producer_pattern, text))
        
        # Check for multiple prices at the end of entries
        price_pattern = r'•\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*(?=[A-Z]|$)'
        price_matches = len(re.findall(price_pattern, text))
        
        # Check for multiple vintages
        vintage_pattern = r'•\s*(?:19|20)\d{2}\s*•'
        vintage_matches = len(re.findall(vintage_pattern, text))
        
        # Consider it multi-entry if we have multiple indicators
        indicators = [producer_matches, price_matches, vintage_matches]
        max_indicators = max(indicators) if indicators else 0
        
        # Return True if we have multiple strong indicators
        return max_indicators > 1 or (bullet_count > 2 and max_indicators > 0)

    def _segment_multi_entries(self, text: str) -> List[str]:
        """Split text containing multiple wine entries into individual entries."""
        entries = []
        
        # Pattern 1: Look for complete wine entries with more flexible matching
        # Pattern: Producer • Wine Name - Type - Vintage • Price
        entry_pattern = r'([A-Z][A-Z\s\-&\.]+?\s*•\s*[^•]+?(?:•\s*(?:19|20)\d{2}|•\s*NV|•\s*V\d{2})\s*•\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
        
        matches = re.findall(entry_pattern, text)
        if matches:
            entries.extend(matches)
        else:
            # Pattern 2: Split on bullet points followed by producer names
            producer_split_pattern = r'\s*•\s*(?=[A-Z][A-Z\s\-&\.]+?\s*•)'
            potential_entries = re.split(producer_split_pattern, text)
            
            for entry in potential_entries:
                entry = entry.strip()
                if entry and len(entry) > 10:
                    entries.append(entry)
        
        # If still no entries, try a simpler approach
        if not entries:
            # Split on bullet points that are followed by all-caps producer names
            simple_split_pattern = r'\s*•\s*(?=[A-Z][A-Z\s]+?\s*•)'
            parts = re.split(simple_split_pattern, text)
            
            for part in parts:
                part = part.strip()
                if part and len(part) > 10 and re.search(r'\d+', part):  # Has a price
                    entries.append(part)
        
        # If still no entries, try the most aggressive approach
        if not entries:
            # Split on any bullet point that's followed by a price and then a producer
            aggressive_pattern = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*•\s*(?=[A-Z][A-Z\s]+)'
            parts = re.split(aggressive_pattern, text)
            
            current_entry = ""
            for i, part in enumerate(parts):
                if re.match(r'\d+', part):  # This is a price
                    current_entry += part
                    if current_entry.strip():
                        entries.append(current_entry.strip())
                    current_entry = ""
                else:
                    current_entry += part
            
            # Add the last part if it exists
            if current_entry.strip():
                entries.append(current_entry.strip())
        
        # Clean up entries
        cleaned_entries = []
        for entry in entries:
            entry = entry.strip()
            if self._is_valid_wine_entry(entry):
                cleaned_entries.append(entry)
        
        return cleaned_entries

    def _is_valid_wine_entry(self, text: str) -> bool:
        """Check if a text segment is a valid wine entry."""
        if not text or len(text) < 10:
            return False
        
        # Must have at least a price or vintage
        has_price = bool(re.search(r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?', text))
        has_vintage = bool(re.search(r'\b(19|20)\d{2}\b|NV', text))
        
        # Must have some wine-related content
        has_wine_term = any(term in text.lower() for term in self.config.wine_terms)
        has_region = any(region in text.lower() for region in self.config.region_terms)
        
        return (has_price or has_vintage) and (has_wine_term or has_region)

    def _create_wine_block(self, text_lines: List[str], page_num: int) -> Dict[str, Any]:
        """Create a wine block from collected text lines."""
        return {
            'text': ' '.join(text_lines),
            'lines': text_lines,
            'page': page_num,
            'type': 'wine_entry'
        }

    def _is_header(self, text: str) -> bool:
        for pattern in self.config.header_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_subheader(self, text: str) -> bool:
        for pattern in self.config.subheader_patterns:
            if re.match(pattern, text):
                return True
        return False

    def _is_wine_line(self, text: str) -> bool:
        # Exclude lines matching exclusion patterns
        for pattern in self.config.wine_exclusion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        # Require price or vintage
        has_price = bool(re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?", text))
        has_vintage = bool(re.search(r"\b(19|20)\d{2}\b", text))
        has_wine_term = any(term in text.lower() for term in self.config.wine_terms)
        has_region = any(region in text.lower() for region in self.config.region_terms)
        result = (has_price or has_vintage) and (has_wine_term or has_region or has_price or has_vintage)
        if not (has_price or has_vintage):
            return False
        return has_wine_term or has_region or has_price or has_vintage 