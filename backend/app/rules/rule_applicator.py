import re
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RuleApplicator:
    """
    Applies generated rules to wine entries with confidence scoring and fallback logic.
    """
    
    def __init__(self):
        self.confidence_threshold = 0.8
        self.min_confidence_for_rule = 0.6
    
    def apply_rules(self, wine_block: Dict[str, Any], rules: Any) -> Dict[str, Any]:
        """Apply rules to a wine block. Handles both list and dictionary rule formats."""
        if not wine_block or not isinstance(wine_block, dict):
            logger.error(f"[apply_rules] wine_block was None or not a dict: {wine_block}")
            return {'fields': {}, 'confidence': 0.0, 'provenance': 'invalid_block'}
        
        if not rules:
            logger.error(f"[apply_rules] rules was None or empty: {rules}")
            return {'fields': {}, 'confidence': 0.0, 'provenance': 'invalid_rules'}
        
        text = wine_block.get('text', '')
        if not text:
            logger.warning(f"[apply_rules] wine_block has no text")
            return {'fields': {}, 'confidence': 0.0, 'provenance': 'no_text'}
        
        extracted_fields = {}
        total_confidence = 0.0
        applied_rules = 0
        
        # Handle dictionary rule format (new comprehensive format)
        if isinstance(rules, dict):
            for field_name, field_rules in rules.items():
                if not isinstance(field_rules, dict):
                    continue
                
                # Apply comprehensive field rules
                field_result = self._apply_field_rules(text, field_name, field_rules)
                if field_result:
                    extracted_fields[field_name] = {
                        'value': field_result['value'],
                        'confidence': field_result['confidence'],
                        'provenance': 'rule',
                        'rule_type': field_result.get('rule_type', 'comprehensive'),
                        'pattern_used': field_result.get('pattern_used', 'multiple')
                    }
                    total_confidence += field_result['confidence']
                    applied_rules += 1
        
        # Handle list rule format (legacy format)
        elif isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    logger.error(f"[apply_rules] rule was not a dict: {rule}")
                    continue
                    
                try:
                    field_name = rule.get('field_name')
                    pattern = rule.get('pattern')
                    confidence = rule.get('confidence', 0.5)
                    
                    if not field_name or not pattern:
                        logger.warning(f"[apply_rules] rule missing field_name or pattern: {rule}")
                        continue
                    
                    # Apply regex pattern
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1) if match.groups() else match.group(0)
                        extracted_fields[field_name] = {
                            'value': value.strip(),
                            'confidence': confidence,
                            'provenance': 'rule',
                            'rule_type': 'regex',
                            'pattern_used': pattern
                        }
                        total_confidence += confidence
                        applied_rules += 1
                        
                except Exception as e:
                    logger.error(f"[apply_rules] Error applying rule {rule}: {e}")
                    continue
        else:
            logger.error(f"[apply_rules] rules was not a dict or list: {type(rules)}")
            return {'fields': {}, 'confidence': 0.0, 'provenance': 'invalid_rules'}
        
        # Calculate average confidence
        avg_confidence = total_confidence / max(applied_rules, 1)
        
        return {
            'fields': extracted_fields,
            'confidence': avg_confidence,
            'provenance': 'rules',
            'applied_rules': applied_rules,
            'fields_extracted': len(extracted_fields)
        }
    
    def _convert_dict_rules_to_list(self, rules_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert dictionary rule format to list format for compatibility."""
        rules_list = []
        
        for field_name, field_rules in rules_dict.items():
            if not isinstance(field_rules, dict):
                continue
                
            # Extract regex patterns
            regex_patterns = field_rules.get('regex_patterns', [])
            for pattern in regex_patterns:
                rules_list.append({
                    'field_name': field_name,
                    'pattern': pattern,
                    'confidence': field_rules.get('confidence_threshold', 0.5),
                    'rule_type': 'regex'
                })
            
            # Extract structural patterns (convert to regex-like patterns)
            structural_rules = field_rules.get('structural_rules', [])
            for struct_rule in structural_rules:
                if struct_rule.get('type') == 'structure' and 'pattern' in struct_rule:
                    pattern = struct_rule['pattern']
                    if isinstance(pattern, list):
                        # Convert list pattern to regex
                        pattern_str = r'\s*\|\s*'.join([re.escape(p) for p in pattern])
                        rules_list.append({
                            'field_name': field_name,
                            'pattern': pattern_str,
                            'confidence': struct_rule.get('confidence', 0.8),
                            'rule_type': 'structural'
                        })
        
        return rules_list
    
    def _apply_field_rules(self, text: str, field_name: str, field_rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply comprehensive field rules to extract field value."""
        best_result = None
        best_confidence = 0.0
        best_pattern = None
        best_rule_type = None
        
        # Apply regex patterns
        regex_patterns = field_rules.get('regex_patterns', [])
        for pattern in regex_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                confidence = field_rules.get('confidence_threshold', 0.6)
                
                # Special handling for region field - add Champagne-specific patterns
                if field_name == 'region':
                    confidence = self._calculate_region_confidence(value, text)
                
                if confidence > best_confidence:
                    best_result = {
                        'value': value.strip(),
                        'confidence': confidence,
                        'pattern_used': pattern,
                        'rule_type': 'regex'
                    }
                    best_confidence = confidence
                    best_pattern = pattern
                    best_rule_type = 'regex'
        
        # Apply positional rules
        if 'positional_rules' in field_rules:
            pos_result = self._apply_positional_rules(text, field_rules['positional_rules'])
            if pos_result and pos_result['confidence'] > best_confidence:
                best_result = pos_result
                best_confidence = pos_result['confidence']
                best_pattern = pos_result.get('pattern_used')
                best_rule_type = 'positional'
        
        # Apply structural rules
        structural_rules = field_rules.get('structural_rules', [])
        for struct_rule in structural_rules:
            if struct_rule.get('type') == 'structure' and 'pattern' in struct_rule:
                pattern = struct_rule['pattern']
                confidence = struct_rule.get('confidence', 0.8)
                
                if isinstance(pattern, list):
                    # Check if all pattern elements are present in text
                    pattern_found = all(p.lower() in text.lower() for p in pattern)
                    if pattern_found:
                        # Extract the most relevant part based on pattern
                        value = self._extract_structural_value(text, pattern)
                        
                        if confidence > best_confidence:
                            best_result = {
                                'value': value,
                                'confidence': confidence,
                                'pattern_used': str(pattern),
                                'rule_type': 'structural'
                            }
                            best_confidence = confidence
                            best_pattern = str(pattern)
                            best_rule_type = 'structural'
        
        # Apply format rules
        if 'format_rules' in field_rules:
            format_result = self._apply_format_rules(text, field_rules['format_rules'])
            if format_result and format_result['confidence'] > best_confidence:
                best_result = format_result
                best_confidence = format_result['confidence']
                best_pattern = format_result.get('pattern_used')
                best_rule_type = 'format'
        
        # Apply validation rules to enhance confidence
        if best_result and 'validation_rules' in field_rules:
            validation_result = self._apply_validation_rules(best_result['value'], field_rules['validation_rules'])
            if validation_result:
                best_result['confidence'] *= validation_result['confidence']
                best_result['validation_passed'] = True
                best_confidence = best_result['confidence']
            else:
                best_result['validation_passed'] = False
                best_result['confidence'] *= 0.5  # Reduce confidence if validation fails
                best_confidence = best_result['confidence']
        
        # Apply database validation rules
        if best_result and 'database_validation_rules' in field_rules:
            db_validation_result = self._apply_database_validation_rules(best_result['value'], field_rules['database_validation_rules'])
            if db_validation_result:
                best_result['confidence'] *= db_validation_result['confidence']
                best_result['database_validation_passed'] = True
                best_confidence = best_result['confidence']
            else:
                best_result['database_validation_passed'] = False
                best_result['confidence'] *= 0.7  # Moderate reduction for database validation failure
                best_confidence = best_result['confidence']
        
        # Apply NER validation rules
        if best_result and 'ner_validation_rules' in field_rules:
            ner_validation_result = self._apply_ner_validation_rules(best_result['value'], field_rules['ner_validation_rules'])
            if ner_validation_result:
                best_result['confidence'] *= ner_validation_result['confidence']
                best_result['ner_validation_passed'] = True
                best_confidence = best_result['confidence']
            else:
                best_result['ner_validation_passed'] = False
                best_result['confidence'] *= 0.8  # Small reduction for NER validation failure
                best_confidence = best_result['confidence']
        
        # Apply conditional rules to enhance confidence
        if 'conditional_rules' in field_rules:
            conditional_result = self._apply_conditional_rules(text, field_rules['conditional_rules'])
            if conditional_result:
                if best_result:
                    best_result['confidence'] *= conditional_result['confidence']
                    best_result['conditional_matched'] = True
                    best_confidence = best_result['confidence']
                else:
                    # If no other rules matched, use conditional rule
                    best_result = conditional_result
                    best_confidence = conditional_result['confidence']
                    best_pattern = conditional_result.get('pattern_used')
                    best_rule_type = 'conditional'
            else:
                if best_result:
                    best_result['conditional_matched'] = False
        
        # Apply sequence rules to enhance confidence
        if 'sequence_rules' in field_rules:
            sequence_result = self._apply_sequence_rules(text, field_rules['sequence_rules'])
            if sequence_result and best_result:
                best_result['confidence'] *= sequence_result['confidence']
                best_result['sequence_matched'] = True
                best_confidence = best_result['confidence']
        
        # Check if we have a field-specific confidence threshold
        confidence_threshold = field_rules.get('confidence_threshold', 0.6)
        
        if best_result and best_confidence >= confidence_threshold:
            best_result['confidence'] = best_confidence
            best_result['pattern_used'] = best_pattern
            best_result['rule_type'] = best_rule_type
            return best_result
        
        return None
    
    def _calculate_region_confidence(self, value: str, text: str) -> float:
        """Calculate confidence for region extraction with Champagne-specific logic."""
        base_confidence = 0.6
        
        # Champagne regions with high confidence
        champagne_regions = [
            'montagne de reims', 'côtes des blancs', 'marne valley',
            'grand cru', 'mailly-champagne', 'cramant', 'avize',
            'le mesnil', 'verzenay', 'verzy', 'bouzy', 'ambonnay',
            'cote des blancs', 'montagne de reims', 'marne valley'
        ]
        
        if value.lower() in champagne_regions:
            base_confidence = 0.9
        
        # Check if region appears in context with producer
        if any(region in text.lower() for region in champagne_regions):
            base_confidence += 0.1
        
        # Check for geographic indicators
        if any(indicator in text.lower() for indicator in ['champagne', 'france', 'grand cru']):
            base_confidence += 0.1
        
        # Check for specific Champagne patterns
        champagne_patterns = [
            r'montagne de reims',
            r'côtes? des? blancs?',
            r'marne valley',
            r'grand cru',
            r'mailly-champagne',
            r'cramant',
            r'avize',
            r'le mesnil',
            r'verzenay',
            r'verzy',
            r'bouzy',
            r'ambonnay'
        ]
        
        for pattern in champagne_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _extract_structural_value(self, text: str, pattern: List[str]) -> str:
        """Extract value based on structural pattern."""
        # For now, return the first pattern element found in text
        for p in pattern:
            if p.lower() in text.lower():
                return p
        return text.strip()
    
    def _apply_positional_rules(self, text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply positional rules to extract field value."""
        for rule in rules:
            if rule.get('type') == 'position' and 'average_position' in rule:
                avg_pos = rule['average_position']
                confidence = rule.get('confidence', 0.7)
                
                # Extract text around the expected position
                start_pos = max(0, int(avg_pos - 10))
                end_pos = min(len(text), int(avg_pos + 10))
                segment = text[start_pos:end_pos]
                
                # Look for potential field values in the segment
                # This is a simplified implementation - could be enhanced
                words = segment.split()
                if words:
                    # Take the most prominent word (capitalized, etc.)
                    for word in words:
                        if word[0].isupper() and len(word) > 2:
                            return {
                                'value': word,
                                'confidence': confidence * 0.8,  # Reduce confidence for positional rules
                                'position_used': avg_pos,
                                'rule_type': 'positional'
                            }
        
        return None
    
    def _apply_format_rules(self, text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply format rules to extract field value."""
        for rule in rules:
            rule_type = rule.get('type')
            pattern = rule.get('pattern', '')
            confidence = rule.get('confidence', 0.7)
            
            if rule_type == 'capitalization':
                # Look for words matching the capitalization pattern
                try:
                    matches = re.findall(pattern, text)
                    if matches:
                        return {
                            'value': matches[0],
                            'confidence': confidence * 0.7,
                            'format_rule': rule_type,
                            'rule_type': 'format'
                        }
                except re.error:
                    continue
            
            elif rule_type == 'separator':
                # Look for text separated by the specified separators
                try:
                    matches = re.findall(pattern, text)
                    if matches:
                        return {
                            'value': matches[0],
                            'confidence': confidence * 0.7,
                            'format_rule': rule_type,
                            'rule_type': 'format'
                        }
                except re.error:
                    continue
        
        return None
    
    def _apply_validation_rules(self, value: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply validation rules to a field value."""
        for rule in rules:
            rule_type = rule.get('type')
            confidence = rule.get('confidence', 0.8)
            
            if rule_type == 'range':
                # Validate numeric range
                try:
                    num_value = float(value)
                    min_val = rule.get('min')
                    max_val = rule.get('max')
                    
                    if min_val is not None and num_value < min_val:
                        return None
                    if max_val is not None and num_value > max_val:
                        return None
                    
                    return {'confidence': confidence}
                except ValueError:
                    return None
            
            elif rule_type == 'format':
                # Validate format pattern
                pattern = rule.get('pattern', '')
                try:
                    if re.match(pattern, value):
                        return {'confidence': confidence}
                    else:
                        return None
                except re.error:
                    continue
            
            elif rule_type == 'length':
                # Validate length constraints
                min_len = rule.get('min_length', 0)
                max_len = rule.get('max_length', float('inf'))
                
                if min_len <= len(value) <= max_len:
                    return {'confidence': confidence}
                else:
                    return None
        
        return {'confidence': 1.0}  # Default validation passed
    
    def _apply_database_validation_rules(self, value: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply database validation rules to a field value."""
        for rule in rules:
            rule_type = rule.get('type')
            confidence = rule.get('confidence', 0.9)
            
            if rule_type == 'database_match':
                valid_values = rule.get('valid_values', [])
                field = rule.get('field', '')
                
                # Check if value matches any database-extracted values
                if value in valid_values:
                    return {'confidence': confidence}
                else:
                    # Try fuzzy matching for close matches
                    from rapidfuzz import fuzz
                    best_match = None
                    best_score = 0
                    
                    for db_value in valid_values:
                        score = fuzz.ratio(value.lower(), db_value.lower())
                        if score > best_score:
                            best_score = score
                            best_match = db_value
                    
                    # If we have a very close match (>90%), consider it valid
                    if best_score > 90:
                        return {'confidence': confidence * 0.9}
                    else:
                        return None
            
        return {'confidence': 1.0}  # Default validation passed
    
    def _apply_ner_validation_rules(self, value: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply NER validation rules to a field value."""
        for rule in rules:
            rule_type = rule.get('type')
            confidence = rule.get('confidence', 0.8)
            
            if rule_type == 'ner_entity_match':
                valid_values = rule.get('valid_values', [])
                entity_type = rule.get('entity_type', '')
                
                # Check if value matches any NER-extracted values
                if value in valid_values:
                    return {'confidence': confidence}
                else:
                    # Try fuzzy matching for close matches
                    from rapidfuzz import fuzz
                    best_match = None
                    best_score = 0
                    
                    for ner_value in valid_values:
                        score = fuzz.ratio(value.lower(), ner_value.lower())
                        if score > best_score:
                            best_score = score
                            best_match = ner_value
                    
                    # If we have a close match (>85%), consider it valid
                    if best_score > 85:
                        return {'confidence': confidence * 0.85}
                    else:
                        return None
            
        return {'confidence': 1.0}  # Default validation passed
    
    def _apply_conditional_rules(self, text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply conditional rules to extract field value."""
        for rule in rules:
            if rule.get('type') == 'context' and 'condition' in rule:
                condition = rule['condition']
                confidence = rule.get('confidence', 0.6)
                
                if self._evaluate_condition(text, condition):
                    return {
                        'value': text.strip(),  # Return full text for conditional matches
                        'confidence': confidence,
                        'pattern_used': condition,
                        'rule_type': 'conditional'
                    }
        
        return None
    
    def _apply_sequence_rules(self, text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Apply sequence rules to validate field order."""
        for rule in rules:
            if rule.get('type') == 'order':
                before_field = rule.get('before')
                after_field = rule.get('after')
                confidence = rule.get('confidence', 0.7)
                
                # For now, just return a confidence boost if sequence rule exists
                # In a more sophisticated implementation, we'd check actual field order
                return {
                    'value': text.strip(),
                    'confidence': confidence,
                    'pattern_used': f"sequence:{before_field}-{after_field}",
                    'rule_type': 'sequence'
                }
        
        return None
    
    def _evaluate_condition(self, text: str, condition: str) -> bool:
        """Evaluate a condition against the text."""
        text_lower = text.lower()
        
        if condition == 'if_contains_champagne':
            return 'champagne' in text_lower
        elif condition == 'if_contains_bordeaux':
            return 'bordeaux' in text_lower
        elif condition == 'if_contains_burgundy':
            return 'burgundy' in text_lower
        elif condition == 'if_contains_red_wine':
            return any(word in text_lower for word in ['red', 'rouge', 'tinto', 'rosso'])
        elif condition == 'if_contains_white_wine':
            return any(word in text_lower for word in ['white', 'blanc', 'blanco', 'bianco'])
        elif condition == 'if_contains_sparkling':
            return any(word in text_lower for word in ['sparkling', 'champagne', 'cremant', 'prosecco'])
        
        return False
    
    def calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence score for extraction result."""
        if not result:
            return 0.0
        
        # Base confidence from the extraction
        base_confidence = result.get('confidence', 0.0)
        
        # Apply confidence modifiers
        confidence_modifiers = []
        
        # Validation passed bonus
        if result.get('validation_passed', False):
            confidence_modifiers.append(1.1)
        
        # Conditional rules matched bonus
        if result.get('conditional_matched', False):
            confidence_modifiers.append(1.05)
        
        # Apply modifiers
        final_confidence = base_confidence
        for modifier in confidence_modifiers:
            final_confidence *= modifier
        
        return min(1.0, final_confidence)
    
    def should_use_fallback(self, result: Dict[str, Any]) -> bool:
        """Determine if AI fallback should be used."""
        if not result or not isinstance(result, dict):
            return True
        
        confidence = result.get('confidence', 0.0)
        fields = result.get('fields', {})
        
        # Use fallback if confidence is low or no fields extracted
        return confidence < self.min_confidence_for_rule or not fields
    
    def merge_results(self, rule_result: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge rule results with AI fallback results."""
        # Defensive: ensure merged is a dict
        if rule_result is None or not isinstance(rule_result, dict):
            logger.error(f"[merge_results] rule_result was None or not a dict: {rule_result}")
            merged = {}
        else:
            merged = rule_result.copy()

        # Ensure fields is always a dictionary - CRITICAL FIX
        if 'fields' not in merged or merged['fields'] is None or not isinstance(merged['fields'], dict):
            logger.error(f"[merge_results] merged['fields'] was None, not a dict, or missing, setting to {{}}. Previous value: {merged.get('fields')}")
            merged['fields'] = {}

        # If rule result has low confidence, use AI result for missing fields
        if self.should_use_fallback(rule_result):
            rule_fields = rule_result.get('fields', {}) if rule_result and isinstance(rule_result, dict) else {}
            if not isinstance(rule_fields, dict) or rule_fields is None:
                logger.error(f"[merge_results] rule_fields was None or not a dict: {rule_fields}")
                rule_fields = {}
            ai_fields = ai_result.get('fields', {}) if ai_result and isinstance(ai_result, dict) else {}
            if not isinstance(ai_fields, dict) or ai_fields is None:
                logger.error(f"[merge_results] ai_fields was None or not a dict: {ai_fields}")
                ai_fields = {}

            for field_name, ai_field_data in ai_fields.items():
                if not isinstance(ai_field_data, dict):
                    logger.error(f"[merge_results] ai_field_data for field '{field_name}' was not a dict: {ai_field_data}")
                    continue
                if field_name not in rule_fields:
                    # Ensure merged['fields'] is still a dict before assignment
                    if merged['fields'] is None:
                        logger.error(f"[merge_results] merged['fields'] became None before assignment, recreating dict")
                        merged['fields'] = {}
                    merged['fields'][field_name] = {
                        'value': ai_field_data.get('value'),
                        'confidence': ai_field_data.get('confidence', 0.0) * 0.8,  # Reduce AI confidence
                        'provenance': 'ai_fallback'
                    }
                elif not isinstance(rule_fields[field_name], dict):
                    logger.error(f"[merge_results] rule_fields['{field_name}'] was not a dict: {rule_fields[field_name]}")
                    # Ensure merged['fields'] is still a dict before assignment
                    if merged['fields'] is None:
                        logger.error(f"[merge_results] merged['fields'] became None before assignment, recreating dict")
                        merged['fields'] = {}
                    merged['fields'][field_name] = {
                        'value': ai_field_data.get('value'),
                        'confidence': ai_field_data.get('confidence', 0.0) * 0.8,
                        'provenance': 'ai_fallback'
                    }
                elif rule_fields[field_name].get('confidence', 0.0) < ai_field_data.get('confidence', 0.0) * 0.8:
                    # Use AI result if it has higher confidence
                    # Ensure merged['fields'] is still a dict before assignment
                    if merged['fields'] is None:
                        logger.error(f"[merge_results] merged['fields'] became None before assignment, recreating dict")
                        merged['fields'] = {}
                    merged['fields'][field_name] = {
                        'value': ai_field_data.get('value'),
                        'confidence': ai_field_data.get('confidence', 0.0) * 0.8,
                        'provenance': 'ai_fallback'
                    }

            merged['provenance'] = 'hybrid_rules_and_ai'

        return merged 