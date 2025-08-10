#!/usr/bin/env python3
"""
Test script to verify producer and wine name extraction fixes.
"""

import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database_enhanced_rules.database_manager import DatabaseManager

def test_producer_extraction():
    """Test the enhanced producer extraction."""
    
    print("🧪 TESTING PRODUCER AND WINE NAME EXTRACTION FIXES")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Test cases from the uploaded file
    test_cases = [
        {
            "text": "2022 Chardonnay | Bourgogne | Armand Heitz 48",
            "expected": {
                "producer_name": "Armand Heitz",
                "vintage": "2022",
                "price": "48",
                "grape_variety": "Chardonnay"
            }
        },
        {
            "text": "2017 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49",
            "expected": {
                "producer_name": "Domaine Bruno Clair",
                "wine_name": "Les Longeroies",
                "vintage": "2017",
                "price": "49",
                "grape_variety": "Chardonnay"
            }
        },
        {
            "text": "2020 Pinot Noir 'Vieilles Vignes' | Burgundy | Remi Rollin 55",
            "expected": {
                "producer_name": "Remi Rollin",
                "wine_name": "Vieilles Vignes",
                "vintage": "2020",
                "price": "55",
                "grape_variety": "Pinot Noir"
            }
        },
        {
            "text": "NV Champagne Brut | Champagne | Dom Pérignon 250",
            "expected": {
                "producer_name": "Dom Pérignon",
                "vintage": "NV",
                "price": "250",
                "grape_variety": None  # Champagne blend
            }
        }
    ]
    
    success_count = 0
    total_tests = 0
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📝 Test Case {i+1}: {test_case['text']}")
        
        # Extract fields
        result = db.extract_fields({'text': test_case['text']})
        extracted_fields = result[0]
        
        # Check each expected field
        test_success = True
        
        for field, expected_value in test_case['expected'].items():
            if expected_value is None:
                continue
                
            total_tests += 1
            actual_field = extracted_fields.get(field)
            
            if actual_field and isinstance(actual_field, dict):
                actual_value = actual_field.get('value')
                confidence = actual_field.get('confidence', 0)
                provenance = actual_field.get('provenance', 'unknown')
                
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value} (confidence: {confidence:.2f}, provenance: {provenance})")
                else:
                    print(f"   ❌ {field}: Expected '{expected_value}', got '{actual_value}'")
                    test_success = False
            else:
                print(f"   ❌ {field}: NOT FOUND")
                test_success = False
        
        if test_success:
            success_count += 1
            print(f"   🎉 Test case {i+1} PASSED")
        else:
            print(f"   💥 Test case {i+1} FAILED")
    
    print(f"\n📊 RESULTS SUMMARY")
    print(f"   Success Rate: {success_count}/{len(test_cases)} test cases passed")
    print(f"   Field Accuracy: {success_count * len(test_cases[0]['expected'])}/{total_tests} fields correct")
    
    return success_count == len(test_cases)

def test_rule_generation_fix():
    """Test that the OpenAI API fix is working."""
    
    print(f"\n🔧 TESTING RULE GENERATION FIX")
    print("=" * 60)
    
    try:
        from app.rules.ai_rule_generator import AIRuleGenerator
        
        # Test initialization
        ai_generator = AIRuleGenerator()
        print("✅ AI Rule Generator initialized successfully")
        
        # Test with sample data
        sample_entries = [
            {
                "text": "2022 Chardonnay | Bourgogne | Armand Heitz 48",
                "fields": {
                    "vintage": "2022",
                    "grape_variety": "Chardonnay",
                    "region": "Bourgogne",
                    "producer_name": "Armand Heitz",
                    "price": "48"
                }
            }
        ]
        
        ai_results = [{"fields": sample_entries[0]["fields"], "confidence": 0.9}]
        initial_results = [{"fields": {}, "confidence": 0.0}]
        
        # This should not crash with the new API format
        rules = ai_generator.generate_rules(sample_entries, ai_results, initial_results)
        print(f"✅ Rule generation completed: {len(rules) if isinstance(rules, dict) else 0} rules generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Rule generation test failed: {e}")
        return False

def main():
    """Main test function."""
    
    # Test producer extraction fixes
    producer_success = test_producer_extraction()
    
    # Test rule generation fix
    rule_success = test_rule_generation_fix()
    
    print(f"\n🎯 OVERALL RESULTS")
    print("=" * 60)
    print(f"Producer Extraction Fix: {'✅ PASSED' if producer_success else '❌ FAILED'}")
    print(f"Rule Generation Fix: {'✅ PASSED' if rule_success else '❌ FAILED'}")
    
    if producer_success and rule_success:
        print(f"\n🎉 ALL FIXES SUCCESSFUL!")
        print(f"The system should now properly extract producer names and wine names.")
    else:
        print(f"\n⚠️ Some fixes need attention.")

if __name__ == "__main__":
    main() 