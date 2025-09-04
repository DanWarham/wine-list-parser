import logging
import re
from typing import List, Dict, Any, Optional

# Try to import database manager, but make it optional for testing
try:
    from app.database_enhanced_rules.database_manager import get_database_manager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    get_database_manager = None

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
        
        # Separate concerns - no more mixing of different categories
        self.producer_indicators = wine_terms or [
            'chateau', 'domaine', 'estate', 'vineyard', 'cellar', 'winery', 'bodega', 'cantina'
        ]
        
        # Type indicators for wine classification
        self.wine_type_indicators = [
            'rouge', 'rose', 'blanc', 'noir', 'sparkling', 'still', 'fortified', 'dessert', 'aperitif'
        ]
        
        # Legacy region terms for backward compatibility (will be replaced by database)
        self.legacy_region_terms = region_terms or [
            'burgundy', 'bordeaux', 'champagne', 'alsace', 'loire', 'rhone',
            'tuscany', 'piedmont', 'veneto', 'rioja', 'ribera', 'priorat',
            'napa', 'sonoma', 'oregon', 'washington', 'barossa', 'mclaren',
            'margaret river', 'marlborough', 'central otago'
        ]

class PDFBlockCategorizer:
    def __init__(self, config: Optional[CategorizerConfig] = None):
        logger.info("[PDFBlockCategorizer] __init__ called.")
        self.config = config or CategorizerConfig()
        
        # Initialize database manager for enhanced categorization
        if DATABASE_AVAILABLE and get_database_manager:
            try:
                self.db_manager = get_database_manager()
                self.db_manager.load_databases()
                logger.info("[PDFBlockCategorizer] Database manager initialized successfully")
            except Exception as e:
                logger.warning(f"[PDFBlockCategorizer] Failed to initialize database manager: {e}")
                self.db_manager = None
        else:
            logger.warning("[PDFBlockCategorizer] Database manager not available - running in fallback mode")
            self.db_manager = None

    def categorize(self, preprocessed_data: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Categorize preprocessed text into different block types."""
        logger.info("[PDFBlockCategorizer] Starting categorization")
        
        categorized_blocks = []
        for page_num, page_lines in enumerate(preprocessed_data):
            page_blocks = self._categorize_page(page_lines, page_num)
            categorized_blocks.extend(page_blocks)
        
        logger.info(f"[PDFBlockCategorizer] Completed categorization - {len(preprocessed_data)} pages, {len(categorized_blocks)} blocks")
        return categorized_blocks
    
    def _categorize_page(self, page_lines: List[Dict[str, Any]], page_num: int) -> List[Dict[str, Any]]:
        """Categorize a single page into different block types."""
        categorized_blocks = []
        current_block = []
        
        for line in page_lines:
            text = line.get('text', '')
            
            # Determine the category of this line using both text and spatial data
            category = self._categorize_block(text, line)
            
            if category == 'wine':
                # If we have a current block, process it first
                if current_block:
                    categorized_blocks.extend(self._process_wine_block(current_block, page_num))
                    current_block = []
                current_block.append(text)
            else:
                # For non-wine blocks, add them immediately
                if current_block:
                    # Process the current wine block before adding this non-wine block
                    categorized_blocks.extend(self._process_wine_block(current_block, page_num))
                    current_block = []
                
                # Add the non-wine block
                categorized_blocks.append(self._create_categorized_block([text], page_num, category))
        
        # Process the last wine block if it exists
        if current_block:
            categorized_blocks.extend(self._process_wine_block(current_block, page_num))
        
        return categorized_blocks
    
    def _categorize_block(self, text: str, block_data: Optional[Dict[str, Any]] = None) -> str:
        """Determine the category of a text block using text content and spatial clues."""
        # Check wine first (most specific)
        if self._is_wine_line(text):
            return 'wine'
        # Then check header (most general)
        elif self._is_header(text, block_data):
            return 'header'
        # Then check subheader
        elif self._is_subheader(text, block_data):
            return 'subheader'
        else:
            return 'other'
    
    def _create_categorized_block(self, text_lines: List[str], page_num: int, category: str) -> Dict[str, Any]:
        """Create a categorized block with the specified category."""
        return {
            'text': ' '.join(text_lines),
            'lines': text_lines,
            'page': page_num,
            'type': 'categorized_block',
            'category': category
        }

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
        
        # NEW: Check for the specific pattern from compagnie-des-vins-surnaturels
        # Pattern: Price followed by Producer (indicating multiple entries)
        # This happens when we have: "Price Producer • Wine Details • Vintage • Price"
        specific_pattern = r'\d+\s+[A-Z][A-Z\s\-&\.]+?\s*•'
        specific_matches = len(re.findall(specific_pattern, text))
        
        # Consider it multi-entry if we have multiple indicators
        indicators = [producer_matches, price_matches, vintage_matches, specific_matches]
        max_indicators = max(indicators) if indicators else 0
        
        # Debug logging for troubleshooting
        logger.debug(f"[Multi-entry detection] Text: {text[:100]}...")
        logger.debug(f"[Multi-entry detection] Bullet count: {bullet_count}, Producer matches: {producer_matches}, Price matches: {price_matches}, Vintage matches: {vintage_matches}, Specific matches: {specific_matches}")
        logger.debug(f"[Multi-entry detection] Max indicators: {max_indicators}, Result: {max_indicators > 1 or specific_matches > 0 or (bullet_count > 2 and max_indicators > 0)}")
        
        # Return True if we have multiple strong indicators OR the specific pattern
        return max_indicators > 1 or specific_matches > 0 or (bullet_count > 2 and max_indicators > 0)

    def _segment_multi_entries(self, text: str) -> List[str]:
        """Split text containing multiple wine entries into individual entries."""
        entries = []
        logger.debug(f"[Segmentation] Starting segmentation for text: {text[:100]}...")
        
        # NEW: Pattern 0: Handle the specific compagnie-des-vins-surnaturels pattern
        # Pattern: "Price Producer • Wine Details • Vintage • Price Producer • Wine Details • Vintage • Price"
        # Split on "Price Producer •" pattern
        specific_pattern = r'(\d+)\s+([A-Z][A-Z\s\-&\.]+?\s*•)'
        specific_matches = re.findall(specific_pattern, text)
        if specific_matches:
            logger.debug(f"[Segmentation] Found {len(specific_matches)} specific pattern matches")
            
            # Split the text on the pattern "Price Producer •"
            split_pattern = r'(\d+\s+[A-Z][A-Z\s\-&\.]+?\s*•)'
            parts = re.split(split_pattern, text)
            
            current_entry = ""
            for i, part in enumerate(parts):
                if re.match(split_pattern, part):
                    # This is a "Price Producer •" pattern - start a new entry
                    if current_entry.strip():
                        entries.append(current_entry.strip())
                    current_entry = part
                else:
                    current_entry += part
            
            # Add the last entry
            if current_entry.strip():
                entries.append(current_entry.strip())
            
            # If we found entries with this pattern, return them
            if entries:
                logger.debug(f"[Segmentation] Returning {len(entries)} entries from specific pattern")
                return self._clean_entries(entries)
        
        # Pattern 1: Look for complete wine entries with more flexible matching
        # Pattern: Producer • Wine Name - Type - Vintage • Price
        entry_pattern = r'([A-Z][A-Z\s\-&\.]+?\s*•\s*[^•]+?(?:•\s*(?:19|20)\d{2}|•\s*NV|•\s*V\d{2})\s*•\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
        
        matches = re.findall(entry_pattern, text)
        if matches:
            logger.debug(f"[Segmentation] Found {len(matches)} entries with pattern 1")
            entries.extend(matches)
        else:
            # Pattern 2: Split on bullet points followed by producer names
            producer_split_pattern = r'\s*•\s*(?=[A-Z][A-Z\s\-&\.]+?\s*•)'
            potential_entries = re.split(producer_split_pattern, text)
            
            for entry in potential_entries:
                entry = entry.strip()
                if entry and len(entry) > 10:
                    entries.append(entry)
            
            logger.debug(f"[Segmentation] Found {len(entries)} entries with pattern 2")
        
        # If still no entries, try a simpler approach
        if not entries:
            # Split on bullet points that are followed by all-caps producer names
            simple_split_pattern = r'\s*•\s*(?=[A-Z][A-Z\s]+?\s*•)'
            parts = re.split(simple_split_pattern, text)
            
            for part in parts:
                part = part.strip()
                if part and len(part) > 10 and re.search(r'\d+', part):  # Has a price
                    entries.append(part)
            
            logger.debug(f"[Segmentation] Found {len(entries)} entries with simple pattern")
        
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
            
            logger.debug(f"[Segmentation] Found {len(entries)} entries with aggressive pattern")
        
        logger.debug(f"[Segmentation] Final result: {len(entries)} entries")
        return self._clean_entries(entries)
    
    def _clean_entries(self, entries: List[str]) -> List[str]:
        """Clean and validate wine entries."""
        cleaned_entries = []
        for entry in entries:
            entry = entry.strip()
            if self._is_valid_wine_entry(entry):
                cleaned_entries.append(entry)
        
        return cleaned_entries

    def _is_valid_wine_entry(self, text: str) -> bool:
        """Check if a text block represents a valid wine entry."""
        # Must have some wine-related content
        has_producer = any(term in text.lower() for term in self.config.producer_indicators)
        has_region = any(region in text.lower() for region in self.config.legacy_region_terms)
        has_grape = self._is_grape_variety(text)
        has_wine_type = any(term in text.lower() for term in self.config.wine_type_indicators)
        
        # Check for price or vintage as strong indicators
        has_price = bool(re.search(r'[€$£¥]\s*\d+', text))
        has_vintage = bool(re.search(r'\b(19|20)\d{2}\b', text))
        
        # Must have at least one wine indicator and one strong indicator
        wine_indicators = [has_producer, has_region, has_grape, has_wine_type]
        strong_indicators = [has_price, has_vintage]
        
        return any(wine_indicators) and any(strong_indicators)

    def _create_wine_block(self, text_lines: List[str], page_num: int) -> Dict[str, Any]:
        """Create a wine block from collected text lines."""
        return {
            'text': ' '.join(text_lines),
            'lines': text_lines,
            'page': page_num,
            'type': 'wine_entry',
            'category': 'wine'
        }

    def _is_header(self, text: str, block_data: Optional[Dict[str, Any]] = None) -> bool:
        """Check if text is a main header using text content and spatial clues."""
        # IMPORTANT: Grape varieties and region names should NEVER be headers
        # Check these first to override any spatial clues
        if self._is_grape_variety(text):
            return False
        if self._is_region_name(text):
            return False
        
        # Check for special headers that should always be headers
        if self._is_special_header(text):
            return True
        
        # Check configured patterns first
        for pattern in self.config.header_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check for spatial/formatting clues if block_data is available
        if block_data:
            # Check font size (headers are usually larger)
            font_size = block_data.get('font_size', 0)
            if font_size > 12:  # Adjust threshold as needed
                return True
            
            # Check for bold text
            if block_data.get('is_bold', False):
                return True
            
            # Check for centered text
            if block_data.get('is_centered', False):
                return True
        
        # Check for ALL-CAPS text (common for headers)
        if text.isupper() and len(text.split()) >= 2:
            return True
        
        # Check for title case text (common for headers)
        if text.istitle() and len(text.split()) >= 2:
            return True
        
        # Check for text that ends with common header patterns
        header_endings = ['WINES', 'WINE', 'REGION', 'REGIONS', 'VARIETIES', 'VARIETY']
        for ending in header_endings:
            if text.upper().endswith(ending):
                return True
        
        # Check for text that starts with common header patterns
        header_startings = ['THE ', 'ALL ', 'SELECTION OF ', 'CHOICE OF ']
        for starting in header_startings:
            if text.upper().startswith(starting):
                return True
        
        return False
    
    def _is_special_header(self, text: str) -> bool:
        """Check if text is a special header that should always be classified as a header."""
        text_upper = text.upper()
        
        # Check for special region combinations
        special_headers = [
            "GERMANY + AUSTRIA + SWITZERLAND",
            "FRANCE + ITALY + SPAIN",
            "NEW WORLD",
            "OLD WORLD",
            "EUROPE",
            "AMERICAS",
            "ASIA PACIFIC"
        ]
        
        for header in special_headers:
            if header in text_upper:
                return True
        
        # Check for wine type categories
        wine_categories = [
            "CHAMPAGNE",
            "SPARKLING",
            "DESSERT WINES",
            "FORTIFIED WINES",
            "ROSE WINES",
            "WHITE WINES",
            "RED WINES"
        ]
        
        for category in wine_categories:
            if category in text_upper:
                return True
        
        # Check for producer categories
        producer_categories = [
            "GRAND CRU",
            "PREMIER CRU",
            "CHATEAU",
            "DOMAINE",
            "ESTATE",
            "WINERY"
        ]
        
        for category in producer_categories:
            if category in text_upper:
                return True
        
        return False
    
    def _has_header_spatial_characteristics(self, block_data: Dict[str, Any]) -> bool:
        """Check if block has spatial characteristics typical of headers."""
        # Check for larger font size
        font_size = block_data.get('font_size', 0)
        if font_size > 12:  # Adjust threshold as needed
            return True
        
        # Check for bold text
        if block_data.get('is_bold', False):
            return True
        
        # Check for centered text
        if block_data.get('is_centered', False):
            return True
        
        # Check for text that's positioned higher on the page (headers are usually at top)
        bbox = block_data.get('bbox', {})
        if 'y0' in bbox:
            # Lower y0 means higher on page
            if bbox['y0'] < 100:  # Adjust threshold as needed
                return True
        
        # Check for text with more whitespace around it
        if block_data.get('has_whitespace_above', False):
            return True
        
        return False

    def _is_subheader(self, text: str, block_data: Optional[Dict[str, Any]] = None) -> bool:
        """Check if text is a subheader."""
        # Check configured patterns first
        for pattern in self.config.subheader_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Check if it's a grape variety (should be subheader)
        if self._is_grape_variety(text):
            return True
        
        # Check if it's a region name (should be subheader)
        if self._is_region_name(text):
            return True
        
        # Additional subheader detection logic
        text_upper = text.upper()
        
        # Common subheader indicators (specific wine styles, appellations, etc.)
        subheader_indicators = [
            'PROSECCO', 'CAVA', 'CREMANT', 'FRANCIACORTA',
            'PINOT GRIS', 'PINOT GRIGIO', 'GEWURZTRAMINER',
            'PULIGNY-MONTRACHET', 'MEURSAULT', 'CHABLIS',
            'MARGEAUX', 'PAUILLAC', 'SAINT-EMILION',
            'BAROLO', 'BARBARESCO', 'BRUNELLO', 'AMARONE',
            'CHIANTI', 'CHIANTI CLASSICO', 'SUPER TUSCAN'
        ]
        
        # Check if text contains subheader indicators
        for indicator in subheader_indicators:
            if indicator in text_upper:
                return True
        
        # Check for mixed case text that's not too long (likely subheaders)
        if len(text.strip()) > 3 and len(text.strip()) < 40:
            # Has some capitalization but not all caps
            has_caps = any(c.isupper() for c in text)
            has_lower = any(c.islower() for c in text)
            
            if has_caps and has_lower:
                # Exclude if it looks like a wine entry
                if not self._looks_like_wine_entry(text):
                    return True
        
        # Use spatial clues if available
        if block_data and 'bbox' in block_data:
            if self._has_subheader_spatial_characteristics(block_data):
                return True
        
        return False
    
    def _has_subheader_spatial_characteristics(self, block_data: Dict[str, Any]) -> bool:
        """Check if a block has spatial characteristics typical of subheaders."""
        if 'bbox' not in block_data:
            return False
        
        bbox = block_data['bbox']
        if len(bbox) != 4:
            return False
        
        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0
        
        # Subheaders are typically:
        # 1. Medium height (between header and body text)
        # 2. Positioned below main headers but above wine entries
        # 3. Often indented or have specific alignment
        
        # Check if height suggests subheader font size (typically 10-14pt)
        # Assuming 72 DPI, 10pt = 10 pixels, 14pt = 14 pixels
        if 8 <= height <= 16:
            return True
        
        # Check if positioned in middle section of page
        # Not at very top (not main header) and not at bottom
        if 100 < y0 < 600:  # Middle section of typical page
            return True
        
        # Check if text has moderate width (not too narrow, not too wide)
        if 50 < width < 200:
            return True
        
        return False
    
    def _looks_like_wine_entry(self, text: str) -> bool:
        """Check if text has the structure of a wine entry."""
        # Check for common wine entry patterns
        # Producer - Wine Name - Vintage - Price
        # Producer - Grape Variety - Vintage - Price
        # Wine Name - Producer - Vintage - Price
        
        # Split by common separators
        parts = re.split(r'[•·\-\–\—\s]{2,}', text.strip())
        if len(parts) < 2:
            return False
        
        # Check if parts contain wine-related terms
        wine_terms = 0
        for part in parts:
            part_lower = part.lower()
            if any(term in part_lower for term in self.config.producer_indicators):
                wine_terms += 1
            if any(term in part_lower for term in self.config.wine_type_indicators):
                wine_terms += 1
            if self._is_grape_variety(part):
                wine_terms += 1
            if self._is_region_name(part):
                wine_terms += 1
        
        # If it has at least 2 wine-related terms, it's likely a wine entry
        return wine_terms >= 2

    def _is_grape_variety(self, text: str) -> bool:
        """Check if text represents a grape variety name."""
        text_clean = text.strip().lower()
        
        # First try database lookup if available
        if self.db_manager:
            try:
                # Search for grape variety in database
                results = self.db_manager.search_grape_variety(text_clean, threshold=0.7)
                if results and results[0][1] >= 0.7:  # Good match found
                    logger.debug(f"Database grape variety match: '{text}' -> {results[0][0]} (confidence: {results[0][1]:.2f})")
                    return True
            except Exception as e:
                logger.debug(f"Database grape variety lookup failed: {e}")
        
        # Fallback to common grape variety patterns
        common_grapes = [
            'pinot noir', 'chardonnay', 'cabernet sauvignon', 'merlot', 'syrah', 'shiraz',
            'sauvignon blanc', 'riesling', 'gewurztraminer', 'pinot gris', 'pinot blanc',
            'grenache', 'mourvedre', 'carignan', 'cinsault', 'viognier', 'marsanne',
            'roussanne', 'aligote', 'gamay', 'nebbiolo', 'barbera', 'dolcetto',
            'sangiovese', 'corvina', 'rondinella', 'garganega', 'nero d\'avola',
            'tempranillo', 'garnacha', 'monastrell', 'albarino', 'verdejo'
        ]
        
        return text_clean in common_grapes
    
    def _is_region_name(self, text: str) -> bool:
        """Check if text represents a wine region name."""
        text_clean = text.strip().lower()
        
        # First try database lookup if available
        if self.db_manager:
            try:
                # Get all regions from database
                all_regions = set()
                regions_data = self.db_manager._databases.get('regions', {})
                
                # Extract country names
                all_regions.update(regions_data.keys())
                
                # Extract region names from each country
                for country_regions in regions_data.values():
                    if isinstance(country_regions, dict):
                        all_regions.update(country_regions.keys())
                        # Extract sub-region names
                        for sub_regions in country_regions.values():
                            if isinstance(sub_regions, list):
                                all_regions.update(sub_regions)
                
                # Check for exact or close matches
                for region in all_regions:
                    if text_clean == region.lower() or text_clean in region.lower() or region.lower() in text_clean:
                        logger.debug(f"Database region match: '{text}' -> {region}")
                        return True
                        
            except Exception as e:
                logger.debug(f"Database region lookup failed: {e}")
        
        # Fallback to legacy region terms
        return text_clean in self.config.legacy_region_terms

    def _is_wine_line(self, text: str) -> bool:
        """Check if a text line represents a wine entry."""
        text_lower = text.lower()
        
        # Check for wine exclusion patterns first
        for pattern in self.config.wine_exclusion_patterns:
            if re.search(pattern, text_lower):
                return False
        
        # Check for special headers that should never be wines
        if self._is_special_header(text):
            return False
        
        # Check for price indicators (€, $, £, etc.)
        has_price = bool(re.search(r'[€$£¥]\s*\d+', text))
        
        # Check for vintage indicators (4-digit years)
        has_vintage = bool(re.search(r'\b(19|20)\d{2}\b', text))
        
        # Check for bullet points or separators (common in wine lists)
        has_separators = bool(re.search(r'[•·\-\–\—]', text))
        
        # Check for producer indicators (chateau, domaine, etc.)
        has_producer = any(term in text_lower for term in self.config.producer_indicators)
        
        # Check for wine type indicators
        has_wine_type = any(term in text_lower for term in self.config.wine_type_indicators)
        
        # Check for grape varieties (using database if available)
        has_grape = self._is_grape_variety(text)
        
        # Check for region names (using database if available)
        has_region = self._is_region_name(text)
        
        # A line is a wine entry if it has:
        # 1. Price OR vintage, AND
        # 2. At least one of: producer indicator, wine type, grape variety, or region
        if has_price or has_vintage:
            return has_producer or has_wine_type or has_grape or has_region
        
        # If no price/vintage, it might still be a wine entry if it has multiple wine indicators
        wine_indicators = [has_producer, has_wine_type, has_grape, has_region]
        if sum(wine_indicators) >= 2:  # At least 2 wine indicators
            return True
        
        # If it has separators and at least one wine indicator, it's likely a wine entry
        if has_separators and any(wine_indicators):
            return True
        
        # Additional check: if it looks like a wine entry structure
        if self._looks_like_wine_entry(text):
            return True
        
        return False