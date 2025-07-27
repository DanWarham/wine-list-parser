import re
from typing import Dict, Any, Tuple, Optional

class RegexStrategy:
    def __init__(self):
        self.default_rules = self._load_default_rules()

    def _load_default_rules(self) -> Dict[str, str]:
        # Load default regex rules for LWIN standard fields
        return {
            # Producer patterns - handle both with and without bullet points
            'producer_name': r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-]+?)(?:\s*[-•]|\s+(?:Las|Los|Le|La|Les)\s+[A-Z]|\s+\d{4})',
            'producer_title': r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-]+?(?:Wines?|Vineyards?|Estate|Cellars?|Domaines?))',
            
            # Wine name and vintage
            'wine_name': r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-]+?(?:Las|Los|Le|La|Les)\s+[A-Z][A-Za-z\s\-]+?)(?:\s*[-•]|\s+\d{4})',
            'vintage': r'(?:^|\s|•\s*)((?:(?:19|20)\d{2}|NV))',
            
            # Geographic patterns
            'country': r'(?:^|\s|•\s*)((?:France|Italy|Spain|USA|Australia|Germany|New Zealand|Chile|Argentina|South Africa))',
            'region': r'(?:^|\s|•\s*)((?:Bordeaux|Burgundy|Champagne|Tuscany|Piedmont|Rioja|Napa|Barossa|Mosel|Marlborough|La Palma))',
            'sub_region': r'(?:^|\s|•\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Wine characteristics
            'colour': r'(?:^|\s|•\s*)((?:Red|White|Rosé|Sparkling|Dessert))',
            'type': r'(?:^|\s|•\s*)((?:Wine|Champagne|Port|Sherry|Madeira))',
            'sub_type': r'(?:^|\s|•\s*)((?:Still|Sparkling|Fortified|Ice))',
            
            # Classification
            'designation': r'(?:^|\s|•\s*)((?:AOC|DOC|DOCG|DO|AVA|IGT|VdP))',
            'classification': r'(?:^|\s|•\s*)((?:Grand Cru|Premier Cru|Classé|Riserva|Gran Reserva))',
            
            # Additional fields
            'price': r'(?:^|\s|•\s*)(?:\$|£|€)?(\d+(?:\.\d{2})?)',
            'grape_variety': r'(?:^|\s|•\s*)((?:Chardonnay|Cabernet Sauvignon|Merlot|Pinot Noir|Syrah|Sauvignon Blanc|Riesling|Listan Blanco|Malbec|Grenache|Tempranillo|Nebbiolo|Sangiovese|Zinfandel|Chenin Blanc|Viognier))'
        }

    def extract(self, block: Dict[str, Any], restaurant_rules: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], float]:
        text = block.get('text', '')
        extracted_fields = {}
        total_matches = 0
        
        # Combine default rules with restaurant-specific rules
        rules = self.default_rules.copy()
        if restaurant_rules:
            for field, field_rules in restaurant_rules.items():
                if 'patterns' in field_rules:
                    # Add restaurant-specific patterns
                    for pattern in field_rules['patterns']:
                        if field not in rules:
                            rules[field] = pattern
                        else:
                            # Combine with existing pattern using alternation
                            rules[field] = f"(?:{rules[field]}|{pattern})"
        
        for field, pattern in rules.items():
            match = re.search(pattern, text)
            if match:
                # Clean up the extracted value
                value = match.group(1).strip()
                
                # Check exclusions if restaurant rules exist
                if restaurant_rules and field in restaurant_rules:
                    if 'exclusions' in restaurant_rules[field]:
                        if value in restaurant_rules[field]['exclusions']:
                            continue
                
                if value:
                    extracted_fields[field] = {
                        'value': value,
                        'confidence': 0.8,  # Base confidence for regex matches
                        'provenance': 'regex'
                    }
                    total_matches += 1
        
        # Calculate confidence based on number of matches
        confidence = total_matches / len(rules) if rules else 0.0
        return extracted_fields, confidence
