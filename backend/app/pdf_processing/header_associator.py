"""
Header-Wine Association Module

This module analyzes the structure of wine lists to associate section headers
(such as regions, grape varieties, wine types) with the wine entries that follow them.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SectionHeader:
    """Represents a section header with its metadata."""
    text: str
    level: int  # 1 = main section, 2 = subsection, etc.
    position: int  # Position in the text blocks
    confidence: float  # How confident we are this is a header
    header_type: str  # 'region', 'grape_variety', 'wine_type', 'producer', 'other'
    associated_wines: List[int]  # Indices of wine entries associated with this header
    page: int = 1  # Page number for deduplication

@dataclass
class WineEntry:
    """Represents a wine entry with its associated header."""
    text: str
    position: int
    producer: Optional[str] = None
    wine_name: Optional[str] = None
    vintage: Optional[str] = None
    region: Optional[str] = None
    grape_variety: Optional[str] = None
    price: Optional[str] = None
    associated_header: Optional[SectionHeader] = None

class HeaderWineAssociator:
    """
    Analyzes wine list structure to associate section headers with wine entries.
    
    This class identifies hierarchical structure in wine lists and creates
    meaningful associations between headers and the wines they categorize.
    """
    
    def __init__(self):
        # Prefer database-driven detection like the categorizer
        try:
            from ..database_enhanced_rules.database_manager import get_database_manager
            self.db_manager = get_database_manager()
            self.db_manager.load_databases()
            logger.info("HeaderWineAssociator initialized with database manager")
        except Exception as e:
            logger.warning(f"HeaderWineAssociator database init failed, falling back to regex lists: {e}")
            self.db_manager = None
        
        # Enhanced header patterns for better recognition
        self.header_patterns = {
            'region': [
                r'^[A-Z][A-Z\s\-]+$',  # All caps regions
                r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title case regions
                r'^[A-Z][A-Z\s&]+[A-Z]$',  # Multi-word regions with & (e.g., "GERMANY + AUSTRIA + SWITZERLAND")
            ],
            'grape_variety': [
                r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title case grape names
            ],
            'wine_type': [
                r'^[A-Z][A-Z\s\-]+$',  # All caps wine types
                r'^CHAMPAGNE$',  # Special case for Champagne
                r'^ROS[ÉE]$',  # Rose/Rosé
                r'^MAGNUMS?$',  # Magnums
            ],
            'producer': [
                r'^(CHÂTEAU|DOMAINE|TENUTA|AZIENDA|BODEGA|WEINGUT|WINERY|ESTATE)$'
            ]
        }
        self.compiled_patterns = {k: [re.compile(p, re.IGNORECASE) for p in v] for k, v in self.header_patterns.items()}
        logger.info("HeaderWineAssociator initialized")
    
    def analyze_wine_list_structure(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the complete structure of a wine list.
        
        Args:
            text_blocks: List of text blocks from PDF extraction
            
        Returns:
            Dictionary containing structured analysis with headers and wine entries
        """
        logger.info(f"Analyzing wine list structure for {len(text_blocks)} text blocks")
        
        # Step 1: Identify potential headers with improved logic
        headers = self._identify_headers_improved(text_blocks)
        
        # Step 2: Deduplicate headers
        headers = self._deduplicate_headers(headers)
        
        # Step 3: Identify wine entries
        wine_entries = self._identify_wine_entries(text_blocks)
        
        # Step 4: Associate headers with wines using improved logic
        self._associate_headers_with_wines_improved(headers, wine_entries, text_blocks)
        
        # Step 5: Build hierarchical structure
        structure = self._build_hierarchical_structure(headers, wine_entries)
        
        # Step 6: Prepare final analysis
        analysis = {
            'headers': [self._header_to_dict(h) for h in headers],
            'wine_entries': [self._wine_entry_to_dict(w) for w in wine_entries],
            'structure': structure,
            'summary': {
                'total_headers': len(headers),
                'total_wines': len(wine_entries),
                'headers_by_type': self._count_headers_by_type(headers),
                'wines_with_headers': sum(1 for w in wine_entries if w.associated_header),
                'structure_levels': max([h.level for h in headers]) if headers else 0
            }
        }
        
        logger.info(f"Analysis complete: {len(headers)} headers, {len(wine_entries)} wines")
        return analysis
    
    def _identify_headers_improved(self, text_blocks: List[Dict[str, Any]]) -> List[SectionHeader]:
        """Improved header identification using font size, boldness, and whitespace cues."""
        headers = []
        
        for i, block in enumerate(text_blocks):
            text = block.get('text', '').strip()
            if not text or len(text) < 2:
                continue
            
            # Skip blocks that are likely wine entries first
            if self._is_likely_wine_entry(text):
                logger.debug(f"Skipping wine entry: {text[:50]}...")
                continue
            
            # Check if this block looks like a header with improved logic
            header_info = self._analyze_header_candidate_improved(text, i, block)
            if header_info:
                # Additional validation to ensure this is actually a standalone header
                if self._validate_header_candidate_improved(text, text_blocks, i):
                    logger.debug(f"Creating header: {text[:50]}... (type: {header_info.header_type}, confidence: {header_info.confidence})")
                    headers.append(header_info)
                else:
                    logger.debug(f"Header validation failed for: {text[:50]}...")
        
        # Sort headers by position
        headers.sort(key=lambda h: h.position)
        
        logger.info(f"Identified {len(headers)} valid headers after validation")
        return headers
    
    def _analyze_header_candidate_improved(self, text: str, position: int, block_data: Dict[str, Any]) -> Optional[SectionHeader]:
        """Analyze a text block to determine if it's a header with improved logic."""
        # Skip very long text (likely not a header)
        if len(text) > 100:
            return None
        
        # Check for all-caps text (common header indicator)
        is_all_caps = text.isupper() and len(text) > 2
        
        # Check for numeric-only text (likely page numbers, not headers)
        if text.isdigit() and len(text) <= 3:
            return None
        
        # Check for special header patterns first
        if self._is_special_header(text):
            return SectionHeader(
                text=text,
                level=1,
                position=position,
                confidence=0.95,
                header_type='other',
                associated_wines=[],
                page=block_data.get('page', 1)
            )
        
        # Check database-driven matches first
        header_type = None
        confidence = 0.0
        text_clean = text.strip().lower()
        
        if self.db_manager:
            try:
                # Regions - be more conservative to avoid matching wine entries
                all_regions = set()
                regions_data = self.db_manager._databases.get('regions', {})
                all_regions.update(regions_data.keys())
                for country_regions in regions_data.values():
                    if isinstance(country_regions, dict):
                        all_regions.update(country_regions.keys())
                        for sub_regions in country_regions.values():
                            if isinstance(sub_regions, list):
                                all_regions.update(sub_regions)
                
                # Only match if the text is exactly a region name (not containing it)
                if text_clean in [r.lower() for r in all_regions]:
                    # Additional check: ensure this is a clean, standalone region name
                    if len(text.split()) == 1 and text.isalpha():
                        header_type = 'region'
                        confidence = 0.9
                    # Also check for standalone region names that are short and clean
                    elif len(text.split()) <= 2 and not any(char in text for char in ['•', '-', '–', '—']) and not re.search(r'\d', text):
                        header_type = 'region'
                        confidence = 0.8
                
                # Grapes - be more conservative
                if not header_type:
                    grape_results = self.db_manager.search_grape_variety(text_clean, threshold=0.85)
                    if grape_results and grape_results[0][1] >= 0.85:
                        header_type = 'grape_variety'
                        confidence = 0.9
            except Exception:
                pass
        
        # Fallback to enhanced regex patterns
        if not header_type:
            for type_name, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.match(text):
                        header_type = type_name
                        confidence = 0.8
                        break
                if header_type:
                    break
        
        # If no pattern match, use improved heuristics
        if not header_type:
            # Check for common header characteristics
            if is_all_caps:
                # Special case: if it's all caps but looks like a wine entry, don't classify as header
                if not self._looks_like_wine_entry(text):
                    header_type = 'other'
                    confidence = 0.7
            elif text.endswith(':') or text.endswith('.'):
                header_type = 'other'
                confidence = 0.6
            elif len(text.split()) <= 4 and any(word.isupper() for word in text.split()):
                # Title case text that's not too long
                if not self._looks_like_wine_entry(text):
                    header_type = 'other'
                    confidence = 0.5
        
        # Only return if we have reasonable confidence
        if confidence >= 0.5:
            # Determine header level based on characteristics
            level = 1 if confidence >= 0.8 else 2
            
            return SectionHeader(
                text=text,
                level=level,
                position=position,
                confidence=confidence,
                header_type=header_type,
                associated_wines=[],
                page=block_data.get('page', 1)
            )
        
        return None
    
    def _is_special_header(self, text: str) -> bool:
        """Check for special header patterns that should always be headers."""
        special_headers = [
            'CHAMPAGNE', 'ROSÉ', 'ROSE', 'MAGNUM', 'MAGNUMS',
            'WHITE', 'RED', 'SPARKLING', 'DESSERT', 'FORTIFIED',
            'BY THE GLASS', 'BY THE BOTTLE', 'HALF BOTTLE',
            'WINE LIST', 'WINELIST', 'WINE MENU', 'WINEMENU'
        ]
        
        # Check for multi-region headers like "GERMANY + AUSTRIA + SWITZERLAND"
        if '+' in text and text.isupper():
            return True
        
        # Check for exact matches
        if text.upper() in special_headers:
            return True
        
        # Check for variations
        text_upper = text.upper()
        for header in special_headers:
            if header in text_upper or text_upper in header:
                return True
        
        return False
    
    def _looks_like_wine_entry(self, text: str) -> bool:
        """Check if text contains patterns indicative of a wine entry."""
        text_lower = text.lower()
        
        # Check for price patterns
        has_price = bool(re.search(r'[€$£¥]\s*\d+', text))
        
        # Check for vintage patterns
        has_vintage = bool(re.search(r'\b(19|20)\d{2}\b', text))
        
        # Check for bullet points or separators
        has_separators = bool(re.search(r'[•·\-\–\—]', text))
        
        # Check for producer indicators
        producer_indicators = ['chateau', 'domaine', 'estate', 'vineyard', 'cellar', 'winery', 'bodega', 'cantina']
        has_producer = any(term in text_lower for term in producer_indicators)
        
        # If it has price or vintage, it's likely a wine entry
        if has_price or has_vintage:
            return True
        
        # If it has separators and multiple wine indicators, it's likely a wine entry
        wine_indicators = [has_producer]
        if has_separators and sum(wine_indicators) >= 1:
            return True
        
        return False
    
    def _deduplicate_headers(self, headers: List[SectionHeader]) -> List[SectionHeader]:
        """Remove duplicate headers based on text and page location."""
        seen = set()
        unique_headers = []
        
        for header in headers:
            # Create a key based on text and page for deduplication
            key = (header.text.lower().strip(), header.page)
            
            if key not in seen:
                seen.add(key)
                unique_headers.append(header)
            else:
                logger.debug(f"Deduplicating header: {header.text} (page {header.page})")
        
        logger.info(f"Deduplication: {len(headers)} -> {len(unique_headers)} headers")
        return unique_headers
    
    def _identify_wine_entries(self, text_blocks: List[Dict[str, Any]]) -> List[WineEntry]:
        """Identify potential wine entries in the text blocks."""
        wine_entries = []
        
        for i, block in enumerate(text_blocks):
            text = block.get('text', '').strip()
            if not text or len(text) < 5:
                continue
            
            # Check if this looks like a wine entry
            if self._is_likely_wine_entry(text):
                logger.debug(f"Creating wine entry: {text[:50]}...")
                wine_entry = WineEntry(
                    text=text,
                    position=i
                )
                
                # Extract basic wine information
                self._extract_basic_wine_info(wine_entry)
                wine_entries.append(wine_entry)
        
        logger.info(f"Identified {len(wine_entries)} wine entries")
        return wine_entries
    
    def _is_likely_wine_entry(self, text: str) -> bool:
        """Check if text is likely a wine entry."""
        # Look for wine-like patterns
        wine_indicators = [
            r'\d{4}',  # Vintage year
            r'\d+\.\d+',  # Price
            r'\d+',  # Any price number
            r'[A-Z][a-z]+ [A-Z][a-z]+',  # Producer name pattern
            r'[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+',  # Wine name pattern
        ]
        
        for pattern in wine_indicators:
            if re.search(pattern, text):
                return True
        
        # Check for common wine-related words
        wine_words = ['château', 'domaine', 'bodega', 'weingut', 'winery', 'estate', 'brut', 'extra-brut', 'rosé', 'blanc', 'rouge', 'pinot', 'chardonnay', 'sauvignon', 'cabernet', 'merlot', 'syrah', 'grenache', 'tempranillo', 'sangiovese', 'nebbiolo', 'barbera', 'dolcetto']
        text_lower = text.lower()
        if any(word in text_lower for word in wine_words):
            return True
        
        # Check for wine entry structure patterns
        if '•' in text or ' - ' in text:
            segments = text.replace('•', ' - ').split(' - ')
            if len(segments) >= 3:  # At least producer, wine name, and one other field
                return True
        
        # Check for price patterns at the end
        if re.search(r'\d+$', text.strip()):
            return True
        
        # Check for vintage patterns
        if re.search(r'\b(19|20)\d{2}\b', text):
            return True
        
        return False
    
    def _extract_basic_wine_info(self, wine_entry: WineEntry):
        """Extract basic wine information from text."""
        text = wine_entry.text
        
        # Extract vintage (4-digit year)
        vintage_match = re.search(r'\b(19|20)\d{2}\b', text)
        if vintage_match:
            wine_entry.vintage = vintage_match.group()
        
        # Extract price (number with decimal)
        price_match = re.search(r'\b\d+\.\d+\b', text)
        if price_match:
            wine_entry.price = price_match.group()
        
        # Extract producer (first capitalized words)
        words = text.split()
        producer_words = []
        for word in words:
            if word[0].isupper() and len(word) > 2:
                producer_words.append(word)
            else:
                break
        
        if producer_words:
            wine_entry.producer = ' '.join(producer_words)
        
        # Extract region from wine entry if available
        if self.db_manager:
            try:
                text_clean = text.lower()
                regions_data = self.db_manager._databases.get('regions', {})
                all_regions = set()
                all_regions.update(regions_data.keys())
                for country_regions in regions_data.values():
                    if isinstance(country_regions, dict):
                        all_regions.update(country_regions.keys())
                        for sub_regions in country_regions.values():
                            if isinstance(sub_regions, list):
                                all_regions.update(sub_regions)
                
                # Look for region mentions in the wine entry
                for region in all_regions:
                    if region.lower() in text_clean:
                        wine_entry.region = region
                        break
            except Exception:
                pass
        
        # Extract grape variety if mentioned
        grape_varieties = ['pinot noir', 'chardonnay', 'sauvignon blanc', 'cabernet sauvignon', 'merlot', 'syrah', 'grenache', 'tempranillo', 'sangiovese', 'nebbiolo', 'barbera', 'dolcetto']
        text_lower = text.lower()
        for grape in grape_varieties:
            if grape in text_lower:
                wine_entry.grape_variety = grape.title()
                break
    
    def _associate_headers_with_wines_improved(self, headers: List[SectionHeader], 
                                             wine_entries: List[WineEntry], 
                                             text_blocks: List[Dict[str, Any]]):
        """Improved header-wine association with multi-level hierarchy support."""
        logger.info(f"Associating {len(headers)} headers with {len(wine_entries)} wine entries")
        
        # Sort by position for proper association
        headers.sort(key=lambda h: h.position)
        wine_entries.sort(key=lambda w: w.position)
        
        # Create a map of position to header for quick lookup
        header_map = {h.position: h for h in headers}
        
        # Associate each wine entry with the nearest preceding header
        for wine_entry in wine_entries:
            # Find the closest preceding header
            closest_header = None
            min_distance = float('inf')
            
            for header in headers:
                if header.position < wine_entry.position:
                    distance = wine_entry.position - header.position
                    if distance < min_distance:
                        min_distance = distance
                        closest_header = header
            
            if closest_header:
                wine_entry.associated_header = closest_header
                closest_header.associated_wines.append(wine_entries.index(wine_entry))
                logger.debug(f"Associated wine '{wine_entry.text[:50]}...' with header '{closest_header.text}'")
            else:
                logger.debug(f"No header found for wine: {wine_entry.text[:50]}...")
    
    def _build_hierarchical_structure(self, headers: List[SectionHeader], 
                                    wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Build a hierarchical structure of the wine list."""
        structure = {
            'regions': {},
            'grape_varieties': {},
            'wine_types': {},
            'producers': {},
            'other': {},
            'structural_insights': []
        }
        
        # Group headers by type
        for header in headers:
            header_type = header.header_type
            if header_type == 'region':
                if header.text not in structure['regions']:
                    structure['regions'][header.text] = []
                structure['regions'][header.text].extend([wine_entries[i] for i in header.associated_wines])
            elif header_type == 'grape_variety':
                if header.text not in structure['grape_varieties']:
                    structure['grape_varieties'][header.text] = []
                structure['grape_varieties'][header.text].extend([wine_entries[i] for i in header.associated_wines])
            elif header_type == 'wine_type':
                if header.text not in structure['wine_types']:
                    structure['wine_types'][header.text] = []
                structure['wine_types'][header.text].extend([wine_entries[i] for i in header.associated_wines])
            elif header_type == 'producer':
                if header.text not in structure['producers']:
                    structure['producers'][header.text] = []
                structure['producers'][header.text].extend([wine_entries[i] for i in header.associated_wines])
            else:
                if header.text not in structure['other']:
                    structure['other'][header.text] = []
                structure['other'][header.text].extend([wine_entries[i] for i in header.associated_wines])
        
        # Add structural insights
        if structure['regions']:
            structure['structural_insights'].append(
                f"Wine list organized by {len(structure['regions'])} regions"
            )
        
        if structure['grape_varieties']:
            structure['structural_insights'].append(
                f"Wine list organized by {len(structure['grape_varieties'])} grape varieties"
            )
        
        if structure['wine_types']:
            structure['structural_insights'].append(
                f"Wine list organized by {len(structure['wine_types'])} wine types"
            )
        
        # Check for hierarchical organization
        level_counts = {}
        for header in headers:
            level = header.level
            if level not in level_counts:
                level_counts[level] = 0
            level_counts[level] += 1
        
        if len(level_counts) > 1:
            structure['structural_insights'].append(
                f"Hierarchical organization with {len(level_counts)} levels"
            )
        
        return structure
    
    def _count_headers_by_type(self, headers: List[SectionHeader]) -> Dict[str, int]:
        """Count headers by type for summary statistics."""
        counts = {}
        for header in headers:
            header_type = header.header_type
            counts[header_type] = counts.get(header_type, 0) + 1
        return counts
    
    def _header_to_dict(self, header: SectionHeader) -> Dict[str, Any]:
        """Convert SectionHeader to dictionary for JSON serialization."""
        return {
            'text': header.text,
            'level': header.level,
            'position': header.position,
            'confidence': header.confidence,
            'header_type': header.header_type,
            'associated_wines_count': len(header.associated_wines),
            'page': header.page
        }
    
    def _wine_entry_to_dict(self, wine_entry: WineEntry) -> Dict[str, Any]:
        """Convert WineEntry to dictionary for JSON serialization."""
        assoc_header_dict = None
        if wine_entry.associated_header:
            assoc_header_dict = {
                'text': wine_entry.associated_header.text,
                'level': wine_entry.associated_header.level,
                'position': wine_entry.associated_header.position,
                'confidence': wine_entry.associated_header.confidence,
                'header_type': wine_entry.associated_header.header_type,
            }
        return {
            'text': wine_entry.text,
            'position': wine_entry.position,
            'producer': wine_entry.producer,
            'wine_name': wine_entry.wine_name,
            'vintage': wine_entry.vintage,
            'region': wine_entry.region,
            'grape_variety': wine_entry.grape_variety,
            'price': wine_entry.price,
            'associated_header': assoc_header_dict
        }

    def _validate_header_candidate_improved(self, text: str, text_blocks: List[Dict[str, Any]], position: int) -> bool:
        """Improved validation that a potential header is actually a standalone header."""
        # Check if this looks like a wine entry first
        if self._looks_like_wine_entry(text):
            return False
        
        # Check if it's too long to be a header
        if len(text) > 50:
            return False
        
        # Check if it contains wine entry indicators
        wine_indicators = ['•', '-', '–', '—', '€', '$', '£', '¥']
        if any(indicator in text for indicator in wine_indicators):
            return False
        
        # Check if it contains numbers (likely not a header)
        if re.search(r'\d', text):
            return False
        
        # Check if it's a special header that should always be valid
        if self._is_special_header(text):
            return True
        
        # Check if it's all caps and reasonable length
        if text.isupper() and 3 <= len(text) <= 30:
            return True
        
        # Check if it's title case and reasonable length
        if (text[0].isupper() and 
            len(text.split()) <= 4 and 
            3 <= len(text) <= 40):
            return True
        
        return False
