from typing import List, Dict, Any, Tuple, Optional
from app.rules import apply_rules
from app.preprocessing import normalize_text
from app.lwin import (
    match_lwin_batch,
    get_lwin_db,
    enrich_wine_entry as lwin_enrich_wine_entry,
    get_lwin_suggestions,
    LWIN_KEY_FIELDS,
    LWIN_FIELD_MAPPING
)
from app.ai_parsing import parse_wine_entries
import re
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Enhanced global rules focused on accurate full-string parsing
GLOBAL_RULES = [
    # Full wine entry patterns (high confidence)
    {
        'pattern': r'(?P<grape_variety>[A-Z][a-zA-Z\s\'-]+(?:\s*/\s*[A-Z][a-zA-Z\s\'-]+)*)\s+(?:\'(?P<cuvee>[^\']+)\'|"(?P<cuvee2>[^"]+)"|(?P<cuvee3>[A-Z][a-zA-Z\s\'-]+))\s*,\s*(?P<producer>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*(?:\s*&\s*[A-Z][a-zA-Z\s\'-]+)*)\s*,\s*(?P<region>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*)\s+(?P<vintage>19\d{2}|20\d{2}|NV)\s+(?P<price>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?)',
        'confidence': 0.95
    },
    {
        'pattern': r'(?P<producer>Château|Domaine|Estate)\s+(?P<cuvee>[A-Z][a-zA-Z\s\'-]+)\s+(?P<region>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*)\s+(?P<vintage>19\d{2}|20\d{2}|NV)\s+(?P<price>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?)',
        'confidence': 0.95
    },
    
    # Common wine patterns (medium confidence)
    {
        'pattern': r'(?P<grape_variety>[A-Z][a-zA-Z\s\'-]+(?:\s*/\s*[A-Z][a-zA-Z\s\'-]+)*)\s+(?:\'(?P<cuvee>[^\']+)\'|"(?P<cuvee2>[^"]+)"|(?P<cuvee3>[A-Z][a-zA-Z\s\'-]+))\s*,\s*(?P<producer>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*(?:\s*&\s*[A-Z][a-zA-Z\s\'-]+)*)\s*,\s*(?P<region>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*)\s+(?P<price>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?)',
        'confidence': 0.85
    },
    {
        'pattern': r'(?P<producer>Château|Domaine|Estate)\s+(?P<cuvee>[A-Z][a-zA-Z\s\'-]+)\s+(?P<region>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*)\s+(?P<price>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?)',
        'confidence': 0.85
    },
    
    # Additional field patterns (lower confidence, used for enrichment)
    {'field': 'vintage', 'pattern': r'(?P<vintage>19\d{2}|20\d{2}|NV|N\.V\.|Non-Vintage)', 'confidence': 0.8},
    {'field': 'price', 'pattern': r'(?P<price>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?|POA)', 'confidence': 0.8},
    {'field': 'bottle_size', 'pattern': r'(?P<bottle_size>\b(750ml|magnum|jeroboam|half|1\.5L|3L|375ml|cl)\b)', 'confidence': 0.7},
    {'field': 'designation', 'pattern': r'(?P<designation>Grand Cru|Premier Cru|1er Cru|Riserva|Reserva|Gran Reserva)', 'confidence': 0.7},
    {'field': 'classification', 'pattern': r'(?P<classification>AOC|DOCG|DOC|IGT|VDP|VDQS|AVA|VQA|GI)', 'confidence': 0.7},
    {'field': 'sub_type', 'pattern': r'(?P<sub_type>Brut|Sec|Demi-Sec|Extra Brut|Rosé|Blanc de Blancs)', 'confidence': 0.7},
    {'field': 'grape_variety', 'pattern': r'(?P<grape_variety>Pinot Noir|Chardonnay|Pinot Meunier|Cabernet Sauvignon|Merlot|Syrah|Grenache)(?:\s*/\s*(?:Pinot Noir|Chardonnay|Pinot Meunier|Cabernet Sauvignon|Merlot|Syrah|Grenache))*', 'confidence': 0.8},
    
    # Producer and cuvee specific patterns
    {'field': 'producer', 'pattern': r'(?P<producer>[A-Z][a-zA-Z\s\'-]+(?:\s+[A-Z][a-zA-Z\s\'-]+)*(?:\s*&\s*[A-Z][a-zA-Z\s\'-]+)*)(?=\s*,\s*[A-Z][a-zA-Z\s\'-]+)', 'confidence': 0.8},
    {'field': 'cuvee', 'pattern': r'(?:\'(?P<cuvee>[^\']+)\'|"(?P<cuvee2>[^"]+)"|(?P<cuvee3>[A-Z][a-zA-Z\s\'-]+))(?=\s*,\s*[A-Z][a-zA-Z\s\'-]+)', 'confidence': 0.8},
]

# Required fields for WineEntry with weights
REQUIRED_FIELDS = {
    'producer': 1.0,  # Most important
    'cuvee': 1.0,     # Most important
    'type': 0.8,      # Important but can be inferred
    'vintage': 0.8,   # Important but can be NV
    'price': 0.9,     # Very important
    'bottle_size': 0.7,  # Can be inferred
    'grape_variety': 0.6,  # Optional
    'country': 0.7,   # Can be inferred
    'region': 0.6,    # Optional
    'subregion': 0.5,  # Optional
    'designation': 0.5,  # Optional
    'classification': 0.5,  # Optional
    'sub_type': 0.5   # Optional
}

def validate_field(field: str, value: Any) -> Tuple[bool, float]:
    """Validate a field value and return (is_valid, confidence)."""
    if not value:
        return False, 0.0
    
    validation_rules = {
        'vintage': lambda x: bool(re.match(r'^(19|20)\d{2}$|^NV$|^N\.V\.$', str(x))),
        'price': lambda x: bool(re.match(r'^\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?$|^POA$', str(x))),
        'bottle_size': lambda x: bool(re.match(r'^\d+(?:\.\d+)?(?:ml|cl|L)$|^magnum$|^jeroboam$|^half$', str(x))),
        'country': lambda x: len(str(x)) >= 2 and len(str(x)) <= 50,
        'region': lambda x: len(str(x)) >= 2 and len(str(x)) <= 100,
        'producer': lambda x: len(str(x)) >= 2 and len(str(x)) <= 100 and not any(kw in str(x).lower() for kw in ['cru', 'grand', 'premier', '1er']),
        'cuvee': lambda x: len(str(x)) >= 1 and len(str(x)) <= 100,
    }
    
    if field in validation_rules:
        is_valid = validation_rules[field](value)
        return is_valid, 0.9 if is_valid else 0.3
    
    return True, 0.7  # Default validation for other fields

def calculate_field_confidence(field: str, value: Any, provenance: str, base_confidence: float) -> float:
    """Calculate confidence score for a field based on multiple factors."""
    # Base confidence from rule or source
    confidence = base_confidence
    
    # Adjust based on provenance
    provenance_multipliers = {
        'restaurant_rule': 1.0,
        'global_rule': 0.9,
        'lwin_match': 0.95,
        'lwin_enrichment': 0.85,
        'context': 0.7,
        'context_propagation': 0.6,
        'missing': 0.2
    }
    confidence *= provenance_multipliers.get(provenance, 0.5)
    
    # Validate field
    is_valid, validation_confidence = validate_field(field, value)
    if not is_valid:
        confidence *= 0.5
    
    # Additional field-specific adjustments
    if field == 'vintage' and str(value).upper() in ['NV', 'N.V.']:
        confidence *= 0.9  # Slightly lower confidence for non-vintage
    
    if field == 'price' and str(value).upper() == 'POA':
        confidence *= 0.8  # Lower confidence for POA
    
    # Apply field weight
    field_weight = REQUIRED_FIELDS.get(field, 0.5)
    confidence *= field_weight
    
    return min(confidence, 1.0)  # Cap at 1.0

def calculate_row_confidence(extracted: Dict[str, Any], field_confidence: Dict[str, float]) -> float:
    """Calculate overall row confidence based on field weights and confidences."""
    total_weight = 0
    weighted_sum = 0
    
    for field, weight in REQUIRED_FIELDS.items():
        if field in field_confidence:
            total_weight += weight
            weighted_sum += field_confidence[field] * weight
    
    # If no fields were found, return 0
    if total_weight == 0:
        return 0.0
    
    # Calculate weighted average
    return weighted_sum / total_weight

def extract_fields_for_entries(entries: List[Dict[str, Any]], ruleset: Dict[str, Any], global_rules: List[Dict[str, Any]] = GLOBAL_RULES) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract fields with focus on accurate full-string parsing."""
    logger.info(f"Starting extract_fields_for_entries with {len(entries)} entries")
    results = []
    per_restaurant_rules = ruleset.get('extraction_rules', []) if ruleset else []
    
    # First pass: extract fields using full-string patterns
    extracted_entries = []
    for idx, entry in enumerate(entries):
        try:
            raw_text = normalize_text(entry['raw_text'])
            extracted = {}
            field_confidence = {}
            provenance = {}
            
            logger.info(f"Processing entry {idx+1}:")
            logger.info(f"  Raw text: {raw_text}")
            
            # 1. Try restaurant-specific rules first
            if per_restaurant_rules:
                logger.info("  Applying restaurant-specific rules")
                for rule in per_restaurant_rules:
                    match = re.search(rule['pattern'], raw_text)
                    if match:
                        logger.info(f"  Found restaurant rule match with pattern: {rule['pattern']}")
                        for field in rule['fields']:
                            if field in match.groupdict() and match.group(field):
                                extracted[field] = match.group(field)
                                field_confidence[field] = calculate_field_confidence(
                                    field, match.group(field), rule.get('provenance', 'restaurant_rule'), rule['confidence']
                                )
                                provenance[field] = rule.get('provenance', 'restaurant_rule')
                                logger.info(f"    Extracted {field}: {match.group(field)} (confidence: {field_confidence[field]})")
            
            # 2. Try global rules for remaining fields
            for rule in global_rules:
                if 'pattern' in rule and 'field' not in rule:  # Full-string pattern
                    match = re.search(rule['pattern'], raw_text)
                    if match:
                        logger.info(f"  Found global rule match with pattern: {rule['pattern']}")
                        for field, value in match.groupdict().items():
                            if value and (field not in extracted or field_confidence.get(field, 0) < rule['confidence']):
                                # Handle cuvee fields (cuvee, cuvee2, cuvee3)
                                if field.startswith('cuvee'):
                                    if 'cuvee' not in extracted or field_confidence.get('cuvee', 0) < rule['confidence']:
                                        extracted['cuvee'] = value
                                        field_confidence['cuvee'] = calculate_field_confidence(
                                            'cuvee', value, 'global_rule', rule['confidence']
                                        )
                                        provenance['cuvee'] = 'global_rule'
                                        logger.info(f"    Extracted cuvee: {value} (confidence: {field_confidence['cuvee']})")
                                else:
                                    extracted[field] = value
                                    field_confidence[field] = calculate_field_confidence(
                                        field, value, 'global_rule', rule['confidence']
                                    )
                                    provenance[field] = 'global_rule'
                                    logger.info(f"    Extracted {field}: {value} (confidence: {field_confidence[field]})")
            
            # 3. Apply additional field patterns for enrichment
            for rule in global_rules:
                if 'field' in rule:  # Field-specific pattern
                    field = rule['field']
                    if field not in extracted or field_confidence.get(field, 0) < rule['confidence']:
                        match = re.search(rule['pattern'], raw_text)
                        if match and match.group(field):
                            extracted[field] = match.group(field)
                            field_confidence[field] = calculate_field_confidence(
                                field, match.group(field), 'field_pattern_match', rule['confidence']
                            )
                            provenance[field] = 'field_pattern_match'
                            logger.info(f"    Field pattern extracted {field}: {match.group(field)} (confidence: {field_confidence[field]})")
            
            # 4. Inherit values from section context if missing
            if entry.get('section_header'):
                for field in ['region', 'country', 'type']:
                    if field not in extracted or field_confidence.get(field, 0) < 0.7:
                        value = entry['section_header']
                        extracted[field] = value
                        field_confidence[field] = 0.7
                        provenance[field] = 'section_inherit'
                        logger.info(f"    Inherited {field} from section: {value}")
            
            if entry.get('sub_section'):
                for field in ['subregion', 'grape_variety']:
                    if field not in extracted or field_confidence.get(field, 0) < 0.7:
                        value = entry['sub_section']
                        extracted[field] = value
                        field_confidence[field] = 0.7
                        provenance[field] = 'subsection_inherit'
                        logger.info(f"    Inherited {field} from subsection: {value}")
            
            # Calculate overall confidence using weighted average
            row_confidence = calculate_row_confidence(extracted, field_confidence)
            logger.info(f"  Final row confidence: {row_confidence}")
            
            # Store extracted entry
            extracted_entries.append({
                'entry': entry,
                'extracted': extracted,
                'field_confidence': field_confidence,
                'provenance': provenance,
                'raw_text': raw_text,
                'row_confidence': row_confidence,
                'needs_review': row_confidence < 0.75  # Adjusted threshold
            })
            
            if idx % 10 == 0:
                logger.info(f"Processed {idx+1}/{len(entries)} entries")
        except Exception as e:
            logger.error(f"Exception processing entry {idx}: {str(e)}")
    
    # Convert to final results format
    results = [{
        **e['extracted'],
        'section_header': e['entry'].get('section'),
        'subheader': e['entry'].get('sub_section'),
        'sub_subheader': e['entry'].get('sub_sub_section'),
        'raw_text': e['entry']['raw_text'],
        'field_confidence': e['field_confidence'],
        'provenance': e['provenance'],
        'row_confidence': e['row_confidence'],
        'needs_review': e['needs_review']
    } for e in extracted_entries]
    
    logger.info(f"Finished extract_fields_for_entries, processed {len(results)} entries")
    return results, extracted_entries

def get_low_confidence_samples(entries: List[Dict[str, Any]], count: int = 10) -> List[Dict[str, Any]]:
    """Get a sample of low confidence entries for rule generation."""
    # Sort by confidence and get the lowest ones
    low_confidence = sorted(entries, key=lambda x: x['row_confidence'])[:count]
    return low_confidence

def generate_initial_rules(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate initial restaurant rules from low confidence samples using LWIN and AI."""
    logger.info("Starting initial rule generation from samples")
    ruleset = {
        'extraction_rules': [],
        'header_patterns': {},
        'exclusion_patterns': [],
        'aliases': {},
        'merging_strategies': []
    }
    
    try:
        # Get LWIN matches for samples
        lwin_matches = match_lwin_batch([s['extracted'] for s in samples])
        
        # Analyze patterns from samples and LWIN matches
        for sample, lwin_match in zip(samples, lwin_matches):
            if not lwin_match:
                continue
                
            raw_text = sample['raw_text']
            extracted = sample['extracted']
            
            # Generate rules based on LWIN matches
            if lwin_match.get('lwin_match_score', 0) >= 85:  # High confidence match
                # Create producer-cuvee pattern
                producer = lwin_match.get('PRODUCER_NAME', '')
                cuvee = lwin_match.get('WINE', '')
                if producer and cuvee:
                    # Create exact match pattern
                    pattern = f"(?P<producer>{re.escape(producer)})\\s+(?P<cuvee>{re.escape(cuvee)})"
                    ruleset['extraction_rules'].append({
                        'pattern': pattern,
                        'confidence': 0.95,
                        'fields': ['producer', 'cuvee'],
                        'provenance': 'lwin_match'
                    })
                    
                    # Create fuzzy match pattern for variations
                    fuzzy_pattern = f"(?P<producer>{re.escape(producer)})(?:\\s+[A-Za-z]+)*\\s+(?P<cuvee>{re.escape(cuvee)})"
                    ruleset['extraction_rules'].append({
                        'pattern': fuzzy_pattern,
                        'confidence': 0.85,
                        'fields': ['producer', 'cuvee'],
                        'provenance': 'lwin_fuzzy'
                    })
                
                # Add to aliases
                if producer:
                    ruleset['aliases']['producer'] = ruleset['aliases'].get('producer', {})
                    ruleset['aliases']['producer'][producer.lower()] = producer
                if cuvee:
                    ruleset['aliases']['cuvee'] = ruleset['aliases'].get('cuvee', {})
                    ruleset['aliases']['cuvee'][cuvee.lower()] = cuvee
            
            # Generate price pattern if present
            price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€$£]?)', raw_text)
            if price_match:
                price_pattern = f"(?P<price>{re.escape(price_match.group(1))})"
                ruleset['extraction_rules'].append({
                    'pattern': price_pattern,
                    'confidence': 0.9,
                    'fields': ['price'],
                    'provenance': 'pattern_match'
                })
            
            # Generate vintage pattern if present
            vintage_match = re.search(r'(19\d{2}|20\d{2}|NV|N\.V\.)', raw_text)
            if vintage_match:
                vintage_pattern = f"(?P<vintage>{re.escape(vintage_match.group(1))})"
                ruleset['extraction_rules'].append({
                    'pattern': vintage_pattern,
                    'confidence': 0.9,
                    'fields': ['vintage'],
                    'provenance': 'pattern_match'
                })
            
            # Add section patterns if present
            if sample.get('section_header'):
                ruleset['header_patterns']['main'] = ruleset['header_patterns'].get('main', [])
                ruleset['header_patterns']['main'].append({
                    'pattern': sample['section_header'],
                    'confidence': 0.9,
                    'provenance': 'section_match'
                })
            if sample.get('subheader'):
                ruleset['header_patterns']['sub'] = ruleset['header_patterns'].get('sub', [])
                ruleset['header_patterns']['sub'].append({
                    'pattern': sample['subheader'],
                    'confidence': 0.9,
                    'provenance': 'section_match'
                })
            
            # Add merging strategies based on line patterns
            if len(sample.get('lines', [])) > 1:
                merging_strategy = {
                    'pattern': raw_text,
                    'confidence': 0.8,
                    'provenance': 'sample_merge'
                }
                ruleset['merging_strategies'].append(merging_strategy)
        
        # Add common exclusion patterns
        ruleset['exclusion_patterns'] = [
            {'pattern': r'by\s+the\s+glass', 'confidence': 0.9},
            {'pattern': r'wine\s+pairing', 'confidence': 0.9},
            {'pattern': r'flight', 'confidence': 0.9},
            {'pattern': r'tasting\s+menu', 'confidence': 0.9}
        ]
        
        logger.info(f"Generated {len(ruleset['extraction_rules'])} initial rules")
        logger.info(f"Generated {len(ruleset['merging_strategies'])} merging strategies")
        return ruleset
        
    except Exception as e:
        logger.error(f"Exception during rule generation: {str(e)}")
        return ruleset

def parse_wine_list(entries: List[Dict[str, Any]], restaurant_rules: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parse wine list with the new multi-stage pipeline:
    1. If restaurant rules exist, parse with them and show refinement.
    2. If no rules:
       - Parse with global rules only (no LWIN/AI)
       - Select a small sample (low-confidence + a few high-confidence)
       - Enrich only this sample with LWIN/AI
       - Generate initial restaurant rules from enriched sample
       - Re-parse all entries with new rules
       - Return all relevant data for refinement
    """
    logger.info("\n===== Starting Wine List Parsing (Multi-Stage) =====")
    logger.info(f"Input entries count: {len(entries)}")

    # 1. If restaurant rules exist, use them directly
    if restaurant_rules and restaurant_rules.get('extraction_rules'):
        logger.info("\nUsing existing restaurant rules")
        results, _ = extract_fields_for_entries(entries, restaurant_rules, GLOBAL_RULES)
        needs_review = [r for r in results if r['needs_review']]
        return results, {
            'final_parse': results,
            'needs_review': needs_review,
            'restaurant_rules': restaurant_rules,
            'stage': 'rules_exist',
        }

    logger.info("\nNo existing restaurant rules found, starting new multi-stage pipeline")

    # 2. Initial parse with global rules only (no LWIN/AI)
    logger.info("\n==== Step 1: Initial Parse with Global Rules (no LWIN/AI) ===")
    initial_results, initial_intermediate = extract_fields_for_entries(entries, None, GLOBAL_RULES)
    logger.info(f"Initial parse completed with {len(initial_results)} entries")

    # 3. Select a sample for enrichment (low-confidence + a few high-confidence)
    logger.info("\n==== Step 2: Selecting Sample for LWIN/AI Enrichment ===")
    sorted_intermediate = sorted(initial_intermediate, key=lambda x: x['row_confidence'])
    sample_size = min(10, len(sorted_intermediate))
    low_confidence = sorted_intermediate[:max(5, sample_size // 2)]
    high_confidence = sorted_intermediate[-max(2, sample_size // 4):] if sample_size > 6 else []
    sample = low_confidence + high_confidence
    logger.info(f"Selected {len(sample)} samples for enrichment (LWIN/AI)")

    # 4. Enrich only the sample with LWIN/AI
    logger.info("\n==== Step 3: LWIN/AI Enrichment of Sample ===")
    lwin_matches = match_lwin_batch([s['extracted'] for s in sample])
    ai_processed_samples = parse_wine_entries(sample)
    enriched_sample = []
    for orig, lwin, ai in zip(sample, lwin_matches, ai_processed_samples):
        enriched = orig.copy()
        # Prefer LWIN match if high confidence
        if lwin and lwin.get('lwin_match_score', 0) >= 85:
            enriched = lwin_enrich_wine_entry(enriched, lwin)
            enriched['lwin_match_info'] = lwin
            enriched['lwin_confidence'] = lwin.get('lwin_match_score', 0) / 100.0
            enriched['lwin_number'] = lwin.get('LWIN', None)
        # Otherwise, use AI fields if present
        elif ai:
            for field, value in ai.items():
                if field != 'field_confidence' and value is not None:
                    enriched[field] = value
            if 'field_confidence' in ai:
                if 'field_confidence' not in enriched:
                    enriched['field_confidence'] = {}
                enriched['field_confidence'].update(ai['field_confidence'])
            enriched['ai_used'] = True
        enriched_sample.append(enriched)
    logger.info(f"Enriched sample size: {len(enriched_sample)}")

    # 5. Generate initial restaurant rules from enriched sample
    logger.info("\n==== Step 4: Generating Initial Restaurant Rules from Enriched Sample ===")
    restaurant_rules = generate_initial_rules(sample)
    logger.info(f"Generated {len(restaurant_rules.get('extraction_rules', []))} initial rules")

    # 6. Re-parse all entries with new rules
    logger.info("\n==== Step 5: Parsing All Entries with New Restaurant Rules ===")
    final_results, _ = extract_fields_for_entries(entries, restaurant_rules, GLOBAL_RULES)
    needs_review = [r for r in final_results if r['needs_review']]
    logger.info(f"Final parse completed. Entries needing review: {len(needs_review)}")
    
    # 7. Return all relevant data for refinement
    refinement_data = {
        'initial_parse': initial_results,
        'enriched_sample': enriched_sample,
        'restaurant_rules': restaurant_rules,
        'final_parse': final_results,
        'needs_review': needs_review,
        'stage': 'multi_stage',
    }
    logger.info("\n===== Multi-Stage Wine List Parsing Complete =====")
    return final_results, refinement_data

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
