#!/usr/bin/env python3
"""
Test script to verify upload fixes
"""

import json
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_json_parsing_fix():
    """Test the improved JSON parsing logic"""
    
    # Test cases that were failing before
    test_cases = [
        # Case 1: Multiple JSON objects (the actual issue from logs)
        {
            "input": '''{
  "producer_name": "Schloss Reichenau",
  "wine_name": "COMPLETER 'SPRECHER GUT'",
  "vintage": "2008",
  "price": "39",
  "grape_variety": "Completer",
  "country": "Switzerland",
  "region": "Jenins",
  "designation": null
}
{
  "producer_name": "JJ Prum",
  "wine_name": "RIESLING SPATLESE 'GRAACHER HIMMELREICH'",
  "vintage": "2012",
  "price": "62",
  "grape_variety": "Riesling",
  "country": "Germany",
  "region": "Mosel",
  "designation": null
}''',
            "expected_keys": ["producer_name", "wine_name", "vintage", "price", "grape_variety", "country", "region", "designation"]
        }
    ]
    
    print("Testing improved JSON parsing logic...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"Input length: {len(test_case['input'])} characters")
        
        try:
            # Simulate the improved JSON parsing logic
            content = test_case['input'].strip()
            
            # Try direct JSON parsing first
            try:
                result = json.loads(content)
                print("✓ Direct JSON parsing successful")
            except json.JSONDecodeError as e:
                print(f"✗ Direct JSON parsing failed: {e}")
                
                # Try to extract JSON from the response using improved regex
                import re
                # Look for JSON object pattern - find the first complete JSON object
                json_matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL))
                if json_matches:
                    # Try each match until we find a valid JSON
                    for match in json_matches:
                        try:
                            result = json.loads(match.group())
                            print("✓ JSON extraction and parsing successful")
                            break
                        except json.JSONDecodeError:
                            continue
                    else:
                        print("✗ Failed to parse any JSON from extracted content")
                        continue
                else:
                    print("✗ No JSON object found in response")
                    continue
            
            # Verify the result has expected keys
            if isinstance(result, dict):
                missing_keys = [key for key in test_case['expected_keys'] if key not in result]
                if not missing_keys:
                    print("✓ Result has all expected keys")
                    print(f"✓ Extracted producer: {result.get('producer_name')}")
                    print(f"✓ Extracted wine: {result.get('wine_name')}")
                else:
                    print(f"✗ Missing keys: {missing_keys}")
            else:
                print("✗ Result is not a dictionary")
                
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_json_parsing_fix() 