import os
import json
from typing import List, Dict, Any, Optional
from functools import lru_cache
import openai
from app.config import OPENAI_API_KEY, OPENAI_MODEL, BATCH_SIZE, CACHE_SIZE

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

@lru_cache(maxsize=CACHE_SIZE)
def parse_wine_text(text: str) -> Dict[str, Any]:
    """Parse a single wine text using OpenAI API."""
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": """You are a wine list parser. Extract structured data from wine descriptions.
                Return a JSON object with these fields:
                - producer: The wine producer/winery name
                - cuvee: The wine name/cuvee
                - vintage: The vintage year (or NV/N.V. for non-vintage)
                - price: The price with currency
                - bottle_size: The bottle size (e.g., 750ml, magnum)
                - grape_variety: The grape variety/varieties
                - country: The country of origin
                - region: The wine region
                - subregion: The subregion (if specified)
                - designation: Special designations (e.g., Grand Cru)
                - classification: Wine classification (e.g., AOC, DOCG)
                - sub_type: Sub-type (e.g., Brut, Sec for sparkling)
                - type: The wine type (red, white, rosé, sparkling)
                
                Only include fields that you are confident about. Return null for uncertain fields."""},
                {"role": "user", "content": f"Parse this wine description: {text}"}
            ],
            temperature=0.1,  # Low temperature for consistent outputs
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        # Add confidence scores
        confidence = {}
        for field in result:
            if result[field] is not None:
                confidence[field] = 0.8  # Base confidence for AI-extracted fields
        
        result['field_confidence'] = confidence
        return result
        
    except Exception as e:
        print(f"Error in AI parsing: {str(e)}")
        return {}

def parse_wine_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """Parse a batch of wine texts using OpenAI API."""
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for text in batch:
            result = parse_wine_text(text)
            results.append(result)
    return results

def parse_wine_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse a list of wine entries using AI."""
    # Extract raw text from entries
    texts = [entry.get('raw_text', '') for entry in entries]
    
    # Parse texts using AI
    parsed_results = parse_wine_batch(texts)
    
    # Merge results with original entries
    enriched_entries = []
    for entry, parsed in zip(entries, parsed_results):
        enriched = entry.copy()
        
        # Update fields with AI results if they exist
        for field, value in parsed.items():
            if field != 'field_confidence' and value is not None:
                enriched[field] = value
        
        # Update field confidence
        if 'field_confidence' in parsed:
            if 'field_confidence' not in enriched:
                enriched['field_confidence'] = {}
            enriched['field_confidence'].update(parsed['field_confidence'])
        
        enriched_entries.append(enriched)
    
    return enriched_entries
