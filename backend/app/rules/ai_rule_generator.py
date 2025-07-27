import json
import openai
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class AIRuleGenerator:
    """
    AI-powered rule generator that uses GPT-4 to generate comprehensive extraction rules
    from a small sample of wine list entries.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("No OpenAI API key provided - AI rule generation will be disabled")
    
    def generate_rules(self, sample_entries: List[Dict[str, Any]], 
                      ai_results: List[Dict[str, Any]], 
                      regex_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive rules using AI analysis of sample entries.
        
        Args:
            sample_entries: List of sample wine entries with text
            ai_results: AI extraction results for the sample
            regex_results: Regex extraction results for the sample
            
        Returns:
            Dictionary containing generated rules and metadata
        """
        if not self.api_key:
            logger.error("No API key available for AI rule generation")
            return {"error": "No API key available", "rules": {}}
        
        try:
            logger.info(f"Generating AI rules from {len(sample_entries)} sample entries")
            
            # Get database-enhanced results for better rule generation
            database_results = self._get_database_enhanced_results(sample_entries)
            
            # Get NER results for additional pattern insights
            ner_results = self._get_ner_results(sample_entries)
            
            # Prepare the AI prompt with all strategy results
            prompt = self._generate_ai_rules_prompt(
                sample_entries, ai_results, regex_results, database_results, ner_results
            )
            
            # Make the AI call
            response = self._call_ai_for_rules(prompt)
            
            # Parse the AI response
            rules = self._parse_ai_response(response)
            
            # Check if parsing failed
            if 'error' in rules.get('metadata', {}):
                logger.warning(f"AI rule generation failed: {rules['metadata']['error']}")
                return {
                    "rules": {},
                    "metadata": {
                        "sample_size": len(sample_entries),
                        "ai_model": "gpt-4",
                        "generation_timestamp": self._get_timestamp(),
                        "rule_categories": [],
                        "error": rules['metadata']['error']
                    }
                }
            
            # Validate and enhance the rules with database knowledge
            validated_rules = self._validate_and_enhance_rules_with_database(
                rules, sample_entries, database_results, ner_results
            )
            
            logger.info(f"Successfully generated {len(validated_rules)} rule categories")
            
            return {
                "rules": validated_rules,
                "metadata": {
                    "sample_size": len(sample_entries),
                    "ai_model": "gpt-4",
                    "generation_timestamp": self._get_timestamp(),
                    "rule_categories": list(validated_rules.keys()),
                    "database_enhanced": True,
                    "ner_enhanced": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating AI rules: {str(e)}")
            return {
                "error": str(e), 
                "rules": {},
                "metadata": {
                    "sample_size": len(sample_entries),
                    "ai_model": "gpt-4",
                    "generation_timestamp": self._get_timestamp(),
                    "rule_categories": [],
                    "error": str(e)
                }
            }
    
    def _generate_ai_rules_prompt(self, sample_entries: List[Dict[str, Any]], 
                                 ai_results: List[Dict[str, Any]], 
                                 regex_results: List[Dict[str, Any]],
                                 database_results: List[Dict[str, Any]],
                                 ner_results: List[Dict[str, Any]]) -> str:
        """Generate the AI prompt for rule generation."""
        
        # Prepare sample data for the prompt
        sample_data = []
        for i, entry in enumerate(sample_entries):
            sample_data.append({
                "text": entry.get('text', ''),
                "ai_extraction": ai_results[i] if i < len(ai_results) else {},
                "regex_extraction": regex_results[i] if i < len(regex_results) else {},
                "database_extraction": database_results[i] if i < len(database_results) else {},
                "ner_extraction": ner_results[i] if i < len(ner_results) else {}
            })
        
        prompt = f"""
You are an expert wine list parsing system. Analyze these wine list entries and generate COMPREHENSIVE extraction rules that can parse similar entries WITHOUT needing AI fallback.

SAMPLE ENTRIES AND EXTRACTIONS:
{json.dumps(sample_data, indent=2)}

TASK: Generate EXHAUSTIVE extraction rules that capture ALL patterns in the wine list format.

CRITICAL ANALYSIS REQUIREMENTS:
1. Analyze the EXACT text structure of each entry
2. Identify ALL patterns that distinguish different fields
3. Look for CONSISTENT formatting across entries
4. Find patterns that AI found but regex missed
5. Generate rules that can extract 90%+ of fields without AI
6. INCORPORATE database knowledge for geographic and producer patterns
7. LEVERAGE NER entity recognition for structural patterns
8. CREATE cross-strategy validation rules

FIELD-SPECIFIC PATTERN ANALYSIS:

VINTAGE (CRITICAL):
- Look for 4-digit years (1900-2024) or "NV"
- Check position: beginning, middle, or end of line
- Look for patterns like "Vintage:", "Year:", or standalone years
- Check for context clues (before/after producer, wine name, etc.)
- Generate MULTIPLE patterns to catch all variations

PRICE (CRITICAL):
- Look for currency symbols (£, €, $, ¥)
- Check for numbers at end of line
- Look for price formatting (12.50, £12.50, 12,50€)
- Check for price indicators like "Price:", "£", "€"
- Generate patterns that distinguish from vintage years

PRODUCER_NAME:
- Usually starts with capital letter
- Often followed by wine name or vintage
- Check for common producer patterns
- Look for separators (comma, dash, colon)

WINE_NAME:
- Often in quotes or italics
- Follows producer name
- Check for specific wine terms (Reserve, Grand Cru, etc.)
- Look for grape variety indicators

GRAPE_VARIETY:
- Common grape names (Chardonnay, Cabernet, etc.)
- Check for "grape" or "variety" indicators
- Look for grape lists separated by commas

REGION/COUNTRY:
- Geographic terms
- Check for "from", "of", "in" indicators
- Look for common wine regions
- USE database knowledge for exact region/country matching
- INCORPORATE producer location data from database

DATABASE-ENHANCED PATTERN ANALYSIS:
- Analyze database extraction results for high-confidence patterns
- Use producer location data to validate region/country relationships
- Leverage grape variety database for accurate variety identification
- Create rules that prioritize database matches over regex for geographic fields

NER-ENHANCED PATTERN ANALYSIS:
- Analyze NER entity types (ORG, GPE, PRODUCT, DATE, etc.)
- Use NER confidence scores to validate regex patterns
- Create structural rules based on entity relationships
- Leverage NER context scoring for field disambiguation

CROSS-STRATEGY VALIDATION:
- Create rules that validate regex matches against database knowledge
- Use NER entity types to confirm field classifications
- Generate confidence boosters when multiple strategies agree
- Create fallback hierarchies (Database > NER > Regex > AI)

RULE GENERATION STRATEGY:
Generate MULTIPLE rule types for each field:

1. REGEX PATTERNS (Primary):
   - Exact text patterns with capture groups
   - Multiple variations for each field
   - High confidence patterns (0.9+)

2. POSITIONAL RULES:
   - Field position in text
   - Distance from start/end
   - Relative position to other fields

3. STRUCTURAL RULES:
   - Word order patterns
   - Context clues
   - Separator patterns

4. FORMAT RULES:
   - Capitalization patterns
   - Punctuation patterns
   - Special character patterns

5. VALIDATION RULES:
   - Data type validation
   - Range validation
   - Format validation

6. CONDITIONAL RULES:
   - Context-dependent extraction
   - Field dependencies
   - Exclusion patterns

7. SEQUENCE RULES:
   - Field order relationships
   - Required field sequences
   - Optional field sequences

SPECIFIC PATTERN EXAMPLES TO GENERATE:

VINTAGE PATTERNS:
- r'\\b(19|20)\\d{{2}}\\b' (4-digit years)
- r'\\bNV\\b' (non-vintage)
- r'Vintage:\\s*(\\d{{4}}|NV)' (with label)
- r'(\\d{{4}})\\s*[-–]\\s*' (year followed by dash)

PRICE PATTERNS:
- r'[£€$¥]\\s*(\\d+(?:\\.\\d{{2}})?)' (currency + number)
- r'(\\d+(?:\\.\\d{{2}})?)\\s*[£€$¥]' (number + currency)
- r'(\\d+(?:\\.\\d{{2}})?)\\s*$' (number at end)
- r'Price:\\s*([£€$¥]?\\s*\\d+(?:\\.\\d{{2}})?)' (with label)

PRODUCER PATTERNS:
- r'^([A-Z][A-Za-z\\s&-]+?)(?=\\s+\\d{{4}}|\\s+NV|\\s+\"|\\s+[A-Z]|\\s*$)' (start of line)
- r'([A-Z][A-Za-z\\s&-]+?)\\s*[,:–-]' (followed by separator)

WINE_NAME PATTERNS:
- r'"([^"]+)"' (quoted names)
- r'\\*([^*]+)\\*' (italicized names)
- r'([A-Z][a-z]+\\s+(?:Reserve|Grand\\s+Cru|Premier\\s+Cru))' (specific terms)

RESPONSE FORMAT:
Return ONLY a valid JSON object with this structure:
{{
    "rules": {{
        "vintage": {{
            "regex_patterns": [
                "\\b(19|20)\\d{{2}}\\b",
                "\\bNV\\b",
                "Vintage:\\s*(\\d{{4}}|NV)"
            ],
            "positional_rules": [
                {{"type": "position", "position": "end", "confidence": 0.8}},
                {{"type": "position", "position": "start", "confidence": 0.7}}
            ],
            "structural_rules": [
                {{"type": "structure", "pattern": ["producer", "vintage"], "confidence": 0.9}},
                {{"type": "structure", "pattern": ["vintage", "price"], "confidence": 0.8}}
            ],
            "validation_rules": [
                {{"type": "range", "min": 1900, "max": 2024, "confidence": 0.9}},
                {{"type": "format", "pattern": "^(\\d{{4}}|NV)$", "confidence": 0.8}}
            ]
        }},
        "price": {{
            "regex_patterns": [
                "[£€$¥]\\s*(\\d+(?:\\.\\d{{2}})?)",
                "(\\d+(?:\\.\\d{{2}})?)\\s*[£€$¥]",
                "(\\d+(?:\\.\\d{{2}})?)\\s*$"
            ],
            "positional_rules": [
                {{"type": "position", "position": "end", "confidence": 0.9}}
            ],
            "validation_rules": [
                {{"type": "format", "pattern": "^\\d+(\\.\\d{{2}})?$", "confidence": 0.8}}
            ]
        }},
        "producer_name": {{
            "regex_patterns": [
                "^([A-Z][A-Za-z\\s&-]+?)(?=\\s+\\d{{4}}|\\s+NV|\\s+\"|\\s+[A-Z]|\\s*$)",
                "([A-Z][A-Za-z\\s&-]+?)\\s*[,:–-]"
            ],
            "positional_rules": [
                {{"type": "position", "position": "start", "confidence": 0.8}}
            ],
            "format_rules": [
                {{"type": "capitalization", "pattern": "^[A-Z]", "confidence": 0.9}}
            ]
        }},
        "wine_name": {{
            "regex_patterns": [
                "\"([^\"]+)\"",
                "\\*([^*]+)\\*",
                "([A-Z][a-z]+\\s+(?:Reserve|Grand\\s+Cru|Premier\\s+Cru))"
            ],
            "structural_rules": [
                {{"type": "structure", "pattern": ["producer", "wine_name"], "confidence": 0.8}}
            ]
        }},
        "grape_variety": {{
            "regex_patterns": [
                "\\b(Chardonnay|Cabernet|Merlot|Pinot|Sauvignon|Riesling|Syrah|Nebbiolo|Sangiovese)\\b",
                "Grapes?:\\s*([A-Za-z\\s,]+)"
            ],
            "confidence_threshold": 0.7
        }},
        "region": {{
            "regex_patterns": [
                "\\b(Bordeaux|Burgundy|Champagne|Tuscany|Piedmont|Rioja|Napa|Sonoma|Barossa)\\b",
                "Region:\\s*([A-Za-z\\s]+)"
            ],
            "confidence_threshold": 0.7
        }},
        "country": {{
            "regex_patterns": [
                "\\b(France|Italy|Spain|Germany|USA|Australia|New Zealand|Argentina|Chile)\\b",
                "Country:\\s*([A-Za-z\\s]+)"
            ],
            "confidence_threshold": 0.7
        }}
    }},
    "metadata": {{
        "analysis_summary": "Comprehensive pattern analysis with multiple extraction strategies",
        "confidence_overall": 0.85,
        "recommended_sample_size": 15,
        "rule_coverage": "90%+ field extraction without AI fallback"
    }}
}}

GENERATE RULES THAT:
1. Capture ALL observed patterns in the sample data
2. Include multiple fallback patterns for each field
3. Have high confidence scores (0.8+)
4. Can distinguish between similar fields (vintage vs price)
5. Handle edge cases and variations
6. Provide comprehensive coverage without AI dependency

Focus on creating rules that can extract 90%+ of fields without needing AI fallback.
"""
        
        return prompt
    
    def _call_ai_for_rules(self, prompt: str) -> str:
        """Make the AI call to generate rules."""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert wine list parsing system. Generate precise, actionable extraction rules based on the provided samples."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling AI for rule generation: {str(e)}")
            raise
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured rules."""
        try:
            # Try to extract JSON from the response if it's not pure JSON
            response = response.strip()
            logger.debug(f"Raw AI response: {response[:500]}...")  # Log first 500 chars

            # If response starts with ```json and ends with ```, extract the JSON part
            if response.startswith('```json'):
                response = response[7:]  # Remove ```json
            if response.endswith('```'):
                response = response[:-3]  # Remove ```

            # Try to find JSON in the response (handle cases where AI adds extra text)
            try:
                # First try direct JSON parsing
                parsed = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the response
                import re
                # Look for JSON object pattern
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse JSON from extracted content: {e2}")
                        logger.error(f"Extracted content: {json_match.group()}")
                        raise
                else:
                    logger.error(f"No JSON object found in AI response: {response}")
                    raise

            # Defensive: Ensure parsed is a dict
            if not isinstance(parsed, dict):
                logger.error(f"AI response is not a dict. Raw response: {response}")
                return {
                    'rules': {},
                    'metadata': {
                        'analysis_summary': 'AI response was not a dict',
                        'confidence_overall': 0.0,
                        'recommended_sample_size': 10,
                        'error': 'AI response was not a dict'
                    }
                }

            # Validate structure
            if 'rules' not in parsed:
                logger.warning("AI response missing 'rules' key, creating default structure")
                return {
                    'rules': {},
                    'metadata': {
                        'analysis_summary': 'No rules generated',
                        'confidence_overall': 0.0,
                        'recommended_sample_size': 10
                    }
                }

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.error(f"Raw AI response: {response}")
            # Return a default structure instead of raising an error
            return {
                'rules': {},
                'metadata': {
                    'analysis_summary': f'Failed to parse AI response: {str(e)}',
                    'confidence_overall': 0.0,
                    'recommended_sample_size': 10,
                    'error': str(e)
                }
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            logger.error(f"Raw AI response: {response}")
            return {
                'rules': {},
                'metadata': {
                    'analysis_summary': f'Error parsing response: {str(e)}',
                    'confidence_overall': 0.0,
                    'recommended_sample_size': 10,
                    'error': str(e)
                }
            }
    
    def _validate_and_enhance_rules_with_database(self, rules: Dict[str, Any], 
                                                 sample_entries: List[Dict[str, Any]],
                                                 database_results: List[Dict[str, Any]],
                                                 ner_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and enhance the generated rules with database and NER knowledge."""
        validated_rules = {}
        
        for field_name, field_rules in rules.get('rules', {}).items():
            validated_field_rules = {}
            
            # Validate and enhance regex patterns
            if 'regex_patterns' in field_rules:
                validated_field_rules['regex_patterns'] = self._validate_regex_patterns(
                    field_rules['regex_patterns']
                )
            
            # Validate and enhance positional rules
            if 'positional_rules' in field_rules:
                validated_field_rules['positional_rules'] = self._validate_positional_rules(
                    field_rules['positional_rules']
                )
            
            # Validate and enhance structural rules
            if 'structural_rules' in field_rules:
                validated_field_rules['structural_rules'] = self._validate_structural_rules(
                    field_rules['structural_rules']
                )
            
            # Validate and enhance format rules
            if 'format_rules' in field_rules:
                validated_field_rules['format_rules'] = self._validate_format_rules(
                    field_rules['format_rules']
                )
            
            # Validate and enhance validation rules
            if 'validation_rules' in field_rules:
                validated_field_rules['validation_rules'] = self._validate_validation_rules(
                    field_rules['validation_rules']
                )
            
            # Validate and enhance conditional rules
            if 'conditional_rules' in field_rules:
                validated_field_rules['conditional_rules'] = self._validate_conditional_rules(
                    field_rules['conditional_rules']
                )
            
            # Validate and enhance sequence rules
            if 'sequence_rules' in field_rules:
                validated_field_rules['sequence_rules'] = self._validate_sequence_rules(
                    field_rules['sequence_rules']
                )
            
            # Add database-enhanced validation rules
            validated_field_rules.update(self._add_database_validation_rules(
                field_name, field_rules, database_results
            ))
            
            # Add NER-enhanced validation rules
            validated_field_rules.update(self._add_ner_validation_rules(
                field_name, field_rules, ner_results
            ))
            
            # Add cross-strategy confidence boosters
            validated_field_rules.update(self._add_cross_strategy_boosters(
                field_name, field_rules, database_results, ner_results
            ))
            
            # Add field-specific enhancements
            validated_field_rules.update(self._enhance_field_rules(field_name, field_rules, sample_entries))
            
            validated_rules[field_name] = validated_field_rules
        
        return validated_rules
    
    def _add_database_validation_rules(self, field_name: str, field_rules: Dict[str, Any], 
                                      database_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add database-enhanced validation rules."""
        enhancements = {}
        
        # Add database validation for geographic fields
        if field_name in ['region', 'country', 'sub_region']:
            db_validation_rules = []
            
            # Get all database-extracted regions/countries
            db_regions = set()
            db_countries = set()
            
            for result in database_results:
                if result.get('region'):
                    db_regions.add(result['region'])
                if result.get('country'):
                    db_countries.add(result['country'])
            
            if db_regions:
                db_validation_rules.append({
                    'type': 'database_match',
                    'field': 'region',
                    'valid_values': list(db_regions),
                    'confidence': 0.9,
                    'description': 'Validate against database-extracted regions'
                })
            
            if db_countries:
                db_validation_rules.append({
                    'type': 'database_match',
                    'field': 'country',
                    'valid_values': list(db_countries),
                    'confidence': 0.9,
                    'description': 'Validate against database-extracted countries'
                })
            
            if db_validation_rules:
                enhancements['database_validation_rules'] = db_validation_rules
        
        # Add producer validation
        if field_name == 'producer_name':
            db_producers = set()
            for result in database_results:
                if result.get('producer'):
                    db_producers.add(result['producer'])
            
            if db_producers:
                enhancements['database_validation_rules'] = [{
                    'type': 'database_match',
                    'field': 'producer_name',
                    'valid_values': list(db_producers),
                    'confidence': 0.9,
                    'description': 'Validate against database-extracted producers'
                }]
        
        # Add grape variety validation
        if field_name == 'grape_variety':
            db_grapes = set()
            for result in database_results:
                if result.get('grape_variety'):
                    db_grapes.add(result['grape_variety'])
            
            if db_grapes:
                enhancements['database_validation_rules'] = [{
                    'type': 'database_match',
                    'field': 'grape_variety',
                    'valid_values': list(db_grapes),
                    'confidence': 0.9,
                    'description': 'Validate against database-extracted grape varieties'
                }]
        
        return enhancements
    
    def _add_ner_validation_rules(self, field_name: str, field_rules: Dict[str, Any], 
                                 ner_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add NER-enhanced validation rules."""
        enhancements = {}
        
        # Map field names to NER entity types
        field_to_entity = {
            'producer_name': 'ORG',
            'region': 'GPE',
            'country': 'GPE',
            'wine_name': 'PRODUCT',
            'vintage': 'DATE',
            'price': 'PERCENT'
        }
        
        entity_type = field_to_entity.get(field_name)
        if entity_type:
            # Collect NER-extracted values for this entity type
            ner_values = set()
            for result in ner_results:
                fields = result.get('fields', {})
                for field_key, field_data in fields.items():
                    if isinstance(field_data, dict) and field_data.get('provenance') == 'ner':
                        # Check if this field corresponds to the entity type
                        if field_key == field_name:
                            value = field_data.get('value')
                            if value:
                                ner_values.add(value)
            
            if ner_values:
                enhancements['ner_validation_rules'] = [{
                    'type': 'ner_entity_match',
                    'entity_type': entity_type,
                    'field': field_name,
                    'valid_values': list(ner_values),
                    'confidence': 0.8,
                    'description': f'Validate against NER {entity_type} entities'
                }]
        
        return enhancements
    
    def _add_cross_strategy_boosters(self, field_name: str, field_rules: Dict[str, Any],
                                   database_results: List[Dict[str, Any]], 
                                   ner_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add cross-strategy confidence boosters."""
        enhancements = {}
        
        # Create confidence boosters when multiple strategies agree
        cross_validation_rules = []
        
        # Database + NER agreement boosters
        if field_name in ['producer_name', 'region', 'country', 'grape_variety']:
            cross_validation_rules.append({
                'type': 'cross_strategy_agreement',
                'strategies': ['database', 'ner'],
                'confidence_boost': 0.2,
                'description': 'Boost confidence when database and NER agree'
            })
        
        # Database + Regex agreement boosters
        if field_name in ['region', 'country', 'producer_name']:
            cross_validation_rules.append({
                'type': 'cross_strategy_agreement',
                'strategies': ['database', 'regex'],
                'confidence_boost': 0.15,
                'description': 'Boost confidence when database and regex agree'
            })
        
        # NER + Regex agreement boosters
        cross_validation_rules.append({
            'type': 'cross_strategy_agreement',
            'strategies': ['ner', 'regex'],
            'confidence_boost': 0.1,
            'description': 'Boost confidence when NER and regex agree'
        })
        
        if cross_validation_rules:
            enhancements['cross_strategy_rules'] = cross_validation_rules
        
        return enhancements
    
    def _validate_regex_patterns(self, patterns: List[str]) -> List[str]:
        """Validate regex patterns."""
        validated_patterns = []
        
        for pattern in patterns:
            try:
                import re
                re.compile(pattern)  # Test if pattern compiles
                validated_patterns.append(pattern)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {str(e)}")
        
        return validated_patterns
    
    def _validate_positional_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate positional rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule and rule['type'] == 'position':
                if 'average_position' in rule and 'confidence' in rule:
                    # Ensure confidence is between 0 and 1
                    rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                    validated_rules.append(rule)
        
        return validated_rules
    
    def _validate_structural_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate structural rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule and rule['type'] == 'structure':
                if 'pattern' in rule and 'confidence' in rule:
                    # Ensure pattern is a list of strings
                    if isinstance(rule['pattern'], list):
                        rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                        validated_rules.append(rule)
        
        return validated_rules
    
    def _validate_format_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate format rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule:
                if 'pattern' in rule and 'confidence' in rule:
                    rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                    validated_rules.append(rule)
        
        return validated_rules
    
    def _validate_validation_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate validation rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule:
                if 'confidence' in rule:
                    rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                    validated_rules.append(rule)
        
        return validated_rules
    
    def _validate_conditional_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate conditional rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule and rule['type'] == 'context':
                if 'condition' in rule and 'confidence' in rule:
                    rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                    validated_rules.append(rule)
        
        return validated_rules
    
    def _validate_sequence_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate sequence rules."""
        validated_rules = []
        
        for rule in rules:
            if isinstance(rule, dict) and 'type' in rule and rule['type'] == 'order':
                if 'before' in rule and 'after' in rule and 'confidence' in rule:
                    rule['confidence'] = max(0.0, min(1.0, rule['confidence']))
                    validated_rules.append(rule)
        
        return validated_rules
    
    def _enhance_field_rules(self, field_name: str, field_rules: Dict[str, Any], 
                           sample_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add field-specific enhancements to rules."""
        enhancements = {}
        
        # Add field-specific default patterns if none exist
        if 'regex_patterns' not in field_rules or not field_rules['regex_patterns']:
            enhancements['regex_patterns'] = self._get_default_patterns(field_name)
        
        # Add confidence thresholds
        enhancements['confidence_threshold'] = 0.7
        
        # Add field priority
        enhancements['priority'] = self._get_field_priority(field_name)
        
        return enhancements
    
    def _get_default_patterns(self, field_name: str) -> List[str]:
        """Get default regex patterns for a field."""
        default_patterns = {
            'producer_name': [
                r'(?:^|\s|•\s*)([A-Z][A-Za-z\s\-]+?)(?:\s*[-•]|\s+(?:Las|Los|Le|La|Les)\s+[A-Z]|\s+\d{4})'
            ],
            'vintage': [
                r'(?:^|\s|•\s*)((?:(?:19|20)\d{2}|NV))'
            ],
            'price': [
                # More specific price patterns that avoid vintage conflicts
                r'(?:^|\s|•\s*)(?:£|€|\$)?(\d{2,4})(?:\s*$|\s+[A-Z]|\s*[^\d])',  # Price at end or followed by text
                r'(?:^|\s|•\s*)(?:£|€|\$)?(\d{3,4})(?:\s*$)',  # Price at very end
                r'(?:^|\s|•\s*)(?:£|€|\$)?(\d{2,4})(?:\s*[A-Za-z])',  # Price followed by letters
            ],
            'grape_variety': [
                r'(?:^|\s|•\s*)((?:Chardonnay|Cabernet Sauvignon|Merlot|Pinot Noir|Syrah|Sauvignon Blanc|Riesling))'
            ]
        }
        
        return default_patterns.get(field_name, [])
    
    def _get_field_priority(self, field_name: str) -> int:
        """Get priority for a field (lower number = higher priority)."""
        priorities = {
            'producer_name': 1,
            'wine_name': 2,
            'vintage': 3,
            'price': 4,
            'region': 5,
            'country': 6,
            'grape_variety': 7,
            'designation': 8,
            'type': 9
        }
        
        return priorities.get(field_name, 10)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() 

    def _get_database_enhanced_results(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get database-enhanced extraction results for rule generation."""
        try:
            from app.database_enhanced_rules.database_manager import DatabaseManager
            from app.database_enhanced_rules.early_extractor import EarlyExtractor
            
            db_manager = DatabaseManager()
            early_extractor = EarlyExtractor(db_manager)
            
            database_results = []
            for entry in sample_entries:
                text = entry.get('text', '')
                if text:
                    # Get database extraction
                    db_extraction = early_extractor.extract_wine_info(text)
                    database_results.append(db_extraction)
                else:
                    database_results.append({})
            
            logger.info(f"Generated database-enhanced results for {len(sample_entries)} entries")
            return database_results
            
        except Exception as e:
            logger.warning(f"Error getting database results: {e}")
            return [{} for _ in sample_entries]
    
    def _get_ner_results(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get NER extraction results for rule generation."""
        try:
            from app.fieldextractor.strategies.ner_strategy import NERStrategy
            
            ner_strategy = NERStrategy()
            ner_results = []
            
            for entry in sample_entries:
                text = entry.get('text', '')
                if text:
                    # Get NER extraction
                    ner_fields, ner_confidence = ner_strategy.extract({'text': text})
                    ner_results.append({
                        'fields': ner_fields,
                        'confidence': ner_confidence,
                        'provenance': 'ner'
                    })
                else:
                    ner_results.append({'fields': {}, 'confidence': 0.0})
            
            logger.info(f"Generated NER results for {len(sample_entries)} entries")
            return ner_results
            
        except Exception as e:
            logger.warning(f"Error getting NER results: {e}")
            return [{'fields': {}, 'confidence': 0.0} for _ in sample_entries] 