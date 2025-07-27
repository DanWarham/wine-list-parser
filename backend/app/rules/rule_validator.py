from typing import List, Dict, Any, Optional, Tuple
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RuleValidator:
    """
    Validates generated rules against test entries and adjusts confidence scores.
    """
    
    def __init__(self):
        self.min_validation_entries = 5
        self.confidence_adjustment_factor = 0.1
    
    def validate_rules(self, rules: Dict[str, Any], test_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate generated rules against test entries.
        
        Args:
            rules: Generated rules dictionary
            test_entries: Test entries for validation
            
        Returns:
            Validation results with metrics and adjusted rules
        """
        if len(test_entries) < self.min_validation_entries:
            logger.warning(f"Insufficient test entries ({len(test_entries)}) for validation")
            return {"error": "Insufficient test entries", "adjusted_rules": rules}
        
        logger.info(f"Validating rules against {len(test_entries)} test entries")
        
        validation_results = {
            'field_validation': {},
            'pattern_validation': {},
            'overall_metrics': {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'accuracy': 0.0
            },
            'rule_adjustments': {}
        }
        
        # Validate each field
        for field_name, field_rules in rules.items():
            field_results = self._validate_field_rules(field_name, field_rules, test_entries)
            validation_results['field_validation'][field_name] = field_results
        
        # Calculate overall metrics
        validation_results['overall_metrics'] = self._calculate_overall_metrics(
            validation_results['field_validation']
        )
        
        # Adjust rules based on validation results
        adjusted_rules = self._adjust_rules_based_on_validation(rules, validation_results)
        validation_results['adjusted_rules'] = adjusted_rules
        
        logger.info(f"Validation completed. Overall F1: {validation_results['overall_metrics']['f1_score']:.3f}")
        
        return validation_results
    
    def _validate_field_rules(self, field_name: str, field_rules: Dict[str, Any], 
                            test_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate rules for a specific field."""
        field_results = {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'pattern_performance': {},
            'rule_type_performance': {},
            'validation_errors': []
        }
        
        for entry in test_entries:
            text = entry.get('text', '')
            expected_value = self._get_expected_value(entry, field_name)
            
            if not text:
                continue
            
            # Test each rule type
            rule_results = self._test_field_rules(text, field_rules, expected_value, field_name)
            
            # Aggregate results
            for rule_type, result in rule_results.items():
                if rule_type not in field_results['rule_type_performance']:
                    field_results['rule_type_performance'][rule_type] = {
                        'true_positives': 0,
                        'false_positives': 0,
                        'false_negatives': 0
                    }
                
                perf = field_results['rule_type_performance'][rule_type]
                perf['true_positives'] += result['true_positives']
                perf['false_positives'] += result['false_positives']
                perf['false_negatives'] += result['false_negatives']
            
            # Overall field result
            best_result = self._get_best_rule_result(rule_results)
            if best_result:
                field_results['true_positives'] += best_result['true_positives']
                field_results['false_positives'] += best_result['false_positives']
                field_results['false_negatives'] += best_result['false_negatives']
        
        # Calculate field metrics
        field_results['metrics'] = self._calculate_field_metrics(field_results)
        
        return field_results
    
    def _test_field_rules(self, text: str, field_rules: Dict[str, Any], 
                         expected_value: Optional[str], field_name: str = None) -> Dict[str, Dict[str, int]]:
        """Test different rule types for a field."""
        results = {}
        
        # Test regex patterns
        if 'regex_patterns' in field_rules:
            results['regex'] = self._test_regex_patterns(text, field_rules['regex_patterns'], expected_value, field_name)
        
        # Test positional rules
        if 'positional_rules' in field_rules:
            results['positional'] = self._test_positional_rules(text, field_rules['positional_rules'], expected_value, field_name)
        
        # Test structural rules
        if 'structural_rules' in field_rules:
            results['structural'] = self._test_structural_rules(text, field_rules['structural_rules'], expected_value, field_name)
        
        # Test format rules
        if 'format_rules' in field_rules:
            results['format'] = self._test_format_rules(text, field_rules['format_rules'], expected_value, field_name)
        
        return results
    
    def _test_regex_patterns(self, text: str, patterns: List[str], 
                           expected_value: Optional[str], field_name: str = None) -> Dict[str, int]:
        """Test regex patterns."""
        result = {'true_positives': 0, 'false_positives': 0, 'false_negatives': 0}
        
        for pattern in patterns:
            try:
                match = re.search(pattern, text)
                if match:
                    extracted_value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    extracted_value = extracted_value.strip()
                    
                    if expected_value:
                        if self._values_match(extracted_value, expected_value, field_name):
                            result['true_positives'] += 1
                        else:
                            result['false_positives'] += 1
                    else:
                        result['false_positives'] += 1
                elif expected_value:
                    result['false_negatives'] += 1
                    
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {str(e)}")
                continue
        
        return result
    
    def _test_positional_rules(self, text: str, rules: List[Dict[str, Any]], 
                             expected_value: Optional[str], field_name: str = None) -> Dict[str, int]:
        """Test positional rules."""
        result = {'true_positives': 0, 'false_positives': 0, 'false_negatives': 0}
        
        for rule in rules:
            if rule.get('type') == 'position' and 'average_position' in rule:
                avg_pos = rule['average_position']
                start_pos = max(0, int(avg_pos - 10))
                end_pos = min(len(text), int(avg_pos + 10))
                segment = text[start_pos:end_pos]
                
                # Extract potential value from segment
                words = segment.split()
                extracted_value = None
                for word in words:
                    if word[0].isupper() and len(word) > 2:
                        extracted_value = word
                        break
                
                if extracted_value:
                    if expected_value and self._values_match(extracted_value, expected_value, field_name):
                        result['true_positives'] += 1
                    else:
                        result['false_positives'] += 1
                elif expected_value:
                    result['false_negatives'] += 1
        
        return result
    
    def _test_structural_rules(self, text: str, rules: List[Dict[str, Any]], 
                             expected_value: Optional[str], field_name: str = None) -> Dict[str, int]:
        """Test structural rules."""
        result = {'true_positives': 0, 'false_positives': 0, 'false_negatives': 0}
        
        for rule in rules:
            if rule.get('type') == 'structure' and 'pattern' in rule:
                pattern_words = rule['pattern']
                text_words = text.split()
                
                extracted_value = None
                for i in range(len(text_words) - len(pattern_words) + 1):
                    if text_words[i:i + len(pattern_words)] == pattern_words:
                        if i + len(pattern_words) < len(text_words):
                            extracted_value = text_words[i + len(pattern_words)]
                            break
                
                if extracted_value:
                    if expected_value and self._values_match(extracted_value, expected_value, field_name):
                        result['true_positives'] += 1
                    else:
                        result['false_positives'] += 1
                elif expected_value:
                    result['false_negatives'] += 1
        
        return result
    
    def _test_format_rules(self, text: str, rules: List[Dict[str, Any]], 
                          expected_value: Optional[str], field_name: str = None) -> Dict[str, int]:
        """Test format rules."""
        result = {'true_positives': 0, 'false_positives': 0, 'false_negatives': 0}
        
        for rule in rules:
            rule_type = rule.get('type')
            pattern = rule.get('pattern', '')
            
            try:
                if rule_type == 'capitalization':
                    matches = re.findall(pattern, text)
                    if matches:
                        extracted_value = matches[0]
                        if expected_value and self._values_match(extracted_value, expected_value, field_name):
                            result['true_positives'] += 1
                        else:
                            result['false_positives'] += 1
                    elif expected_value:
                        result['false_negatives'] += 1
                        
            except re.error:
                continue
        
        return result
    
    def _get_expected_value(self, entry: Dict[str, Any], field_name: str) -> Optional[str]:
        """Get expected value for a field from the entry."""
        field_data = entry.get(field_name, {})
        
        if isinstance(field_data, dict):
            return field_data.get('value')
        else:
            return field_data
    
    def _values_match(self, value1: str, value2: str, field_name: str = None) -> bool:
        """Check if two values match (with normalization and field-specific logic)."""
        if not value1 or not value2:
            return False
        
        # Normalize values
        norm1 = value1.lower().strip()
        norm2 = value2.lower().strip()
        
        # Field-specific validation logic
        if field_name == 'vintage':
            # For vintage, exact match or year range validation
            if norm1 == norm2:
                return True
            # Check if both are valid years
            if self._is_valid_year(norm1) and self._is_valid_year(norm2):
                return norm1 == norm2
            return False
        
        elif field_name == 'price':
            # For price, normalize currency symbols and decimals
            price1 = self._normalize_price(norm1)
            price2 = self._normalize_price(norm2)
            return price1 == price2
        
        elif field_name == 'producer_name':
            # For producer names, more flexible matching
            return self._producer_names_match(norm1, norm2)
        
        # Default exact match
        return norm1 == norm2
    
    def _is_valid_year(self, value: str) -> bool:
        """Check if a value is a valid year."""
        try:
            year = int(value)
            return 1900 <= year <= 2024
        except ValueError:
            return value.lower() == 'nv'
    
    def _normalize_price(self, price: str) -> str:
        """Normalize price string for comparison."""
        # Remove currency symbols and normalize
        import re
        # Remove currency symbols and extra spaces
        normalized = re.sub(r'[£€$,\s]', '', price)
        # Handle decimal points
        if '.' in normalized:
            parts = normalized.split('.')
            if len(parts) == 2 and len(parts[1]) == 2:
                # Keep as is (e.g., "375.00")
                pass
            else:
                # Remove decimal if not cents
                normalized = parts[0]
        return normalized
    
    def _producer_names_match(self, name1: str, name2: str) -> bool:
        """Check if producer names match with some flexibility."""
        # Exact match
        if name1 == name2:
            return True
        
        # Split into words and check for partial matches
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        # Check for significant overlap
        common_words = words1.intersection(words2)
        if len(common_words) >= min(len(words1), len(words2)) * 0.7:
            return True
        
        return False
    
    def _get_best_rule_result(self, rule_results: Dict[str, Dict[str, int]]) -> Optional[Dict[str, int]]:
        """Get the best performing rule result."""
        if not rule_results:
            return None
        
        # Calculate F1 score for each rule type
        best_result = None
        best_f1 = 0.0
        
        for rule_type, result in rule_results.items():
            tp = result['true_positives']
            fp = result['false_positives']
            fn = result['false_negatives']
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_result = result
        
        return best_result
    
    def _calculate_field_metrics(self, field_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate metrics for a field."""
        tp = field_results['true_positives']
        fp = field_results['false_positives']
        fn = field_results['false_negatives']
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'accuracy': accuracy
        }
    
    def _calculate_overall_metrics(self, field_validation: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall validation metrics."""
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        for field_results in field_validation.values():
            total_tp += field_results['true_positives']
            total_fp += field_results['false_positives']
            total_fn += field_results['false_negatives']
        
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = total_tp / (total_tp + total_fp + total_fn) if (total_tp + total_fp + total_fn) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'accuracy': accuracy
        }
    
    def _adjust_rules_based_on_validation(self, rules: Dict[str, Any], 
                                        validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust rules based on validation results."""
        adjusted_rules = rules.copy()
        
        for field_name, field_validation in validation_results['field_validation'].items():
            if field_name not in adjusted_rules:
                continue
            
            field_metrics = field_validation['metrics']
            field_rules = adjusted_rules[field_name]
            
            # Adjust confidence scores based on validation performance
            performance_factor = field_metrics['f1_score']
            
            # Adjust rule type confidences
            for rule_type, rule_performance in field_validation['rule_type_performance'].items():
                if rule_type in field_rules:
                    rule_metrics = self._calculate_field_metrics(rule_performance)
                    rule_f1 = rule_metrics['f1_score']
                    
                    # Adjust confidence for this rule type
                    if rule_type == 'regex_patterns':
                        for pattern in field_rules[rule_type]:
                            # Adjust pattern confidence based on performance
                            pass  # Implementation depends on pattern structure
                    
                    elif rule_type == 'positional_rules':
                        for rule in field_rules[rule_type]:
                            if 'confidence' in rule:
                                rule['confidence'] *= (0.5 + 0.5 * rule_f1)
                    
                    elif rule_type == 'structural_rules':
                        for rule in field_rules[rule_type]:
                            if 'confidence' in rule:
                                rule['confidence'] *= (0.5 + 0.5 * rule_f1)
                    
                    elif rule_type == 'format_rules':
                        for rule in field_rules[rule_type]:
                            if 'confidence' in rule:
                                rule['confidence'] *= (0.5 + 0.5 * rule_f1)
            
            # Adjust overall field confidence threshold
            if 'confidence_threshold' in field_rules:
                field_rules['confidence_threshold'] *= (0.5 + 0.5 * performance_factor)
        
        return adjusted_rules
    
    def get_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of validation results."""
        overall_metrics = validation_results['overall_metrics']
        field_validation = validation_results['field_validation']
        
        # Get best and worst performing fields
        field_performances = []
        for field_name, field_results in field_validation.items():
            metrics = field_results['metrics']
            field_performances.append({
                'field': field_name,
                'f1_score': metrics['f1_score'],
                'precision': metrics['precision'],
                'recall': metrics['recall']
            })
        
        field_performances.sort(key=lambda x: x['f1_score'], reverse=True)
        
        return {
            'overall_f1_score': overall_metrics['f1_score'],
            'overall_precision': overall_metrics['precision'],
            'overall_recall': overall_metrics['recall'],
            'overall_accuracy': overall_metrics['accuracy'],
            'best_performing_field': field_performances[0] if field_performances else None,
            'worst_performing_field': field_performances[-1] if field_performances else None,
            'field_count': len(field_validation),
            'validation_quality': self._assess_validation_quality(overall_metrics['f1_score'])
        }
    
    def _assess_validation_quality(self, f1_score: float) -> str:
        """Assess the quality of validation results."""
        if f1_score >= 0.9:
            return 'excellent'
        elif f1_score >= 0.8:
            return 'good'
        elif f1_score >= 0.7:
            return 'fair'
        elif f1_score >= 0.6:
            return 'poor'
        else:
            return 'very_poor'
