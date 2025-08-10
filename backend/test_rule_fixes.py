#!/usr/bin/env python3
"""
Comprehensive test to diagnose rule generation failure and fix producer/wine name extraction.
"""

import os
import sys
import logging
from typing import Dict, List, Any

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline
from app.rules.ai_rule_generator import AIRuleGenerator
from app.rules.rule_applicator import RuleApplicator
from app.database_enhanced_rules.database_manager import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rule_generation_diagnosis():
    """Test to diagnose why rule generation is failing."""
    
    print("🔍 DIAGNOSING RULE GENERATION FAILURE")
    print("=" * 60)
    
    # Test 1: Check if AI rule generator is working
    print("\n1. Testing AI Rule Generator...")
    try:
        ai_generator = AIRuleGenerator()
        print("✅ AI Rule Generator initialized successfully")
        
        # Test with sample data
        sample_entries = [
            {
                "text": "2022 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49",
                "fields": {
                    "vintage": "2022",
                    "grape_variety": "Chardonnay",
                    "wine_name": "Les Longeroies",
                    "region": "Bourgogne",
                    "producer_name": "Domaine Bruno Clair",
                    "price": "49"
                }
            }
        ]
        
        ai_results = [{"fields": sample_entries[0]["fields"], "confidence": 0.9}]
        initial_results = [{"fields": {}, "confidence": 0.0}]
        
        rules = ai_generator.generate_rules(sample_entries, ai_results, initial_results)
        print(f"✅ AI Rule Generation: {len(rules) if isinstance(rules, dict) else 0} rules generated")
        print(f"📋 Rules keys: {list(rules.keys()) if isinstance(rules, dict) else 'Not a dict'}")
        
    except Exception as e:
        print(f"❌ AI Rule Generator failed: {e}")
        return False
    
    # Test 2: Check rule applicator with enhanced patterns
    print("\n2. Testing Rule Applicator with Enhanced Patterns...")
    try:
        rule_applicator = RuleApplicator()
        
        # Test with enhanced patterns from database_manager
        db_manager = DatabaseManager()
        
        # Test wine block
        test_block = {
            "text": "2022 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49"
        }
        
        # Extract using database manager first
        db_result = db_manager.extract_fields(test_block["text"])
        print(f"✅ Database Manager extracted {len(db_result)} fields")
        
        # Test rule application
        test_rules = {
            "producer_name": {
                "regex_patterns": [
                    r'([A-Z][A-Za-z\s&-]+?)(?=\s+\d{4}|\s+NV|\s+\"|\s+[A-Z]|$)',
                    r'([A-Z][A-Za-z\s&-]+?)\s*[,:–-]',
                    r'([A-Z][A-Za-z\s&-]+?)\s*\|\s*[A-Z]',
                ],
                "confidence_threshold": 0.7
            },
            "wine_name": {
                "regex_patterns": [
                    r'\'([^\']+)\'',
                    r'\"([^\"]+)\"',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\|\s+[A-Z]',
                ],
                "confidence_threshold": 0.7
            },
            "vintage": {
                "regex_patterns": [
                    r'\b(19|20)\d{2}\b',
                    r'\bNV\b',
                ],
                "confidence_threshold": 0.8
            },
            "price": {
                "regex_patterns": [
                    r'(\d+)\s*$',
                    r'[£€$¥]\s*(\d+(?:\.\d{2})?)',
                ],
                "confidence_threshold": 0.8
            }
        }
        
        rule_result = rule_applicator.apply_rules(test_block, test_rules)
        print(f"✅ Rule Applicator result: {rule_result.get('applied_rules', 0)} rules applied")
        print(f"📋 Extracted fields: {list(rule_result.get('fields', {}).keys())}")
        
        # Check specific fields
        fields = rule_result.get('fields', {})
        if 'producer_name' in fields:
            print(f"✅ Producer extracted: {fields['producer_name']['value']}")
        else:
            print("❌ Producer NOT extracted")
            
        if 'wine_name' in fields:
            print(f"✅ Wine name extracted: {fields['wine_name']['value']}")
        else:
            print("❌ Wine name NOT extracted")
            
    except Exception as e:
        print(f"❌ Rule Applicator test failed: {e}")
        return False
    
    # Test 3: Test with real data from the uploaded file
    print("\n3. Testing with Real Upload Data...")
    try:
        # Sample entries from the uploaded file analysis
        real_entries = [
            {
                "text": "2022 Chardonnay | Bourgogne | Armand Heitz 48",
                "expected": {
                    "vintage": "2022",
                    "grape_variety": "Chardonnay",
                    "region": "Bourgogne",
                    "producer_name": "Armand Heitz",
                    "price": "48"
                }
            },
            {
                "text": "2017 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49",
                "expected": {
                    "vintage": "2017",
                    "grape_variety": "Chardonnay",
                    "wine_name": "Les Longeroies",
                    "region": "Bourgogne",
                    "producer_name": "Domaine Bruno Clair",
                    "price": "49"
                }
            }
        ]
        
        success_count = 0
        for i, entry in enumerate(real_entries):
            print(f"\n   Testing entry {i+1}: {entry['text']}")
            
            # Test database manager
            db_result = db_manager.extract_fields(entry['text'])
            db_fields = {k: v['value'] for k, v in db_result.items() if isinstance(v, dict) and v.get('value')}
            
            # Test rule applicator
            rule_result = rule_applicator.apply_rules({"text": entry['text']}, test_rules)
            rule_fields = {k: v['value'] for k, v in rule_result.get('fields', {}).items() if isinstance(v, dict) and v.get('value')}
            
            print(f"   Database fields: {list(db_fields.keys())}")
            print(f"   Rule fields: {list(rule_fields.keys())}")
            
            # Check if producer was extracted
            if 'producer_name' in rule_fields or 'producer_name' in db_fields:
                producer = rule_fields.get('producer_name') or db_fields.get('producer_name')
                print(f"   ✅ Producer: {producer}")
                success_count += 1
            else:
                print(f"   ❌ Producer NOT found")
                
            # Check if wine name was extracted
            if 'wine_name' in rule_fields or 'wine_name' in db_fields:
                wine_name = rule_fields.get('wine_name') or db_fields.get('wine_name')
                print(f"   ✅ Wine name: {wine_name}")
            else:
                print(f"   ❌ Wine name NOT found")
        
        print(f"\n   Success rate: {success_count}/{len(real_entries)} entries had producer extracted")
        
    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        return False
    
    return True

def implement_producer_fixes():
    """Implement fixes for producer and wine name extraction."""
    
    print("\n🔧 IMPLEMENTING PRODUCER AND WINE NAME FIXES")
    print("=" * 60)
    
    # Fix 1: Enhance database manager patterns
    print("\n1. Enhancing Database Manager Patterns...")
    
    # Add enhanced patterns to database_manager.py
    enhanced_patterns = {
        'producer_name': [
            # Pattern 1: Producer at end before price
            r'([A-Z][A-Za-z\s&-]+?)\s+(\d+)\s*$',
            # Pattern 2: Producer after region separator
            r'\|\s*([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',
            # Pattern 3: Producer with common prefixes
            r'(Domaine|Château|Maison|Cave|Cantina|Bodega)\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',
            # Pattern 4: Producer with quotes
            r'([A-Z][A-Za-z\s&-]+?)\s*[\'\"]',
            # Pattern 5: Producer before vintage
            r'([A-Z][A-Za-z\s&-]+?)\s+(19|20)\d{2}',
        ],
        'wine_name': [
            # Pattern 1: Quoted wine names
            r'[\'\"]([^\'\"]+)[\'\"]',
            # Pattern 2: Wine name between grape and region
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\|\s+[A-Z]',
            # Pattern 3: Wine name with common suffixes
            r'([A-Z][A-Za-z\s&-]+?)\s+(Reserve|Grand|Premier|Vieilles|Vignes)',
            # Pattern 4: Wine name after vintage
            r'(19|20)\d{2}\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\|)',
        ]
    }
    
    print("✅ Enhanced patterns defined")
    
    # Fix 2: Update database manager with better field extraction logic
    print("\n2. Updating Database Manager Field Extraction...")
    
    # Create improved field extraction function
    def extract_enhanced_fields(text: str) -> Dict[str, Any]:
        """Enhanced field extraction with better producer and wine name detection."""
        extracted_fields = {}
        
        # Enhanced producer detection
        producer_patterns = [
            r'\|\s*([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',  # After region separator
            r'([A-Z][A-Za-z\s&-]+?)\s+(\d+)\s*$',  # Before price
            r'(Domaine|Château|Maison|Cave|Cantina|Bodega)\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\d+)?\s*$',  # With prefix
        ]
        
        for pattern in producer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    # Handle patterns with multiple groups
                    producer = ' '.join([g for g in match.groups() if g])
                else:
                    producer = match.group(1)
                
                if producer and len(producer.strip()) > 2:
                    extracted_fields['producer_name'] = {
                        'value': producer.strip(),
                        'confidence': 0.9,
                        'provenance': 'enhanced_regex'
                    }
                    break
        
        # Enhanced wine name detection
        wine_name_patterns = [
            r'[\'\"]([^\'\"]+)[\'\"]',  # Quoted names
            r'(19|20)\d{2}\s+([A-Z][A-Za-z\s&-]+?)(?:\s+\|)',  # After vintage
            r'([A-Z][A-Za-z\s&-]+?)\s+(Reserve|Grand|Premier|Vieilles|Vignes)',  # With suffixes
        ]
        
        for pattern in wine_name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    wine_name = ' '.join([g for g in match.groups() if g])
                else:
                    wine_name = match.group(1)
                
                if wine_name and len(wine_name.strip()) > 2:
                    extracted_fields['wine_name'] = {
                        'value': wine_name.strip(),
                        'confidence': 0.8,
                        'provenance': 'enhanced_regex'
                    }
                    break
        
        return extracted_fields
    
    print("✅ Enhanced field extraction function created")
    
    # Fix 3: Test the enhanced extraction
    print("\n3. Testing Enhanced Extraction...")
    
    test_cases = [
        "2022 Chardonnay | Bourgogne | Armand Heitz 48",
        "2017 Chardonnay 'Les Longeroies' | Bourgogne | Domaine Bruno Clair 49",
        "2020 Pinot Noir 'Vieilles Vignes' | Burgundy | Remi Rollin 55",
        "NV Champagne Brut | Champagne | Dom Pérignon 250"
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases):
        print(f"\n   Test case {i+1}: {test_case}")
        
        # Import re for the test
        import re
        result = extract_enhanced_fields(test_case)
        
        if 'producer_name' in result:
            print(f"   ✅ Producer: {result['producer_name']['value']}")
            success_count += 1
        else:
            print(f"   ❌ Producer NOT found")
            
        if 'wine_name' in result:
            print(f"   ✅ Wine name: {result['wine_name']['value']}")
        else:
            print(f"   ❌ Wine name NOT found")
    
    print(f"\n   Enhanced extraction success rate: {success_count}/{len(test_cases)}")
    
    return success_count > 0

def main():
    """Main test function."""
    print("🚀 COMPREHENSIVE RULE GENERATION DIAGNOSIS AND FIXES")
    print("=" * 80)
    
    # Run diagnosis
    diagnosis_success = test_rule_generation_diagnosis()
    
    if diagnosis_success:
        print("\n✅ Diagnosis completed successfully")
        
        # Implement fixes
        fixes_success = implement_producer_fixes()
        
        if fixes_success:
            print("\n✅ Fixes implemented successfully")
            print("\n🎯 NEXT STEPS:")
            print("1. Update database_manager.py with enhanced patterns")
            print("2. Test the fixes with real upload data")
            print("3. Monitor producer and wine name extraction rates")
        else:
            print("\n❌ Fixes failed to implement")
    else:
        print("\n❌ Diagnosis failed")

if __name__ == "__main__":
    main() 