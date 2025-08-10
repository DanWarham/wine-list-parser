#!/usr/bin/env python3
"""
Test script to verify enhanced price detection and vintage recognition patterns.
"""

import os
import sys
import re
from typing import Dict, List, Any

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database_enhanced_rules.database_manager import DatabaseManager

def test_enhanced_patterns():
    """Test the enhanced price and vintage patterns."""
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Test cases for vintage recognition
    vintage_test_cases = [
        "2021 Chardonnay Reserve",
        "NV Champagne Brut",
        "2019-2020 Pinot Noir",
        "2018 | Bordeaux | Château Margaux",
        "2020A Cabernet Sauvignon",
        "Vintage: 2017",
        "Year: NV",
        "2019£45",
        "2020 750ml",
        "2018 Château Lafite",
        "2025 Pinot Noir",  # Should be rejected (too recent)
        "123 Chardonnay",   # Should be rejected (too small for vintage)
    ]
    
    # Test cases for price recognition
    price_test_cases = [
        "Chardonnay Reserve 45",
        "Pinot Noir | Producer | 67",
        "£45 Chardonnay",
        "Chardonnay €45",
        "Pinot Noir 123",
        "Price: £45",
        "Chardonnay 45A",
        "Pinot Noir 45|",
        "Chardonnay 45-",
        "Pinot Noir 45Château",
        "Chardonnay 45FRANCE",
        "2021 Chardonnay 45",  # Should extract both vintage and price
    ]
    
    print("🧪 Testing Enhanced Pattern Recognition")
    print("=" * 50)
    
    print("\n📅 VINTAGE RECOGNITION TESTS:")
    print("-" * 30)
    
    for i, test_case in enumerate(vintage_test_cases, 1):
        result, confidence = db_manager.extract_fields({'text': test_case})
        vintage = result.get('vintage', {}).get('value') if result.get('vintage') else None
        print(f"{i:2d}. '{test_case}' -> Vintage: {vintage} (conf: {confidence:.2f})")
    
    print("\n💰 PRICE RECOGNITION TESTS:")
    print("-" * 30)
    
    for i, test_case in enumerate(price_test_cases, 1):
        result, confidence = db_manager.extract_fields({'text': test_case})
        price = result.get('price', {}).get('value') if result.get('price') else None
        vintage = result.get('vintage', {}).get('value') if result.get('vintage') else None
        print(f"{i:2d}. '{test_case}' -> Price: {price}, Vintage: {vintage} (conf: {confidence:.2f})")
    
    print("\n🎯 DISAMBIGUATION TESTS:")
    print("-" * 30)
    
    # Test cases that could be ambiguous
    ambiguous_test_cases = [
        "2021 Chardonnay 45",      # Should be vintage 2021, price 45
        "NV Champagne 67",         # Should be vintage NV, price 67
        "2019 Pinot Noir 123",     # Should be vintage 2019, price 123
        "2020 Cabernet 89",        # Should be vintage 2020, price 89
        "123 Chardonnay 45",       # Should be price 123, no vintage (123 too small)
        "2025 Pinot Noir 67",      # Should be price 67, no vintage (2025 too recent)
    ]
    
    for i, test_case in enumerate(ambiguous_test_cases, 1):
        result, confidence = db_manager.extract_fields({'text': test_case})
        price = result.get('price', {}).get('value') if result.get('price') else None
        vintage = result.get('vintage', {}).get('value') if result.get('vintage') else None
        print(f"{i:2d}. '{test_case}' -> Vintage: {vintage}, Price: {price} (conf: {confidence:.2f})")
    
    print("\n📊 PATTERN ANALYSIS:")
    print("-" * 30)
    
    # Analyze pattern effectiveness
    vintage_success = 0
    price_success = 0
    total_vintage_tests = len(vintage_test_cases)
    total_price_tests = len(price_test_cases)
    
    for test_case in vintage_test_cases:
        result, _ = db_manager.extract_fields({'text': test_case})
        if result.get('vintage'):
            vintage_success += 1
    
    for test_case in price_test_cases:
        result, _ = db_manager.extract_fields({'text': test_case})
        if result.get('price'):
            price_success += 1
    
    vintage_rate = (vintage_success / total_vintage_tests) * 100
    price_rate = (price_success / total_price_tests) * 100
    
    print(f"Vintage Recognition Rate: {vintage_success}/{total_vintage_tests} ({vintage_rate:.1f}%)")
    print(f"Price Recognition Rate: {price_success}/{total_price_tests} ({price_rate:.1f}%)")
    
    # Test grape variety matching
    print("\n🍇 GRAPE VARIETY MATCHING TEST:")
    print("-" * 30)
    
    grape_test_cases = [
        "Chardonnay Reserve",
        "Pinot Noir | Producer",
        "Cabernet Sauvignon 2021",
        "Merlot | Region | Producer",
        "Syrah Reserve",
        "Riesling | Germany",
        "Sauvignon Blanc | New Zealand",
        "Nebbiolo | Italy",
        "Sangiovese | Tuscany",
        "Verdejo | Spain",  # Should match from database
        "Albarino | Spain",  # Should match from database
        "Loureiro | Portugal",  # Should match from database
    ]
    
    grape_success = 0
    for test_case in grape_test_cases:
        result, _ = db_manager.extract_fields({'text': test_case})
        grape = result.get('grape_variety', {}).get('value') if result.get('grape_variety') else None
        print(f"'{test_case}' -> Grape: {grape}")
        if grape:
            grape_success += 1
    
    grape_rate = (grape_success / len(grape_test_cases)) * 100
    print(f"\nGrape Variety Recognition Rate: {grape_success}/{len(grape_test_cases)} ({grape_rate:.1f}%)")
    
    print("\n✅ Enhanced Pattern Testing Complete!")

if __name__ == "__main__":
    test_enhanced_patterns() 