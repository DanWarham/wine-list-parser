import os
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
from rapidfuzz import fuzz, process
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from app.config import LWIN_XLSX_PATH, BATCH_SIZE
import re

# Fields to normalize for matching
LWIN_KEY_FIELDS = ['producer', 'cuvee', 'vintage', 'region', 'country', 'grape_variety']

# LWIN field mapping to our model fields
LWIN_FIELD_MAPPING = {
    'PRODUCER_NAME': 'producer',
    'WINE': 'cuvee',
    'VINTAGE_CONFIG': 'vintage',
    'REGION': 'region',
    'COUNTRY': 'country',
    'COLOUR': 'type',
    'SUB_TYPE': 'sub_type',
    'DESIGNATION': 'designation',
    'CLASSIFICATION': 'CLASSIFICATION',
    'TYPE': 'type'
}

# Example alias table (expand as needed)
LWIN_ALIAS_TABLE = {
    'producer': {},
    'cuvee': {}
}

# Confidence thresholds
DIRECT_MATCH_THRESHOLD = 100
FUZZY_MATCH_THRESHOLD = 85
PARTIAL_MATCH_THRESHOLD = 70

# Field weights for LWIN matching
LWIN_FIELD_WEIGHTS = {
    'producer': 1.0,  # Most important
    'cuvee': 1.0,     # Most important
    'vintage': 0.8,   # Important but can be NV
    'region': 0.7,    # Important for matching
    'country': 0.7,   # Important for matching
    'grape_variety': 0.6  # Optional
}

@lru_cache(maxsize=1)
def get_lwin_db() -> pd.DataFrame:
    """Load and normalize the LWIN database."""
    try:
        # Load the LWIN database
        lwin_db = pd.read_excel(LWIN_XLSX_PATH)
        lwin_db = lwin_db.copy()
        lwin_db.columns = [col.strip().upper() for col in lwin_db.columns]
        # Precompute normalized columns for fast matching
        for field in LWIN_KEY_FIELDS:
            col = None
            for k, v in LWIN_FIELD_MAPPING.items():
                if v == field:
                    col = k
                    break
            if col and col in lwin_db.columns:
                lwin_db[field + '_norm'] = lwin_db[col].fillna('').astype(str).str.lower().str.strip()
            else:
                lwin_db[field + '_norm'] = ''
        # Create a composite key for faster lookups
        lwin_db['composite_key'] = lwin_db.apply(
            lambda row: ' '.join(str(row.get(col, '')).strip().lower() 
                               for col in LWIN_KEY_FIELDS),
            axis=1
        )
        for col in lwin_db.columns:
            if lwin_db[col].dtype == 'object':
                lwin_db[col] = lwin_db[col].fillna('').astype(str).str.strip()
        return lwin_db
    except Exception as e:
        print(f"Error loading LWIN database: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def normalize_wine_dict(wine: Dict[str, Any]) -> Dict[str, str]:
    """Return a normalized dict of key fields for matching."""
    norm = {f: (str(wine.get(f, '')).lower().strip() if wine.get(f) else '') for f in LWIN_KEY_FIELDS}
    
    # Apply alias table
    for field in ['producer', 'cuvee']:
        if norm[field] in LWIN_ALIAS_TABLE.get(field, {}):
            norm[field] = LWIN_ALIAS_TABLE[field][norm[field]]
    
    # Normalize producer names
    if norm['producer']:
        # Remove common suffixes
        norm['producer'] = re.sub(r'\s+(?:&|and)\s+.*$', '', norm['producer'])
        # Remove common prefixes
        norm['producer'] = re.sub(r'^(?:château|domaine|estate)\s+', '', norm['producer'])
        # Remove common designations
        norm['producer'] = re.sub(r'\s+(?:grand\s+cru|premier\s+cru|1er\s+cru)$', '', norm['producer'])
    
    # Normalize cuvee names
    if norm['cuvee']:
        # Remove quotes
        norm['cuvee'] = re.sub(r'^[\'"]|[\'"]$', '', norm['cuvee'])
        # Remove common designations
        norm['cuvee'] = re.sub(r'\s+(?:grand\s+cru|premier\s+cru|1er\s+cru)$', '', norm['cuvee'])
    
    return norm

def calculate_match_score(wine_norm: Dict[str, str], lwin_row: pd.Series) -> Tuple[float, str]:
    """Calculate match score and provenance between normalized wine dict and LWIN row."""
    scores = []
    matched_fields = []
    total_weight = 0
    
    # Direct matches with weights
    for field in LWIN_KEY_FIELDS:
        if wine_norm[field] and field + '_norm' in lwin_row:
            weight = LWIN_FIELD_WEIGHTS.get(field, 0.5)
            if wine_norm[field] == lwin_row[field + '_norm']:
                scores.append(100 * weight)
                matched_fields.append(field)
                total_weight += weight
    
    # Fuzzy matches for remaining fields with weights
    for field in LWIN_KEY_FIELDS:
        if field not in matched_fields and wine_norm[field] and field + '_norm' in lwin_row:
            weight = LWIN_FIELD_WEIGHTS.get(field, 0.5)
            # Use token sort ratio for better handling of word order
            score = fuzz.token_sort_ratio(wine_norm[field], lwin_row[field + '_norm'])
            
            # Boost score for producer matches
            if field == 'producer' and score > 80:
                score = min(100, score + 10)
            
            # Boost score for cuvee matches
            if field == 'cuvee' and score > 80:
                score = min(100, score + 5)
            
            scores.append(score * weight)
            total_weight += weight
    
    if not scores:
        return 0.0, 'no_match'
    
    # Calculate weighted average
    avg_score = sum(scores) / total_weight if total_weight > 0 else 0.0
    
    # Determine provenance
    if avg_score >= DIRECT_MATCH_THRESHOLD:
        provenance = 'direct'
    elif avg_score >= FUZZY_MATCH_THRESHOLD:
        provenance = 'fuzzy'
    elif avg_score >= PARTIAL_MATCH_THRESHOLD:
        provenance = 'partial'
    else:
        provenance = 'no_match'
    
    return avg_score, provenance

def enrich_wine_entry(wine: Dict[str, Any], lwin_match: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich wine entry with LWIN data, preserving original values if they exist."""
    enriched = wine.copy()
    
    # Map LWIN fields to our model fields
    for lwin_field, our_field in LWIN_FIELD_MAPPING.items():
        if lwin_field in lwin_match and not enriched.get(our_field):
            enriched[our_field] = lwin_match[lwin_field]
            # Set high confidence for LWIN-enriched fields
            if 'field_confidence' not in enriched:
                enriched['field_confidence'] = {}
            enriched['field_confidence'][our_field] = 0.95
    
    # Update field confidence based on match score
    if 'lwin_match_score' in lwin_match:
        match_score = lwin_match['lwin_match_score']
        if 'field_confidence' not in enriched:
            enriched['field_confidence'] = {}
        
        # Update confidence for matched fields
        for field in LWIN_KEY_FIELDS:
            if field in enriched and field in lwin_match:
                enriched['field_confidence'][field] = min(0.95, match_score / 100)
    
    return enriched

def process_batch(batch: List[Dict[str, Any]], lwin_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Process a batch of wine entries for LWIN matching."""
    results = []
    for wine in batch:
        wine_norm = normalize_wine_dict(wine)
        
        # Try direct match first
        query = None
        for field in LWIN_KEY_FIELDS:
            col = field + '_norm'
            val = wine_norm[field]
            if val:
                cond = (lwin_df[col] == val)
                query = cond if query is None else (query & cond)
        
        if query is not None:
            matches = lwin_df[query]
            if not matches.empty:
                match = matches.iloc[0].to_dict()
                match['lwin_match_score'] = 100
                match['lwin_match_provenance'] = 'direct'
                results.append(match)
                continue
        
        # Try fuzzy matching
        best_score = 0
        best_match = None
        best_provenance = 'no_match'
        
        for _, row in lwin_df.iterrows():
            score, provenance = calculate_match_score(wine_norm, row)
            if score > best_score:
                best_score = score
                best_match = row.to_dict()
                best_provenance = provenance
        
        if best_score >= PARTIAL_MATCH_THRESHOLD:
            best_match['lwin_match_score'] = best_score
            best_match['lwin_match_provenance'] = best_provenance
            results.append(best_match)
        else:
            results.append(None)
    
    return results

def match_lwin_batch(wines: List[Dict[str, Any]], batch_size: int = 100) -> List[Dict[str, Any]]:
    """Match a batch of wine entries against the LWIN database (fast vectorized direct, then fuzzy)."""
    try:
        lwin_db = get_lwin_db()
        if lwin_db.empty:
            return wines
        results = []
        for i in range(0, len(wines), batch_size):
            batch = wines[i:i + batch_size]
            # 1. Try vectorized direct match on all normalized fields
            for wine in batch:
                wine_norm = normalize_wine_dict(wine)
                mask = np.ones(len(lwin_db), dtype=bool)
                for field in LWIN_KEY_FIELDS:
                    val = wine_norm[field]
                    if val:
                        mask &= (lwin_db[field + '_norm'] == val)
                direct_matches = lwin_db[mask]
                if not direct_matches.empty:
                    match = direct_matches.iloc[0].to_dict()
                    match['lwin_match_score'] = 100
                    match['lwin_match_provenance'] = 'direct'
                    wine.update(match)
                    wine['lwin_match_score'] = 100
                    # Update field confidence for matched fields
                    if 'field_confidence' not in wine:
                        wine['field_confidence'] = {}
                    for field in LWIN_KEY_FIELDS:
                        if field in wine_norm and wine_norm[field]:
                            wine['field_confidence'][field] = 0.95
                    results.append(wine)
                    continue
                # 2. Fuzzy match only if no direct match
                # Use composite key for RapidFuzz process extraction
                choices = lwin_db['composite_key'].tolist()
                query = ' '.join([wine_norm[f] for f in LWIN_KEY_FIELDS])
                best = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
                if best and best[1] >= PARTIAL_MATCH_THRESHOLD:
                    idx = best[2]
                    match = lwin_db.iloc[idx].to_dict()
                    match['lwin_match_score'] = best[1]
                    match['lwin_match_provenance'] = 'fuzzy'
                    wine.update(match)
                    wine['lwin_match_score'] = best[1]
                    # Update field confidence for matched fields based on match score
                    if 'field_confidence' not in wine:
                        wine['field_confidence'] = {}
                    for field in LWIN_KEY_FIELDS:
                        if field in wine_norm and wine_norm[field]:
                            wine['field_confidence'][field] = min(0.95, best[1] / 100)
                    results.append(wine)
                else:
                    results.append(wine)
        return results
    except Exception as e:
        print(f"Error in batch LWIN matching: {str(e)}")
        return wines

def match_lwin(wine: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    """Match a wine entry against the LWIN database."""
    try:
        # Get normalized wine data
        normalized = normalize_wine_dict(wine)
        
        # Get LWIN database
        lwin_db = get_lwin_db()
        if lwin_db.empty:
            return wine, 0.0
            
        # Create composite key for matching
        composite_key = ' '.join(str(normalized.get(field, '')).strip().lower() 
                               for field in LWIN_KEY_FIELDS)
        
        # Try direct match first
        matches = lwin_db[lwin_db['composite_key'] == composite_key]
        if not matches.empty:
            best_match = matches.iloc[0]
            return enrich_wine_entry(wine, best_match), 1.0
            
        # Try fuzzy matching if no direct match
        best_score = 0.0
        best_match = None
        
        for _, row in lwin_db.iterrows():
            score = calculate_match_score(normalized, row)
            if score > best_score:
                best_score = score
                best_match = row
                
        if best_score >= FUZZY_MATCH_THRESHOLD and best_match is not None:
            return enrich_wine_entry(wine, best_match), best_score
            
        return wine, 0.0
        
    except Exception as e:
        print(f"Error in LWIN matching: {str(e)}")
        return wine, 0.0

def get_lwin_suggestions(wine: Dict[str, Any], lwin_df: Optional[pd.DataFrame] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Get a list of potential LWIN matches for a wine entry."""
    if lwin_df is None:
        lwin_df = get_lwin_db()
    
    wine_norm = normalize_wine_dict(wine)
    suggestions = []
    
    for _, row in lwin_df.iterrows():
        score, provenance = calculate_match_score(wine_norm, row)
        if score >= PARTIAL_MATCH_THRESHOLD:
            match = row.to_dict()
            match['lwin_match_score'] = score
            match['lwin_match_provenance'] = provenance
            suggestions.append(match)
    
    # Sort by score and limit results
    suggestions.sort(key=lambda x: x['lwin_match_score'], reverse=True)
    return suggestions[:limit]

def update_lwin_alias_table(correction: Dict[str, str]) -> None:
    """Update the LWIN alias table with a user correction."""
    for field in ['producer', 'cuvee']:
        if field in correction and field in LWIN_ALIAS_TABLE:
            original = correction[field].lower().strip()
            corrected = correction.get(f'corrected_{field}', '').lower().strip()
            if original and corrected:
                LWIN_ALIAS_TABLE[field][original] = corrected 