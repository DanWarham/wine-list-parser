import os
import json
import openai
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

    def extract(self, block: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Extract fields from a single text block using AI."""
        text = block.get('text', '')
        if not text or not self.api_key:
            return {}, 0.0

        extracted_fields = {}
        confidence = 0.0

        try:
            response = openai.chat.completions.create(
                model=OPENAI_MODEL or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """
CRITICAL: You must respond with ONLY ONE valid JSON object. Do NOT return multiple JSON objects, arrays, or any extra text, explanations, or formatting. Your response must be a single JSON object and nothing else.

IMPORTANT RULES:
1. Producer: The winery/producer name (e.g., 'Chartogne-Taillet', 'Ulysse Collin')
2. Cuvee: The specific wine name in quotes or italics (e.g., 'Hors Serie', 'Les Maillons')
3. Vintage: The year (e.g., '2016', '2019') or 'NV' for non-vintage
4. Price: The numeric price at the end (e.g., '168', '245', '280')
5. Grape Variety: The grape type (e.g., 'Chardonnay', 'Pinot Noir')
6. Region: The wine region (e.g., 'Côtes des Blancs', 'Montagne de Reims')
7. Country: Usually 'France' for French wines, or the specific country
8. Classification: Special designations (e.g., 'Grand Cru', '1er Cru')

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
  "type": "wine type if specified"
}

Only include fields you are confident about. Use null for uncertain fields.
DO NOT add any text before or after the JSON object.
DO NOT return multiple JSON objects or arrays. Return a single JSON object only."""},
                    {"role": "user", "content": f"Parse this wine description: {text}"}
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
                for field_name, value in result.items():
                    if value is not None and value != "":
                        extracted_fields[field_name] = {
                            'value': str(value),
                            'confidence': 0.9,  # High confidence for AI-extracted fields
                            'provenance': 'ai'
                        }
            else:
                logger.error(f"AI response was not a dict: {result}")
                extracted_fields = {}
            confidence = 0.9  # High confidence for AI-extracted fields
            
        except Exception as e:
            logger.error(f"Error in AI extraction: {e}")
            logger.error(f"Input text: {text[:200]}...")  # Log first 200 chars of input
            
            # Return a minimal structure to prevent complete failure
            return {
                'producer_name': {
                    'value': None,
                    'confidence': 0.0,
                    'provenance': 'ai_error_fallback'
                },
                'wine_name': {
                    'value': None,
                    'confidence': 0.0,
                    'provenance': 'ai_error_fallback'
                }
            }, 0.0

        return extracted_fields, confidence

    def extract_batch(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract fields from multiple text blocks using AI."""
        results = []
        for i, block in enumerate(blocks):
            try:
                fields, confidence = self.extract(block)
                # The extract method now returns properly formatted fields
                # Just ensure we have a valid structure
                if not fields:
                    # If no fields were extracted, create a minimal structure
                    fields = {
                        'producer_name': {
                            'value': None,
                            'confidence': 0.0,
                            'provenance': 'ai_no_extraction'
                        }
                    }
                
                results.append(fields)
            except Exception as e:
                logger.error(f"Error processing block {i}: {e}")
                # Add a fallback result for this block
                results.append({
                    'producer_name': {
                        'value': None,
                        'confidence': 0.0,
                        'provenance': 'ai_error'
                    }
                })
        
        return results

    def _parse_response(self, response: str) -> Dict[str, Any]:
        # Parse the response from OpenAI to extract fields
        # This is a placeholder implementation
        return {'producer': 'Unknown', 'vintage': 'Unknown', 'price': 'Unknown'}
