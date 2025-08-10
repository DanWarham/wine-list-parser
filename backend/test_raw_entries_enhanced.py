#!/usr/bin/env python3
"""
Test script to extract 20 varied raw entries from the uploaded wine list
and test them with enhanced patterns to verify improvements.
"""

import os
import sys
import json
from typing import Dict, List, Any
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models import WineListFile, WineEntry
from app.database_enhanced_rules.database_manager import DatabaseManager

def extract_varied_raw_entries():
    """Extract 20 varied raw entries from the uploaded wine list."""
    
    db = next(get_db())
    
    # Find the wine list file for "the-10-cases.pdf"
    wine_list = db.query(WineListFile).filter(
        WineListFile.filename == "the-10-cases.pdf"
    ).first()
    
    if not wine_list:
        print("❌ Wine list file 'the-10-cases.pdf' not found in database")
        return []
    
    print(f"✅ Found wine list: {wine_list.filename} (ID: {wine_list.id})")
    
    # Get all wine entries for this file
    wine_entries = db.query(WineEntry).filter(
        WineEntry.wine_list_file_id == wine_list.id
    ).all()
    
    print(f"📊 Found {len(wine_entries)} wine entries in database")
    
    if len(wine_entries) == 0:
        print("❌ No wine entries found in database")
        return []
    
    # Select 20 varied entries (every nth entry to get variety)
    step = max(1, len(wine_entries) // 20)
    selected_entries = []
    
    for i in range(0, len(wine_entries), step):
        if len(selected_entries) >= 20:
            break
        entry = wine_entries[i]
        if entry.raw_text:  # Only include entries with raw text
            selected_entries.append({
                'id': str(entry.id),
                'raw_text': entry.raw_text,
                'producer': entry.producer,
                'cuvee': entry.cuvee,
                'vintage': entry.vintage,
                'price': entry.price,
                'grape_variety': entry.grape_variety,
                'country': entry.country,
                'region': entry.region,
                'confidence': entry.row_confidence
            })
    
    print(f"🎯 Selected {len(selected_entries)} varied entries for testing")
    return selected_entries

def test_enhanced_patterns_on_raw_entries(raw_entries: List[Dict[str, Any]]):
    """Test enhanced patterns on raw entries."""
    
    db_manager = DatabaseManager()
    
    print("\n🧪 Testing Enhanced Patterns on Raw Entries")
    print("=" * 60)
    
    results = {
        'total_entries': len(raw_entries),
        'vintage_extracted': 0,
        'price_extracted': 0,
        'grape_extracted': 0,
        'producer_extracted': 0,
        'region_extracted': 0,
        'country_extracted': 0,
        'entries_with_vintage': 0,
        'entries_with_price': 0,
        'entries_with_grape': 0,
        'detailed_results': []
    }
    
    for i, entry in enumerate(raw_entries, 1):
        raw_text = entry['raw_text']
        
        print(f"\n📝 Entry {i}: {raw_text[:80]}...")
        
        # Test with enhanced patterns
        extracted_fields, confidence = db_manager.extract_fields({'text': raw_text})
        
        # Compare with original extraction
        original_vintage = entry.get('vintage')
        original_price = entry.get('price')
        original_grape = entry.get('grape_variety')
        original_producer = entry.get('producer')
        original_region = entry.get('region')
        original_country = entry.get('country')
        
        # Get enhanced extraction results
        enhanced_vintage = extracted_fields.get('vintage', {}).get('value') if extracted_fields.get('vintage') else None
        enhanced_price = extracted_fields.get('price', {}).get('value') if extracted_fields.get('price') else None
        enhanced_grape = extracted_fields.get('grape_variety', {}).get('value') if extracted_fields.get('grape_variety') else None
        enhanced_producer = extracted_fields.get('producer', {}).get('value') if extracted_fields.get('producer') else None
        enhanced_region = extracted_fields.get('region', {}).get('value') if extracted_fields.get('region') else None
        enhanced_country = extracted_fields.get('country', {}).get('value') if extracted_fields.get('country') else None
        
        # Track results
        if enhanced_vintage:
            results['vintage_extracted'] += 1
        if enhanced_price:
            results['price_extracted'] += 1
        if enhanced_grape:
            results['grape_extracted'] += 1
        if enhanced_producer:
            results['producer_extracted'] += 1
        if enhanced_region:
            results['region_extracted'] += 1
        if enhanced_country:
            results['country_extracted'] += 1
        
        if original_vintage:
            results['entries_with_vintage'] += 1
        if original_price:
            results['entries_with_price'] += 1
        if original_grape:
            results['entries_with_grape'] += 1
        
        # Print comparison
        print(f"  🍷 Vintage: {original_vintage} -> {enhanced_vintage}")
        print(f"  💰 Price: {original_price} -> {enhanced_price}")
        print(f"  🍇 Grape: {original_grape} -> {enhanced_grape}")
        print(f"  🏭 Producer: {original_producer} -> {enhanced_producer}")
        print(f"  🗺️ Region: {original_region} -> {enhanced_region}")
        print(f"  🌍 Country: {original_country} -> {enhanced_country}")
        print(f"  🎯 Confidence: {confidence:.2f}")
        
        # Store detailed result
        results['detailed_results'].append({
            'entry_id': entry['id'],
            'raw_text': raw_text,
            'original': {
                'vintage': original_vintage,
                'price': original_price,
                'grape_variety': original_grape,
                'producer': original_producer,
                'region': original_region,
                'country': original_country
            },
            'enhanced': {
                'vintage': enhanced_vintage,
                'price': enhanced_price,
                'grape_variety': enhanced_grape,
                'producer': enhanced_producer,
                'region': enhanced_region,
                'country': enhanced_country
            },
            'confidence': confidence
        })
    
    return results

def analyze_improvements(results: Dict[str, Any]):
    """Analyze the improvements from enhanced patterns."""
    
    print("\n📊 IMPROVEMENT ANALYSIS")
    print("=" * 60)
    
    total_entries = results['total_entries']
    
    # Calculate extraction rates
    vintage_rate = (results['vintage_extracted'] / total_entries) * 100
    price_rate = (results['price_extracted'] / total_entries) * 100
    grape_rate = (results['grape_extracted'] / total_entries) * 100
    producer_rate = (results['producer_extracted'] / total_entries) * 100
    region_rate = (results['region_extracted'] / total_entries) * 100
    country_rate = (results['country_extracted'] / total_entries) * 100
    
    print(f"📈 ENHANCED PATTERN EXTRACTION RATES:")
    print(f"  🍷 Vintage: {results['vintage_extracted']}/{total_entries} ({vintage_rate:.1f}%)")
    print(f"  💰 Price: {results['price_extracted']}/{total_entries} ({price_rate:.1f}%)")
    print(f"  🍇 Grape Variety: {results['grape_extracted']}/{total_entries} ({grape_rate:.1f}%)")
    print(f"  🏭 Producer: {results['producer_extracted']}/{total_entries} ({producer_rate:.1f}%)")
    print(f"  🗺️ Region: {results['region_extracted']}/{total_entries} ({region_rate:.1f}%)")
    print(f"  🌍 Country: {results['country_extracted']}/{total_entries} ({country_rate:.1f}%)")
    
    # Compare with original analysis
    print(f"\n📊 COMPARISON WITH ORIGINAL ANALYSIS:")
    print(f"  🍷 Vintage: 7.9% (original) -> {vintage_rate:.1f}% (enhanced)")
    print(f"  💰 Price: 7.9% (original) -> {price_rate:.1f}% (enhanced)")
    print(f"  🍇 Grape Variety: 7.9% (original) -> {grape_rate:.1f}% (enhanced)")
    
    # Calculate improvements
    vintage_improvement = vintage_rate - 7.9
    price_improvement = price_rate - 7.9
    grape_improvement = grape_rate - 7.9
    
    print(f"\n🚀 IMPROVEMENTS:")
    print(f"  🍷 Vintage: +{vintage_improvement:.1f} percentage points")
    print(f"  💰 Price: +{price_improvement:.1f} percentage points")
    print(f"  🍇 Grape Variety: +{grape_improvement:.1f} percentage points")
    
    # Analyze specific improvements
    print(f"\n🎯 DETAILED IMPROVEMENTS:")
    
    vintage_improvements = 0
    price_improvements = 0
    grape_improvements = 0
    
    for result in results['detailed_results']:
        original = result['original']
        enhanced = result['enhanced']
        
        # Check if enhanced extraction found something that original didn't
        if not original['vintage'] and enhanced['vintage']:
            vintage_improvements += 1
        if not original['price'] and enhanced['price']:
            price_improvements += 1
        if not original['grape_variety'] and enhanced['grape_variety']:
            grape_improvements += 1
    
    print(f"  🍷 New vintage extractions: {vintage_improvements}")
    print(f"  💰 New price extractions: {price_improvements}")
    print(f"  🍇 New grape variety extractions: {grape_improvements}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"enhanced_pattern_test_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📁 Detailed results saved to: {output_file}")
    
    return {
        'vintage_rate': vintage_rate,
        'price_rate': price_rate,
        'grape_rate': grape_rate,
        'vintage_improvement': vintage_improvement,
        'price_improvement': price_improvement,
        'grape_improvement': grape_improvement
    }

def main():
    """Main function to test enhanced patterns on raw entries."""
    
    print("🎯 Testing Enhanced Patterns on Raw Wine List Entries")
    print("=" * 60)
    
    # Extract raw entries
    raw_entries = extract_varied_raw_entries()
    
    if not raw_entries:
        print("❌ No raw entries found for testing")
        return
    
    # Test enhanced patterns
    results = test_enhanced_patterns_on_raw_entries(raw_entries)
    
    # Analyze improvements
    improvements = analyze_improvements(results)
    
    print(f"\n✅ Enhanced Pattern Testing Complete!")
    print(f"📊 Overall improvement: {improvements['vintage_improvement'] + improvements['price_improvement'] + improvements['grape_improvement']:.1f} percentage points")

if __name__ == "__main__":
    main() 