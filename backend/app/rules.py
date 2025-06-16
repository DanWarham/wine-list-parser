import re
from typing import Dict, Any, List

def apply_rules(rules: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
    """
    Apply a list of regex rules to the text. Each rule is a dict with:
      - 'field': field name to extract
      - 'pattern': regex pattern (with named group if possible)
      - 'confidence': confidence score for this rule
    Returns a dict of {field: (value, confidence)}
    """
    results = {}
    for rule in rules:
        field = rule['field']
        pattern = rule['pattern']
        confidence = rule.get('confidence', 0.8)
        match = re.search(pattern, text)
        if match:
            value = match.group(field) if field in match.groupdict() else match.group(0)
            results[field] = {'value': value.strip(), 'confidence': confidence, 'provenance': 'regex'}
    return results
