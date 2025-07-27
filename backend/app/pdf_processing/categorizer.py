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
                    wine_blocks.append(self._create_wine_block(current_block, page_num))
                    current_block = []
                current_block.append(text)
            elif current_block:
                current_block.append(text)
        
        # Add the last block if it exists
        if current_block:
            wine_blocks.append(self._create_wine_block(current_block, page_num))
        
        return wine_blocks

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