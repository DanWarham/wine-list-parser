import re
from typing import List, Dict, Any, Tuple

# Enhanced exclusion patterns
EXCLUSION_PATTERNS = {
    'by_the_glass': [
        r"by\s+the\s+glass",
        r"glass\s+pour",
        r"glass\s+only",
        r"available\s+by\s+glass"
    ],
    'wine_pairing': [
        r"wine\s+pairing",
        r"pairing\s+menu",
        r"tasting\s+menu",
        r"flight"
    ],
    'non_wine': [
        r"beer",
        r"cocktail",
        r"spirit",
        r"liquor",
        r"whiskey",
        r"vodka",
        r"gin",
        r"rum",
        r"tequila"
    ]
}

# Bottle size patterns
BOTTLE_SIZE_PATTERNS = {
    'standard': r"\b(750ml|75cl|standard)\b",
    'half': r"\b(375ml|37\.5cl|half\s*bottle)\b",
    'magnum': r"\b(1\.5L|150cl|magnum)\b",
    'double_magnum': r"\b(3L|300cl|double\s*magnum)\b",
    'jeroboam': r"\b(3L|300cl|jeroboam)\b",
    'imperial': r"\b(6L|600cl|imperial)\b",
    'salmanazar': r"\b(9L|900cl|salmanazar)\b",
    'balthazar': r"\b(12L|1200cl|balthazar)\b",
    'nebuchadnezzar': r"\b(15L|1500cl|nebuchadnezzar)\b"
}

# Variant patterns
VARIANT_PATTERNS = {
    'vintage': r"\b(19|20)\d{2}\b",
    'reserve': r"\breserve\b",
    'special': r"\bspecial\b",
    'limited': r"\blimited\b",
    'single': r"\bsingle\b",
    'grand': r"\bgrand\b",
    'premier': r"\bpremier\b",
    'cru': r"\bcru\b"
}

def is_probable_wine_line(line: Dict[str, Any]) -> bool:
    """Enhanced wine line detection with better pattern matching."""
    text = line["text"].lower()
    
    # Skip if line is too short
    if len(text) < 3:
        return False
    
    # Skip if line matches exclusion patterns
    for pattern_group in EXCLUSION_PATTERNS.values():
        if any(re.search(pattern, text) for pattern in pattern_group):
            return False
    
    # Check for price pattern
    has_price = bool(re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?", text))
    
    # Check for vintage pattern
    has_vintage = bool(re.search(r"\b(19|20)\d{2}\b", text))
    
    # Expanded list of wine terms
    wine_terms = [
        "wine", "chateau", "domaine", "estate", "vineyard", "cellar",
        "pinot", "chardonnay", "cabernet", "merlot", "syrah", "grenache",
        "sauvignon", "blanc", "noir", "rouge", "rose", "sparkling",
        "champagne", "burgundy", "bordeaux", "italy", "spain", "france",
        "germany", "australia", "usa", "new zealand", "chile", "argentina"
    ]
    has_wine_term = any(term in text for term in wine_terms)
    
    # Check for bottle size
    has_bottle_size = any(re.search(pattern, text) for pattern in BOTTLE_SIZE_PATTERNS.values())
    
    # Check for common wine-producing regions
    wine_regions = [
        "burgundy", "bordeaux", "champagne", "alsace", "loire", "rhone",
        "tuscany", "piedmont", "veneto", "rioja", "ribera", "priorat",
        "napa", "sonoma", "oregon", "washington", "barossa", "mclaren",
        "margaret river", "marlborough", "central otago"
    ]
    has_region = any(region in text for region in wine_regions)
    
    # Line is probably a wine if it has:
    # 1. Price, OR
    # 2. Vintage and (wine term OR region), OR
    # 3. Bottle size, OR
    # 4. Two or more wine terms/regions
    wine_term_count = sum(1 for term in wine_terms + wine_regions if term in text)
    has_multiple_terms = wine_term_count >= 2
    
    return has_price or (has_vintage and (has_wine_term or has_region)) or has_bottle_size or has_multiple_terms

def is_probable_continuation(line: Dict[str, Any], prev_line: Dict[str, Any]) -> bool:
    """Enhanced continuation detection with better context awareness."""
    text = line["text"].lower()
    prev_text = prev_line["text"].lower()
    
    # Check for common continuation patterns
    continuation_patterns = [
        r"^[a-z]",  # Starts with lowercase
        r"^[&]",    # Starts with ampersand
        r"^[;]",    # Starts with semicolon
        r"^[|]",    # Starts with pipe
        r"^[-–]",   # Starts with dash
        r"^[\(]",   # Starts with parenthesis
    ]
    
    # Check for price in previous line but not in current
    prev_has_price = bool(re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?", prev_text))
    curr_has_price = bool(re.search(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?", text))
    
    # Check for common wine term in previous line
    wine_terms = ["wine", "chateau", "domaine", "estate", "vineyard", "cellar"]
    prev_has_wine_term = any(term in prev_text for term in wine_terms)
    
    # Line is probably a continuation if:
    # 1. Matches continuation patterns, or
    # 2. Previous line has price but current doesn't, or
    # 3. Previous line has wine term and current line is short
    return (
        any(re.match(pattern, text) for pattern in continuation_patterns) or
        (prev_has_price and not curr_has_price) or
        (prev_has_wine_term and len(text.split()) <= 3)
    )

def extract_bottle_size(text: str) -> Tuple[str, float]:
    """Extract bottle size and convert to standard ml."""
    text = text.lower()
    size_map = {
        'standard': 750,
        'half': 375,
        'magnum': 1500,
        'double_magnum': 3000,
        'jeroboam': 3000,
        'imperial': 6000,
        'salmanazar': 9000,
        'balthazar': 12000,
        'nebuchadnezzar': 15000
    }
    
    for size_name, pattern in BOTTLE_SIZE_PATTERNS.items():
        if re.search(pattern, text):
            return size_name, size_map[size_name]
    
    return 'standard', 750  # Default to standard size

def extract_variants(text: str) -> List[str]:
    """Extract wine variants from text."""
    variants = []
    for variant_type, pattern in VARIANT_PATTERNS.items():
        if re.search(pattern, text.lower()):
            variants.append(variant_type)
    return variants

def segment_wine_entries(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhanced wine entry segmentation with better multi-line handling and variant detection."""
    entries = []
    current_entry = None
    
    print(f"[DEBUG] Starting segmentation with {len(lines)} lines")
    
    for i, line in enumerate(lines):
        # Skip if line is empty
        if not line["text"].strip():
            continue
        
        # Check if this is a new wine entry
        is_wine = is_probable_wine_line(line)
        if is_wine:
            #print(f"[DEBUG] Found wine line: {line['text']}")
            # Save previous entry if exists
            if current_entry:
                entries.append(current_entry)
            
            # Start new entry
            current_entry = {
                "raw_text": line["text"],
                "lines": [line],
                "section": line.get("section"),
                "sub_section": line.get("sub_section"),
                "sub_sub_section": line.get("sub_sub_section"),
                "bottle_size": extract_bottle_size(line["text"])[0],
                "bottle_size_ml": extract_bottle_size(line["text"])[1],
                "variants": extract_variants(line["text"])
            }
        else:
            print(f"[DEBUG] Skipped line: {line['text']}")
        
        # Check if this is a continuation of current entry
        if current_entry and is_probable_continuation(line, current_entry["lines"][-1]):
            print(f"[DEBUG] Added continuation: {line['text']}")
            current_entry["raw_text"] += " " + line["text"]
            current_entry["lines"].append(line)
    
    # Add final entry if exists
    if current_entry:
        entries.append(current_entry)
    
    print(f"[DEBUG] Finished segmentation with {len(entries)} entries")
    return entries 