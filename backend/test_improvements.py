#!/usr/bin/env python3
"""
Comprehensive test script to verify all improvements:
1. Refined producer patterns (improve 20.8% success rate)
2. Fixed price accuracy (avoid "202" errors)
3. Proper field mapping (producer_name -> producer, wine_name -> cuvee)
"""

import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database_enhanced_rules.database_manager import DatabaseManager

def test_all_improvements():
    """Test all three improvements comprehensively."""
    
    print("🧪 TESTING ALL IMPROVEMENTS")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Test cases designed to challenge each improvement
    test_cases = [
        # Test Case 1: Producer with "de" (new pattern)
        {
            "text": "2022 Chardonnay | Bourgogne | Domaine de la Romanée-Conti 250",
            "expected": {
                "producer": "Domaine de la Romanée-Conti",
                "producer_name": "Domaine de la Romanée-Conti",
                "vintage": "2022",
                "price": "250",
                "grape_variety": "Chardonnay"
            }
        },
        # Test Case 2: Producer with ampersand (new pattern)
        {
            "text": "2019 Pinot Noir | Burgundy | Louis Jadot & Fils 85",
            "expected": {
                "producer": "Louis Jadot & Fils",
                "producer_name": "Louis Jadot & Fils",
                "vintage": "2019",
                "price": "85",
                "grape_variety": "Pinot Noir"
            }
        },
        # Test Case 3: Wine name with quotes (test field mapping)
        {
            "text": "2017 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49",
            "expected": {
                "producer": "Domaine Bruno Clair",
                "producer_name": "Domaine Bruno Clair",
                "cuvee": "Les Longeroies",
                "wine_name": "Les Longeroies",
                "vintage": "2017",
                "price": "49",
                "grape_variety": "Chardonnay"
            }
        },
        # Test Case 4: Price vs vintage confusion (test price accuracy)
        {
            "text": "2020 Pinot Noir | Burgundy | Remi Rollin 55",
            "expected": {
                "producer": "Remi Rollin",
                "producer_name": "Remi Rollin",
                "vintage": "2020",
                "price": "55",
                "grape_variety": "Pinot Noir"
            }
        },
        # Test Case 5: Multiple word producer (new pattern)
        {
            "text": "2018 Cabernet Sauvignon | Bordeaux | Château Margaux 350",
            "expected": {
                "producer": "Château Margaux",
                "producer_name": "Château Margaux",
                "vintage": "2018",
                "price": "350",
                "grape_variety": "Cabernet Sauvignon"
            }
        },
        # Test Case 6: Complex wine name with designation
        {
            "text": "2015 Pinot Noir 'Grand Cru' | Burgundy | Domaine de la Vougeraie 120",
            "expected": {
                "producer": "Domaine de la Vougeraie",
                "producer_name": "Domaine de la Vougeraie",
                "cuvee": "Grand Cru",
                "wine_name": "Grand Cru",
                "vintage": "2015",
                "price": "120",
                "grape_variety": "Pinot Noir"
            }
        },
        # Test Case 7: Edge case - avoid 202 as price
        {
            "text": "2022 Riesling | Mosel | Dr. Loosen 202",
            "expected": {
                "producer": "Dr. Loosen",
                "producer_name": "Dr. Loosen",
                "vintage": "2022",
                "price": "202",  # This should be price, not vintage
                "grape_variety": "Riesling"
            }
        },
        # Test Case 8: Producer with multiple words and suffix
        {
            "text": "2021 Chardonnay Reserve | California | Kendall Jackson Vintners 45",
            "expected": {
                "producer": "Kendall Jackson Vintners",
                "producer_name": "Kendall Jackson Vintners",
                "cuvee": "Reserve",
                "wine_name": "Reserve",
                "vintage": "2021",
                "price": "45",
                "grape_variety": "Chardonnay"
            }
        }
    ]
    
    success_count = 0
    total_tests = 0
    improvement_results = {
        "producer_extraction": {"success": 0, "total": 0},
        "price_accuracy": {"success": 0, "total": 0},
        "field_mapping": {"success": 0, "total": 0}
    }
    
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
                    
                    # Track improvement categories
                    if field in ['producer', 'producer_name']:
                        improvement_results["producer_extraction"]["success"] += 1
                        improvement_results["producer_extraction"]["total"] += 1
                    elif field == 'price':
                        improvement_results["price_accuracy"]["success"] += 1
                        improvement_results["price_accuracy"]["total"] += 1
                    elif field in ['cuvee', 'wine_name']:
                        improvement_results["field_mapping"]["success"] += 1
                        improvement_results["field_mapping"]["total"] += 1
                        
                else:
                    print(f"   ❌ {field}: Expected '{expected_value}', got '{actual_value}'")
                    test_success = False
                    
                    # Track failures
                    if field in ['producer', 'producer_name']:
                        improvement_results["producer_extraction"]["total"] += 1
                    elif field == 'price':
                        improvement_results["price_accuracy"]["total"] += 1
                    elif field in ['cuvee', 'wine_name']:
                        improvement_results["field_mapping"]["total"] += 1
            else:
                print(f"   ❌ {field}: NOT FOUND")
                test_success = False
                
                # Track failures
                if field in ['producer', 'producer_name']:
                    improvement_results["producer_extraction"]["total"] += 1
                elif field == 'price':
                    improvement_results["price_accuracy"]["total"] += 1
                elif field in ['cuvee', 'wine_name']:
                    improvement_results["field_mapping"]["total"] += 1
        
        if test_success:
            success_count += 1
            print(f"   🎉 Test case {i+1} PASSED")
        else:
            print(f"   💥 Test case {i+1} FAILED")
    
    # Print detailed improvement results
    print(f"\n📊 IMPROVEMENT RESULTS")
    print("=" * 60)
    
    for improvement, stats in improvement_results.items():
        if stats["total"] > 0:
            success_rate = (stats["success"] / stats["total"]) * 100
            print(f"{improvement.replace('_', ' ').title()}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        else:
            print(f"{improvement.replace('_', ' ').title()}: No tests")
    
    print(f"\n📈 OVERALL RESULTS")
    print("=" * 60)
    print(f"Success Rate: {success_count}/{len(test_cases)} test cases passed")
    print(f"Field Accuracy: {success_count * len(test_cases[0]['expected'])}/{total_tests} fields correct")
    
    # Calculate improvement metrics
    producer_success_rate = (improvement_results["producer_extraction"]["success"] / improvement_results["producer_extraction"]["total"] * 100) if improvement_results["producer_extraction"]["total"] > 0 else 0
    price_success_rate = (improvement_results["price_accuracy"]["success"] / improvement_results["price_accuracy"]["total"] * 100) if improvement_results["price_accuracy"]["total"] > 0 else 0
    mapping_success_rate = (improvement_results["field_mapping"]["success"] / improvement_results["field_mapping"]["total"] * 100) if improvement_results["field_mapping"]["total"] > 0 else 0
    
    print(f"\n🎯 IMPROVEMENT METRICS")
    print("=" * 60)
    print(f"Producer Extraction: {producer_success_rate:.1f}% (target: >20.8%)")
    print(f"Price Accuracy: {price_success_rate:.1f}% (target: >53.5%)")
    print(f"Field Mapping: {mapping_success_rate:.1f}% (target: >28.5%)")
    
    # Success criteria
    producer_improved = producer_success_rate > 20.8
    price_improved = price_success_rate > 53.5
    mapping_working = mapping_success_rate > 0
    
    print(f"\n🏆 IMPROVEMENT STATUS")
    print("=" * 60)
    print(f"Producer Patterns: {'✅ IMPROVED' if producer_improved else '❌ NEEDS WORK'}")
    print(f"Price Accuracy: {'✅ IMPROVED' if price_improved else '❌ NEEDS WORK'}")
    print(f"Field Mapping: {'✅ WORKING' if mapping_working else '❌ BROKEN'}")
    
    return producer_improved and price_improved and mapping_working

def main():
    """Main test function."""
    
    success = test_all_improvements()
    
    if success:
        print(f"\n🎉 ALL IMPROVEMENTS SUCCESSFUL!")
        print(f"The system should now show better results for the next upload.")
    else:
        print(f"\n⚠️ Some improvements need further attention.")

if __name__ == "__main__":
    main() 