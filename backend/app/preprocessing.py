import re
import unicodedata
from typing import List, Dict, Any, Tuple

def normalize_text(text: str) -> str:
    """Enhanced text normalization with better hyphen repair and unicode handling."""
    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)
    
    # Normalize various types of hyphens and dashes
    text = re.sub(r"[\u2010-\u2015\u2043\u2212\u23AF\u23E4]", "-", text)
    
    # Fix common hyphenation patterns
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)  # Fix line-break hyphens
    text = re.sub(r"(\w+)-\s*(\w+)", r"\1\2", text)  # Fix regular hyphens between words
    
    # Fix common producer name patterns
    text = re.sub(r"(\w+)(?:&|and)\s*(\w+)", r"\1 & \2", text)  # Normalize & and and
    text = re.sub(r"(\w+)(?:'|')\s*(\w+)", r"\1'\2", text)  # Normalize apostrophes
    
    # Fix common wine list formatting
    text = re.sub(r"(\d+)\s*€", r"\1€", text)  # Fix space before €
    text = re.sub(r"(\d+)\s*\$", r"\1$", text)  # Fix space before $
    text = re.sub(r"(\d+)\s*£", r"\1£", text)  # Fix space before £
    
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_contents_page(page: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, int]]:
    """Detect if a page is a contents/index page and extract page numbers."""
    contents_keywords = ["contents", "index", "table of contents", "wine list", "sommelier's selection"]
    page_mapping = {}
    
    # Check if page contains contents keywords
    page_text = " ".join([line["text"].lower() for line in page])
    if not any(kw in page_text for kw in contents_keywords):
        return False, page_mapping
    
    # Look for page number patterns
    for line in page:
        text = line["text"]
        # Match patterns like "Section Name .......... 12" or "Section Name - 12"
        match = re.search(r"(.+?)(?:\.+\s*|\s*-\s*|\s*\.\s*)(\d+)$", text)
        if match:
            section = match.group(1).strip()
            page_num = int(match.group(2))
            page_mapping[section] = page_num
    
    return len(page_mapping) > 0, page_mapping

def is_non_content_page(page: List[Dict[str, Any]]) -> bool:
    """Enhanced non-content page detection."""
    non_content_keywords = [
        "table of contents", "notes", "about", "introduction", "summary",
        "terms and conditions", "disclaimer", "copyright", "all rights reserved",
        "page", "of", "wine list", "menu", "sommelier's selection"
    ]
    
    # Check page length
    if len(page) < 2:
        return True
    
    # Check for non-content patterns
    page_text = " ".join([line["text"].lower() for line in page])
    
    # Check for common non-content patterns
    if any(kw in page_text for kw in non_content_keywords):
        return True
    
    # Check for page numbers only
    if all(re.match(r"^\d+$", line["text"].strip()) for line in page):
        return True
    
    # Check for very short lines
    if all(len(line["text"].strip()) < 10 for line in page):
        return True
    
    return False

def preprocess_extraction(pages: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Enhanced preprocessing with contents page detection and better text normalization."""
    processed_pages = []
    contents_page_mapping = {}
    
    # First pass: detect contents page and build mapping
    for page_num, page in enumerate(pages):
        is_contents, page_mapping = is_contents_page(page)
        if is_contents:
            contents_page_mapping.update(page_mapping)
            continue  # Skip contents page in output
    
    # Second pass: process pages
    for page_num, page in enumerate(pages):
        # Skip non-content pages
        if is_non_content_page(page):
            continue
        
        processed_page = []
        for line in page:
            # Normalize text
            line["text"] = normalize_text(line["text"])
            
            # Skip empty lines
            if not line["text"]:
                continue
            
            # Add page number from contents mapping if available
            if contents_page_mapping:
                line["contents_page"] = page_num + 1
            
            processed_page.append(line)
        
        if processed_page:  # Only add non-empty pages
            processed_pages.append(processed_page)
    
    return processed_pages

def detect_sections(pages: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Enhanced section detection with multi-level support and better pattern matching."""
    section = None
    sub_section = None
    sub_sub_section = None  # For three-level hierarchy
    output = []
    
    # Enhanced header patterns
    header_patterns = {
        'main': [
            r"^[A-Z][A-Z\s]{2,30}$",  # All caps, 2-30 chars
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$",  # Title Case
            r"^(?:Red|White|Sparkling|Rosé|Dessert|Sweet|Fortified)\s+Wines?$",
            r"^(?:Champagne|Sparkling|Still|Fortified)\s+Wines?$"
        ],
        'sub': [
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$",  # Title Case
            r"^(?:Champagne|Burgundy|Bordeaux|Italy|Spain|USA|Australia|Germany|New Zealand)$",
            r"^(?:Pinot Noir|Chardonnay|Cabernet|Merlot|Syrah|Grenache)\s+Wines?$"
        ],
        'sub_sub': [
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$",  # Title Case
            r"^(?:Pinot Noir|Chardonnay|Cabernet|Merlot|Syrah|Grenache)$",
            r"^(?:Grand Cru|Premier Cru|1er Cru|Riserva|Reserva|Gran Reserva)$"
        ]
    }
    
    # Known section keywords
    header_keywords = {
        'main': ["champagne", "rosé", "magnums", "white", "red", "sparkling", "dessert", "sweet", "fortified"],
        'sub': ["burgundy", "bordeaux", "italy", "spain", "usa", "australia", "germany", "new zealand", "champagne"],
        'sub_sub': ["pinot noir", "chardonnay", "cabernet", "merlot", "syrah", "grenache", "grand cru", "premier cru", "1er cru"]
    }
    
    for page in pages:
        for line in page:
            text = line["text"]
            is_header = False
            is_subheader = False
            is_sub_subheader = False
            
            # Check for main section
            if any(re.match(pattern, text) for pattern in header_patterns['main']) or \
               any(kw in text.lower() for kw in header_keywords['main']):
                section = text
                sub_section = None
                sub_sub_section = None
                is_header = True
            
            # Check for sub-section
            elif any(re.match(pattern, text) for pattern in header_patterns['sub']) or \
                 any(kw in text.lower() for kw in header_keywords['sub']):
                sub_section = text
                sub_sub_section = None
                is_subheader = True
            
            # Check for sub-sub-section
            elif any(re.match(pattern, text) for pattern in header_patterns['sub_sub']) or \
                 any(kw in text.lower() for kw in header_keywords['sub_sub']):
                sub_sub_section = text
                is_sub_subheader = True
            
            # Update line with section context
            line.update({
                "is_header": is_header,
                "is_subheader": is_subheader,
                "is_sub_subheader": is_sub_subheader,
                "section": section,
                "sub_section": sub_section,
                "sub_sub_section": sub_sub_section
            })
            
            output.append(line)
    
    return output
