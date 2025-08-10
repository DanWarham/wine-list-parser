import os
import json
import openai
import re
from typing import Dict, Any, Tuple, List
from app.config import OPENAI_API_KEY, OPENAI_MODEL
import logging

logger = logging.getLogger(__name__)

class AIStrategy:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("No OpenAI API key provided - AI strategy will be disabled")

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to handle complex formatting and bullet points.
        This improves AI extraction by normalizing the input.
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
        
        # Add structure markers for better parsing
        text = re.sub(r'(\d{4})\s*•', r'\1 •', text)  # Ensure space before bullet after year
        text = re.sub(r'([A-Z][a-z]+)\s*•', r'\1 •', text)  # Ensure space before bullet after words
        
        return text.strip()

    def _extract_structured_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract fields using pattern recognition before AI processing.
        This provides fallback extraction for common patterns.
        """
        structured_fields = {}
        
        # Enhanced patterns for bullet-point formatted text
        patterns = {
            'producer_name': [
                r'^([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+(?:Las|Los|Le|La|Les)\s+[A-Z]|\s+\d{4})',
                r'•\s*([A-Z][A-Za-z\s\-&\.]+?)(?:\s*[-•]|\s+\d{4})',
                r'([A-Z][A-Za-z\s\-&\.]+?)\s*•\s*[A-Z]'
            ],
            'vintage': [
                r'(?:^|\s|•\s*)((?:19|20)\d{2}|NV)\s*•',
                r'•\s*((?:19|20)\d{2}|NV)',
                r'((?:19|20)\d{2}|NV)\s*[-•]'
            ],
            'price': [
                r'•\s*(\d+(?:\.\d{2})?)\s*$',
                r'(\d+(?:\.\d{2})?)\s*$',
                r'•\s*(\d+(?:\.\d{2})?)\s*[A-Z]'
            ],
            'grape_variety': [
                r'•\s*(Chardonnay|Pinot Noir|Sauvignon Blanc|Riesling|Merlot|Cabernet|Syrah|Nebbiolo|Sangiovese|Savagnin|Chenin|Melon)\s*•',
                r'(Chardonnay|Pinot Noir|Sauvignon Blanc|Riesling|Merlot|Cabernet|Syrah|Nebbiolo|Sangiovese|Savagnin|Chenin|Melon)\s*[-•]'
            ],
            'type': [
                r'•\s*(Brut|Extra-Brut|Sec|Demi-Sec|Doux|NV|Vintage|Magnum|Grand Cru|Premier Cru)\s*•',
                r'(Brut|Extra-Brut|Sec|Demi-Sec|Doux|NV|Vintage|Magnum|Grand Cru|Premier Cru)\s*[-•]'
            ],
            'region': [
                r'•\s*(Champagne|Bordeaux|Burgundy|Jura|Loire|Anjou|Savennières|Muscadet|Côtes|Arbois)\s*•',
                r'(Champagne|Bordeaux|Burgundy|Jura|Loire|Anjou|Savennières|Muscadet|Côtes|Arbois)\s*[-•]'
            ],
            'sub_region': [
                r'•\s*([A-Z][A-Za-z\s]+(?:Côte|Village|Clos|Domaine))\s*•',
                r'([A-Z][A-Za-z\s]+(?:Côte|Village|Clos|Domaine))\s*[-•]'
            ]
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) > 1:  # Avoid single character matches
                        structured_fields[field] = value
                        break
        
        return structured_fields

    def extract(self, block: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Extract fields from a single text block using AI with enhanced preprocessing."""
        text = block.get('text', '')
        if not text or not self.api_key:
            return {}, 0.0

        # Preprocess the text for better AI understanding
        preprocessed_text = self._preprocess_text(text)
        
        # Extract structured fields as fallback
        structured_fields = self._extract_structured_fields(preprocessed_text)
        
        extracted_fields = {}
        confidence = 0.0

        try:
            # Enhanced system prompt for complex text structures
            system_prompt = """
CRITICAL: You must respond with ONLY ONE valid JSON object. Do NOT return multiple JSON objects, arrays, or any extra text, explanations, or formatting. Your response must be a single JSON object and nothing else.

ENHANCED EXTRACTION RULES FOR COMPLEX WINE LIST FORMATS:

1. PRODUCER: Look for winery/producer names, especially at the beginning of lines or after bullet points (•)
   - Examples: 'PIERRE MONTCUIT', 'LA ROGERIE', 'AURÉLIEN SUENEN'
   - Often followed by wine names or regions

2. WINE NAME/CUVEE: Look for specific wine names, often in quotes, italics, or after producer names
   - Examples: 'LES ROBARTS', 'MESNIL SUR OGER', 'LES 3 TERROIRS'
   - May be separated by dashes (-) or bullet points (•)

3. VINTAGE: Look for 4-digit years (2015, 2019, 2020) or 'NV' for non-vintage
   - Often appears before prices or at the end of entries
   - May be followed by bullet points or dashes

4. PRICE: Look for numeric values, usually at the end of entries
   - Examples: '94', '145', '255', '399'
   - May be preceded by bullet points or dashes

5. GRAPE VARIETY: Look for grape names like Chardonnay, Pinot Noir, Savagnin, etc.
   - Often appears in the middle of entries
   - May be followed by vintage or price

6. TYPE: Look for wine types like 'Brut', 'Extra-Brut', 'Grand Cru', 'Magnum'
   - Often appears after grape variety or before vintage

7. REGION: Look for wine regions like 'Champagne', 'Jura', 'Anjou', 'Arbois'
   - May appear as standalone entries or after producer names

8. SUB-REGION: Look for specific areas like 'Cramant', 'Arbois-Pupillin', 'Avize'
   - Often appears after main region names

9. COUNTRY: Usually 'France' for French wines, but check for other countries

10. DESIGNATION: Look for classifications like 'Grand Cru', 'Premier Cru', 'AOC'

SPECIAL HANDLING FOR BULLET POINT FORMATS:
- Bullet points (•) often separate different pieces of information
- Look for patterns like: "Producer • Wine Name • Vintage • Price"
- Some entries may have multiple bullet points separating different wines

Return ONLY a JSON object with these exact field names:
{
  "producer_name": "exact producer name",
  "wine_name": "exact cuvee name", 
  "vintage": "year or NV",
  "price": "numeric price",
  "grape_variety": "grape type",
  "country": "country name",
  "region": "region name",
  "sub_region": "sub-region if specified",
  "designation": "classification if any",
  "type": "wine type if specified",
  "bottle_size": "bottle size if specified"
}

Only include fields you are confident about. Use null for uncertain fields.
DO NOT add any text before or after the JSON object.
DO NOT return multiple JSON objects or arrays. Return a single JSON object only."""

            response = openai.chat.completions.create(
                model=OPENAI_MODEL or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this wine description (note the bullet points and formatting): {preprocessed_text}"}
                ],
                temperature=0.1,
                timeout=30  # 30 second timeout
            )
            
            # Extract and clean the response content
            content = response.choices[0].message.content.strip()
            logger.debug(f"Raw AI response: {content[:500]}...")  # Log first 500 chars
            
            # Try to find JSON in the response (handle cases where AI adds extra text)
            try:
                # First try direct JSON parsing
                result = json.loads(content)
                logger.debug("Direct JSON parsing successful")
            except json.JSONDecodeError as e:
                logger.warning(f"Direct JSON parsing failed: {e}")
                # If that fails, try to extract JSON from the response
                import re
                # Look for JSON object pattern - find the first complete JSON object
                json_matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL))
                if json_matches:
                    # Try each match until we find a valid JSON
                    for match in json_matches:
                        try:
                            result = json.loads(match.group())
                            logger.debug("JSON extraction and parsing successful")
                            break
                        except json.JSONDecodeError:
                            continue
                    else:
                        logger.error(f"Failed to parse any JSON from extracted content")
                        logger.error(f"Content: {content}")
                        return {}, 0.0
                else:
                    logger.error(f"No JSON object found in AI response: {content}")
                    return {}, 0.0

            # Ensure result is a dict and handle None values
            if isinstance(result, dict):
                # Convert raw values to properly formatted field data
                for field, value in result.items():
                    if value is not None and value != "" and value != "null":
                        # Use structured fields as fallback if AI didn't extract something
                        if field not in result or not result[field]:
                            if field in structured_fields:
                                value = structured_fields[field]
                        
                        extracted_fields[field] = {
                            'value': str(value).strip(),
                            'confidence': 0.9,  # High confidence for AI extraction
                            'provenance': 'ai_fallback'
                        }
                
                # Add any structured fields that AI missed
                for field, value in structured_fields.items():
                    if field not in extracted_fields:
                        extracted_fields[field] = {
                            'value': value,
                            'confidence': 0.7,  # Lower confidence for pattern matching
                            'provenance': 'pattern_fallback'
                        }
                
                # Calculate confidence based on number of extracted fields
                confidence = len(extracted_fields) / 11.0  # 11 possible fields
                confidence = min(confidence, 0.95)  # Cap at 95%
                
            else:
                logger.error(f"AI response is not a dictionary: {type(result)}")
                return {}, 0.0
                
        except Exception as e:
            logger.error(f"Error in AI extraction: {e}")
            # Fall back to structured extraction only
            for field, value in structured_fields.items():
                extracted_fields[field] = {
                    'value': value,
                    'confidence': 0.6,  # Lower confidence for fallback
                    'provenance': 'pattern_fallback_only'
                }
            confidence = len(extracted_fields) / 11.0 * 0.6  # Reduced confidence for fallback

        return extracted_fields, confidence

    def extract_batch(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract fields from multiple text blocks using AI."""
        results = []
        
        for i, block in enumerate(blocks):
            try:
                extracted_fields, confidence = self.extract(block)
                
                result = {
                    'block_index': i,
                    'text': block.get('text', ''),
                    'fields': extracted_fields,
                    'confidence': confidence,
                    'provenance': 'ai_fallback'
                }
                
                results.append(result)
                
                # Log progress for large batches
                if (i + 1) % 10 == 0:
                    logger.info(f"AI extraction progress: {i + 1}/{len(blocks)} blocks processed")
                    
            except Exception as e:
                logger.error(f"Error processing block {i}: {e}")
                # Add empty result for failed block
                results.append({
                    'block_index': i,
                    'text': block.get('text', ''),
                    'fields': {},
                    'confidence': 0.0,
                    'provenance': 'ai_fallback_error'
                })
        
        return results

    def _parse_response(self, response: str) -> Dict[str, Any]:
        # Parse the response from OpenAI to extract fields
        # This is a placeholder implementation
        return {}
