import re
from typing import Dict, Any, Tuple, Optional

class RegexStrategy:
    def __init__(self):
        self.default_rules = self._load_default_rules()

    def _load_default_rules(self) -> Dict[str, str]:
        # Load default regex rules for LWIN standard fields with enhanced bullet point support
        return {
            # Enhanced producer patterns - handle bullet points and complex formatting
            'producer_name': [
                r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+(?:Las|Los|Le|La|Les)\s+[A-Z]|\s+\d{4})',
                r'•\s*([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})',
                r'([A-Z][A-Za-z\s\-&\.]+?)\s*•\s*[A-Z]',
                r'^([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})',
                r'(?:^|\s)([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})'
            ],
            'producer_title': [
                r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-&\.]+?(?:Wines?|Vineyards?|Estate|Cellars?|Domaines?))',
                r'•\s*([A-Z][A-Za-z\s\-&\.]+?(?:Wines?|Vineyards?|Estate|Cellars?|Domaines?))'
            ],
            
            # Enhanced wine name patterns
            'wine_name': [
                r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-&\.]+?(?:Las|Los|Le|La|Les)\s+[A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})',
                r'•\s*([A-Z][A-Za-z\s\-&\.]+?(?:Las|Los|Le|La|Les)\s+[A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})',
                r'([A-Z][A-Za-z\s\-&\.]+?(?:Las|Los|Le|La|Les)\s+[A-Z][A-Za-z\s\-&\.]+?)\s*•\s*[A-Z]',
                r'•\s*([A-Z][A-Za-z\s\-&\.]+?)\s*[-•]\s*[A-Z]',
                r'(?:^|\s)([A-Z][A-Za-z\s\-&\.]+?)\s*[-•]\s*[A-Z]'
            ],
            
            # Enhanced vintage patterns with bullet point support
            'vintage': [
                r'(?:^|\s|•\s*)((?:(?:19|20)\d{2}|NV))\s*•',
                r'•\s*((?:(?:19|20)\d{2}|NV))',
                r'((?:(?:19|20)\d{2}|NV))\s*[-•]',
                r'(?:^|\s)((?:(?:19|20)\d{2}|NV))\s*[-•]',
                r'•\s*((?:(?:19|20)\d{2}|NV))\s*[-•]'
            ],
            
            # Enhanced geographic patterns
            'country': [
                r'(?:^|\s|•\s*)((?:France|Italy|Spain|USA|Australia|Germany|New Zealand|Chile|Argentina|South Africa))',
                r'•\s*((?:France|Italy|Spain|USA|Australia|Germany|New Zealand|Chile|Argentina|South Africa))'
            ],
            'region': [
                r'(?:^|\s|•\s*)((?:Bordeaux|Burgundy|Champagne|Tuscany|Piedmont|Rioja|Napa|Barossa|Mosel|Marlborough|La Palma|Jura|Loire|Anjou|Savennières|Muscadet|Côtes|Arbois))',
                r'•\s*((?:Bordeaux|Burgundy|Champagne|Tuscany|Piedmont|Rioja|Napa|Barossa|Mosel|Marlborough|La Palma|Jura|Loire|Anjou|Savennières|Muscadet|Côtes|Arbois))'
            ],
            'sub_region': [
                r'(?:^|\s|•\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'•\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-•]'
            ],
            
            # Enhanced wine characteristics with bullet point support
            'colour': [
                r'(?:^|\s|•\s*)((?:Red|White|Rosé|Sparkling|Dessert))',
                r'•\s*((?:Red|White|Rosé|Sparkling|Dessert))'
            ],
            'type': [
                r'(?:^|\s|•\s*)((?:Wine|Champagne|Port|Sherry|Madeira|Brut|Extra-Brut|Sec|Demi-Sec|Doux|Vintage|Magnum))',
                r'•\s*((?:Wine|Champagne|Port|Sherry|Madeira|Brut|Extra-Brut|Sec|Demi-Sec|Doux|Vintage|Magnum))',
                r'((?:Wine|Champagne|Port|Sherry|Madeira|Brut|Extra-Brut|Sec|Demi-Sec|Doux|Vintage|Magnum))\s*[-•]'
            ],
            'sub_type': [
                r'(?:^|\s|•\s*)((?:Still|Sparkling|Fortified|Ice))',
                r'•\s*((?:Still|Sparkling|Fortified|Ice))'
            ],
            
            # Enhanced classification patterns
            'designation': [
                r'(?:^|\s|•\s*)((?:AOC|DOC|DOCG|DO|AVA|IGT|VdP))',
                r'•\s*((?:AOC|DOC|DOCG|DO|AVA|IGT|VdP))'
            ],
            'classification': [
                r'(?:^|\s|•\s*)((?:Grand Cru|Premier Cru|Classé|Riserva|Gran Reserva))',
                r'•\s*((?:Grand Cru|Premier Cru|Classé|Riserva|Gran Reserva))',
                r'((?:Grand Cru|Premier Cru|Classé|Riserva|Gran Reserva))\s*[-•]'
            ],
            
            # Enhanced price patterns with bullet point support
            'price': [
                r'(?:^|\s|•\s*)(?:\$|£|€)?(\d+(?:\.\d{2})?)\s*$',
                r'•\s*(?:\$|£|€)?(\d+(?:\.\d{2})?)\s*$',
                r'(?:\$|£|€)?(\d+(?:\.\d{2})?)\s*[-•]',
                r'•\s*(?:\$|£|€)?(\d+(?:\.\d{2})?)\s*[-•]',
                r'(?:\$|£|€)?(\d+(?:\.\d{2})?)\s*[A-Z]'
            ],
            
            # Enhanced grape variety patterns
            'grape_variety': [
                r'(?:^|\s|•\s*)((?:Chardonnay|Cabernet Sauvignon|Merlot|Pinot Noir|Syrah|Sauvignon Blanc|Riesling|Listan Blanco|Malbec|Grenache|Tempranillo|Nebbiolo|Sangiovese|Zinfandel|Chenin Blanc|Viognier|Savagnin|Melon de Bourgogne))',
                r'•\s*((?:Chardonnay|Cabernet Sauvignon|Merlot|Pinot Noir|Syrah|Sauvignon Blanc|Riesling|Listan Blanco|Malbec|Grenache|Tempranillo|Nebbiolo|Sangiovese|Zinfandel|Chenin Blanc|Viognier|Savagnin|Melon de Bourgogne))',
                r'((?:Chardonnay|Cabernet Sauvignon|Merlot|Pinot Noir|Syrah|Sauvignon Blanc|Riesling|Listan Blanco|Malbec|Grenache|Tempranillo|Nebbiolo|Sangiovese|Zinfandel|Chenin Blanc|Viognier|Savagnin|Melon de Bourgogne))\s*[-•]'
            ],
            
            # New bottle size patterns
            'bottle_size': [
                r'(?:^|\s|•\s*)((?:Magnum|Bottle|Half Bottle|Jeroboam|Methuselah|Salmanazar|Balthazar|Nebuchadnezzar))',
                r'•\s*((?:Magnum|Bottle|Half Bottle|Jeroboam|Methuselah|Salmanazar|Balthazar|Nebuchadnezzar))',
                r'((?:Magnum|Bottle|Half Bottle|Jeroboam|Methuselah|Salmanazar|Balthazar|Nebuchadnezzar))\s*[-•]'
            ]
        }

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to normalize bullet points and special characters.
        """
        if not text:
            return text
        
        # Normalize bullet points and special characters
        text = re.sub(r'[•·∙‣⁃]', ' • ', text)  # Normalize various bullet characters
        text = re.sub(r'[–—]', ' - ', text)      # Normalize dashes
        text = re.sub(r'["“”]', '"', text)       # Normalize quotes
        text = re.sub(r"[’‘']", "'", text)       # Normalize apostrophes

        # Clean up multiple spaces and formatting
        text = re.sub(r'\s+', ' ', text)         # Multiple spaces to single
        text = re.sub(r'•\s*•', '•', text)       # Multiple bullets to single
        text = re.sub(r'-\s*-', '-', text)       # Multiple dashes to single
        
        return text.strip()

    def extract(self, block: Dict[str, Any], restaurant_rules: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], float]:
        text = block.get('text', '')
        if not text:
            return {}, 0.0
        
        # Preprocess the text
        preprocessed_text = self._preprocess_text(text)
        
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
                            rules[field] = [pattern]
                        else:
                            # Add to existing patterns
                            if isinstance(rules[field], list):
                                rules[field].append(pattern)
                            else:
                                rules[field] = [rules[field], pattern]
        
        # Process each field with multiple patterns
        for field, patterns in rules.items():
            if isinstance(patterns, str):
                patterns = [patterns]  # Convert single pattern to list
            
            for pattern in patterns:
                match = re.search(pattern, preprocessed_text, re.IGNORECASE)
                if match:
                    # Clean up the extracted value
                    value = match.group(1).strip()
                    
                    # Check exclusions if restaurant rules exist
                    if restaurant_rules and field in restaurant_rules:
                        if 'exclusions' in restaurant_rules[field]:
                            if value in restaurant_rules[field]['exclusions']:
                                continue
                    
                    # Additional validation for common fields
                    if self._validate_field_value(field, value):
                        if value and len(value) > 1:  # Avoid single character matches
                            extracted_fields[field] = {
                                'value': value,
                                'confidence': 0.8,  # Base confidence for regex matches
                                'provenance': 'regex'
                            }
                            total_matches += 1
                            break  # Use first successful pattern for each field
        
        # Calculate confidence based on number of matches
        confidence = total_matches / len(rules) if rules else 0.0
        return extracted_fields, confidence

    def _validate_field_value(self, field: str, value: str) -> bool:
        """
        Validate extracted field values to ensure they make sense.
        """
        if not value:
            return False
        
        # Field-specific validation
        if field == 'vintage':
            # Vintage should be a year or NV
            if not re.match(r'^(?:19|20)\d{2}$|^NV$', value):
                return False
        
        elif field == 'price':
            # Price should be numeric
            if not re.match(r'^\d+(?:\.\d{2})?$', value):
                return False
        
        elif field == 'producer_name':
            # Producer should start with capital letter and be reasonable length
            if not re.match(r'^[A-Z][A-Za-z\s\-&\.]{1,50}$', value):
                return False
        
        elif field == 'grape_variety':
            # Grape variety should be a known grape
            known_grapes = {
                'chardonnay', 'pinot noir', 'cabernet sauvignon', 'merlot', 'syrah',
                'sauvignon blanc', 'riesling', 'malbec', 'grenache', 'tempranillo',
                'nebbiolo', 'sangiovese', 'zinfandel', 'chenin blanc', 'viognier',
                'savagnin', 'melon de bourgogne', 'listan blanco'
            }
            if value.lower() not in known_grapes:
                return False
        
        return True 