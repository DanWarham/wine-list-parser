#!/usr/bin/env python3
"""
AI Rule Generator for wine list extraction.
Generates extraction rules based on AI analysis of sample data.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import openai
from app.database_enhanced_rules.database_manager import DatabaseManager
from app.database_enhanced_rules.early_extractor import EarlyExtractor

logger = logging.getLogger(__name__)

class AIRuleGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            # Initialize OpenAI client with new API format
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
        
        self.db_manager = DatabaseManager()
        self.early_extractor = EarlyExtractor()
        
        # Chunking configuration
        self.max_chunk_size = 5  # entries per chunk
        self.max_tokens_per_chunk = 4000  # conservative token limit
        self.max_total_tokens = 16000  # total token limit for all chunks

    def generate_rules(self, sample_entries: List[Dict[str, Any]], 
                      ai_results: List[Dict[str, Any]], 
                      initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI rules from sample entries with chunking support."""
        logger.info(f"Generating AI rules from {len(sample_entries)} sample entries")
        
        if len(sample_entries) <= self.max_chunk_size:
            logger.info("Small sample, using direct processing")
            return self._generate_rules_direct(sample_entries, ai_results, initial_results)
        else:
            logger.info("Large sample, using chunked processing")
            return self._generate_rules_chunked(sample_entries, ai_results, initial_results)

    def _generate_rules_chunked(self, sample_entries: List[Dict[str, Any]], 
                               ai_results: List[Dict[str, Any]], 
                               initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate rules using chunked processing for large samples."""
        try:
            # Estimate total tokens
            total_tokens = self._estimate_tokens(sample_entries)
            logger.info(f"Estimated total tokens: {total_tokens}")
            
            if total_tokens <= self.max_total_tokens:
                # Process in chunks but combine results
                return self._process_chunks_and_combine(sample_entries, ai_results, initial_results)
            else:
                # Process in chunks and summarize
                return self._process_chunks_and_summarize(sample_entries, ai_results, initial_results)
                
        except Exception as e:
            logger.error(f"Error in chunked rule generation: {str(e)}")
            return self._get_fallback_rules()

    def _estimate_tokens(self, sample_entries: List[Dict[str, Any]]) -> int:
        """Estimate token count for sample entries."""
        total_text = ""
        for entry in sample_entries:
            total_text += entry.get('text', '') + " "
        
        # Rough estimation: 1 token ≈ 4 characters
        return len(total_text) // 4

    def _process_chunks_and_combine(self, sample_entries: List[Dict[str, Any]], 
                                   ai_results: List[Dict[str, Any]], 
                                   initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process chunks and combine results."""
        all_rules = {}
        
        # Process in chunks
        for i in range(0, len(sample_entries), self.max_chunk_size):
            chunk = sample_entries[i:i + self.max_chunk_size]
            chunk_ai = ai_results[i:i + self.max_chunk_size] if i < len(ai_results) else []
            chunk_initial = initial_results[i:i + self.max_chunk_size] if i < len(initial_results) else []
            
            logger.info(f"Processing chunk {i//self.max_chunk_size + 1}: {len(chunk)} entries")
            
            try:
                chunk_rules = self._generate_rules_direct(chunk, chunk_ai, chunk_initial)
                if isinstance(chunk_rules, dict) and 'rules' in chunk_rules:
                    # Merge rules from this chunk
                    for field, rules in chunk_rules['rules'].items():
                        if field not in all_rules:
                            all_rules[field] = rules
                        else:
                            # Merge patterns
                            if 'regex_patterns' in rules and 'regex_patterns' in all_rules[field]:
                                all_rules[field]['regex_patterns'].extend(rules['regex_patterns'])
                            if 'structural_rules' in rules and 'structural_rules' in all_rules[field]:
                                all_rules[field]['structural_rules'].extend(rules['structural_rules'])
            except Exception as e:
                logger.error(f"Error processing chunk {i//self.max_chunk_size + 1}: {e}")
                continue
        
        return {
            'rules': all_rules,
            'confidence': 0.8,
            'timestamp': datetime.now().isoformat(),
            'processing_method': 'chunked_combined'
        }

    def _process_chunks_and_summarize(self, sample_entries: List[Dict[str, Any]], 
                                     ai_results: List[Dict[str, Any]], 
                                     initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process chunks and generate summary rules."""
        # Sample from chunks for summary generation
        summary_entries = []
        step = max(1, len(sample_entries) // 10)  # Take 10 representative entries
        
        for i in range(0, len(sample_entries), step):
            summary_entries.append(sample_entries[i])
            if len(summary_entries) >= 10:
                break
        
        logger.info(f"Generating summary rules from {len(summary_entries)} representative entries")
        
        try:
            summary_rules = self._generate_rules_direct(summary_entries, ai_results[:len(summary_entries)], initial_results[:len(summary_entries)])
            if isinstance(summary_rules, dict):
                summary_rules['processing_method'] = 'chunked_summarized'
            return summary_rules
        except Exception as e:
            logger.error(f"Error generating summary rules: {e}")
            return self._get_fallback_rules()

    def _generate_rules_direct(self, sample_entries: List[Dict[str, Any]], 
                              ai_results: List[Dict[str, Any]], 
                              initial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate rules directly for small samples."""
        try:
            # Create database-enhanced results
            database_results = self._generate_database_enhanced_results(sample_entries)
            
            # Create NER results
            ner_results = self._generate_ner_results(sample_entries)
            
            # Prepare the prompt
            prompt = self._create_analysis_prompt(
                sample_entries, ai_results, initial_results, 
                database_results, ner_results
            )
            
            if not self.client:
                logger.warning("No OpenAI client available, using fallback rules")
                return self._get_fallback_rules()
            
            # Call AI with new API format
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            rules = self._parse_ai_response(result_text)
            
            return {
                'rules': rules,
                'confidence': 0.9,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calling AI for rule generation: {str(e)}")
            return self._get_fallback_rules()

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI rule generation."""
        return """You are an expert wine list parser. Your task is to analyze wine list entries and generate reliable extraction rules.

Key principles:
1. Focus on patterns that are consistent and reliable
2. Use regex patterns that can handle variations
3. Set appropriate confidence thresholds
4. Prioritize producer names and wine names
5. Handle common wine list formats

Return only valid JSON with the specified structure."""

    def _create_analysis_prompt(self, sample_entries: List[Dict[str, Any]], 
                               ai_results: List[Dict[str, Any]], 
                               initial_results: List[Dict[str, Any]],
                               database_results: List[Dict[str, Any]],
                               ner_results: List[Dict[str, Any]]) -> str:
        """Create analysis prompt for AI rule generation."""
        
        prompt = f"""
Analyze the following wine list entries and generate extraction rules. Focus on patterns that can be reliably applied to similar entries.

SAMPLE ENTRIES:
"""
        
        for i, entry in enumerate(sample_entries):
            prompt += f"\nEntry {i+1}: {entry.get('text', '')}"
            if i < len(ai_results) and ai_results[i]:
                prompt += f"\nAI Results: {ai_results[i]}"
            if i < len(database_results) and database_results[i]:
                prompt += f"\nDatabase Results: {database_results[i]}"
            prompt += "\n"
        
        prompt += """
Based on these entries, generate JSON-formatted extraction rules with the following structure:

{
  "producer_name": {
    "regex_patterns": ["pattern1", "pattern2"],
    "confidence_threshold": 0.8
  },
  "wine_name": {
    "regex_patterns": ["pattern1", "pattern2"],
    "confidence_threshold": 0.8
  },
  "vintage": {
    "regex_patterns": ["pattern1", "pattern2"],
    "confidence_threshold": 0.9
  },
  "price": {
    "regex_patterns": ["pattern1", "pattern2"],
    "confidence_threshold": 0.9
  },
  "grape_variety": {
    "regex_patterns": ["pattern1", "pattern2"],
    "confidence_threshold": 0.8
  }
}

Focus on:
1. Producer names (often at the end before price)
2. Wine names (often in quotes or after vintage)
3. Vintage years (4-digit years or NV)
4. Prices (numbers at end or with currency symbols)
5. Grape varieties (common wine grapes)

Return only the JSON object, no additional text.
"""
        
        return prompt

    def _generate_database_enhanced_results(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate database-enhanced results for sample entries."""
        results = []
        for entry in sample_entries:
            try:
                text = entry.get('text', '')
                if text:
                    # Use early extractor for database-enhanced extraction
                    extracted = self.early_extractor.extract_fields(text)
                    results.append(extracted)
                else:
                    results.append({})
            except Exception as e:
                logger.error(f"Error in database-enhanced extraction: {e}")
                results.append({})
        
        logger.info(f"Generated database-enhanced results for {len(results)} entries")
        return results

    def _generate_ner_results(self, sample_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate NER results for sample entries."""
        results = []
        for entry in sample_entries:
            try:
                text = entry.get('text', '')
                if text:
                    # Use database manager for NER-like extraction
                    extracted = self.db_manager.extract_fields(text)
                    results.append(extracted)
                else:
                    results.append({})
            except Exception as e:
                logger.error(f"Error in NER extraction: {e}")
                results.append({})
        
        logger.info(f"Generated NER results for {len(results)} entries")
        return results

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to extract rules."""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            # Parse JSON
            rules = json.loads(cleaned_text)
            
            # Validate structure
            if isinstance(rules, dict):
                return rules
            else:
                logger.warning("AI response is not a dictionary")
                return self._get_fallback_rules()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return self._get_fallback_rules()
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._get_fallback_rules()

    def _get_fallback_rules(self) -> Dict[str, Any]:
        """Get fallback rules when AI generation fails."""
        logger.info("Using fallback rules due to AI generation failure")
        
        # Enhanced fallback rules based on common wine list patterns
        fallback_rules = {
            'producer_name': {
                'regex_patterns': [
                    r'\|\s*([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',  # After region separator
                    r'([A-Z][A-Za-z\s&-]+?)\s+(\d+)\s*$',  # Before price
                    r'(Domaine|Château|Maison|Cave|Cantina|Bodega)\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',  # With prefix
                    r'^([A-Z][A-Za-z\s&-]+?)(?=\s+\d{4}|\s+NV|\s+\"|\s+[A-Z]|$)',  # At start
                ],
                'confidence_threshold': 0.7
            },
            'wine_name': {
                'regex_patterns': [
                    r'[\'\"]([^\'\"]+)[\'\"]',  # Quoted names
                    r'(19|20)\d{2}\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\|)',  # After vintage
                    r'([A-Z][A-Za-z\s&-]+?)\s+(Reserve|Grand|Premier|Vieilles|Vignes)',  # With suffixes
                ],
                'confidence_threshold': 0.7
            },
            'vintage': {
                'regex_patterns': [
                    r'\b(19|20)\d{2}\b',  # 4-digit years
                    r'\bNV\b',  # Non-vintage
                    r'(\d{4})\s*[-\u2013]',  # Year followed by dash
                ],
                'confidence_threshold': 0.8
            },
            'price': {
                'regex_patterns': [
                    r'(\d+)\s*$',  # Number at end
                    r'[£€$¥]\s*(\d+(?:\.\d{2})?)',  # Currency symbols
                    r'(\d{2,4})\s*[A-Z]',  # Number followed by letter
                ],
                'confidence_threshold': 0.8
            },
            'grape_variety': {
                'regex_patterns': [
                    r'\b(Chardonnay|Pinot Noir|Cabernet|Merlot|Syrah|Riesling|Sauvignon Blanc)\b',
                    r'\b(Meunier|Nebbiolo|Sangiovese|Verdejo|Albarino)\b',
                ],
                'confidence_threshold': 0.7
            }
        }
        
        logger.info(f"Generated {len(fallback_rules)} fallback rules")
        return fallback_rules 