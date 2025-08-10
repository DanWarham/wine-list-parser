#!/usr/bin/env python3
"""
Test script for IntelligentSampler diversity analysis

This script processes a PDF file through the extraction pipeline,
runs the IntelligentSampler with the new diversity axes,
and prints a detailed breakdown of the sample diversity.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import required modules
from app.pdf_processing.extractor import PDFExtractor, ExtractionStrategy, ExtractionConfig
from app.pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
from app.pdf_processing.categorizer import PDFBlockCategorizer, CategorizerConfig
from app.rules.intelligent_sampler import IntelligentSampler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_pdf_to_wine_blocks(pdf_path: str) -> List[Dict[str, Any]]:
    """Process a PDF file and extract wine blocks."""
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Initialize components
    extractor = PDFExtractor(ExtractionConfig(strategy=ExtractionStrategy.HYBRID))
    preprocessor = PDFPreprocessor(PreprocessingConfig())
    categorizer = PDFBlockCategorizer(CategorizerConfig())
    
    # Extract text from PDF
    logger.info("Extracting text from PDF...")
    pages, metadata = extractor.extract(pdf_path)
    logger.info(f"Extracted {len(pages)} pages")
    
    # Preprocess text
    logger.info("Preprocessing text...")
    preprocessed_pages = preprocessor.preprocess(pages)
    logger.info(f"Preprocessed {len(preprocessed_pages)} pages")
    
    # Categorize into wine blocks
    logger.info("Categorizing wine blocks...")
    wine_blocks = categorizer.categorize(preprocessed_pages)
    logger.info(f"Found {len(wine_blocks)} wine blocks")
    
    return wine_blocks

def analyze_sampler_diversity(wine_blocks: List[Dict[str, Any]], sample_size: int = 15) -> Dict[str, Any]:
    """Run IntelligentSampler and analyze diversity breakdown."""
    logger.info(f"Running IntelligentSampler with sample size {sample_size}")
    
    # Initialize sampler
    sampler = IntelligentSampler()
    
    # Select sample
    selected_sample = sampler.select_sample(wine_blocks, sample_size)
    
    # Analyze diversity breakdown
    diversity_breakdown = {
        'total_entries': len(wine_blocks),
        'sample_size': len(selected_sample),
        'axes': defaultdict(list),
        'selection_reasons': defaultdict(int),
        'diversity_scores': []
    }
    
    # Categorize by selection reason
    for entry in selected_sample:
        if entry and '_sampling_metadata' in entry:
            reason = entry['_sampling_metadata'].get('selection_reason', 'unknown')
            diversity_breakdown['selection_reasons'][reason] += 1
            diversity_breakdown['diversity_scores'].append(
                entry['_sampling_metadata'].get('diversity_score', 0)
            )
    
    # Analyze by diversity axes
    for entry in selected_sample:
        if entry:
            text = entry.get('text', '')
            
            # Length analysis
            length_cat = sampler._classify_length(text)
            diversity_breakdown['axes']['length'].append(length_cat)
            
            # Delimiter analysis
            delim_cat = sampler._classify_delimiter(text)
            diversity_breakdown['axes']['delimiter'].append(delim_cat)
            
            # Field order analysis
            order_cat = sampler._classify_field_order(text)
            diversity_breakdown['axes']['field_order'].append(order_cat)
            
            # Wine type analysis
            wine_type = sampler._classify_wine_type(text)
            if wine_type:
                diversity_breakdown['axes']['wine_type'].append(wine_type)
            
            # Price analysis
            price = sampler._extract_price(entry)
            if price is not None:
                price_range = sampler._classify_price_range(price)
                diversity_breakdown['axes']['price_range'].append(price_range)
            
            # Region analysis
            region = sampler._identify_region(text)
            if region:
                diversity_breakdown['axes']['region'].append(region)
    
    return diversity_breakdown

def print_diversity_report(breakdown: Dict[str, Any]):
    """Print a formatted diversity breakdown report."""
    print("\n" + "="*80)
    print("INTELLIGENT SAMPLER DIVERSITY ANALYSIS REPORT")
    print("="*80)
    
    print(f"\n📊 OVERVIEW:")
    print(f"   Total entries in file: {breakdown['total_entries']}")
    print(f"   Sample size selected: {breakdown['sample_size']}")
    print(f"   Sampling ratio: {breakdown['sample_size']/breakdown['total_entries']:.1%}")
    
    print(f"\n🎯 SELECTION REASON BREAKDOWN:")
    for reason, count in breakdown['selection_reasons'].items():
        percentage = count / breakdown['sample_size'] * 100
        print(f"   {reason.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n📏 ENTRY LENGTH DIVERSITY:")
    length_counts = defaultdict(int)
    for length_cat in breakdown['axes']['length']:
        length_counts[length_cat] += 1
    for length_cat, count in length_counts.items():
        percentage = count / len(breakdown['axes']['length']) * 100
        print(f"   {length_cat.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n🔤 DELIMITER DIVERSITY:")
    delim_counts = defaultdict(int)
    for delim_cat in breakdown['axes']['delimiter']:
        delim_counts[delim_cat] += 1
    for delim_cat, count in delim_counts.items():
        percentage = count / len(breakdown['axes']['delimiter']) * 100
        print(f"   {delim_cat.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 FIELD ORDER DIVERSITY:")
    order_counts = defaultdict(int)
    for order_cat in breakdown['axes']['field_order']:
        order_counts[order_cat] += 1
    for order_cat, count in order_counts.items():
        percentage = count / len(breakdown['axes']['field_order']) * 100
        print(f"   {order_cat.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n🍷 WINE TYPE DIVERSITY:")
    wine_type_counts = defaultdict(int)
    for wine_type in breakdown['axes']['wine_type']:
        wine_type_counts[wine_type] += 1
    for wine_type, count in wine_type_counts.items():
        percentage = count / len(breakdown['axes']['wine_type']) * 100
        print(f"   {wine_type.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n💰 PRICE RANGE DIVERSITY:")
    price_counts = defaultdict(int)
    for price_range in breakdown['axes']['price_range']:
        price_counts[price_range] += 1
    for price_range, count in price_counts.items():
        percentage = count / len(breakdown['axes']['price_range']) * 100
        print(f"   {price_range.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n🌍 REGIONAL DIVERSITY:")
    region_counts = defaultdict(int)
    for region in breakdown['axes']['region']:
        region_counts[region] += 1
    for region, count in region_counts.items():
        percentage = count / len(breakdown['axes']['region']) * 100
        print(f"   {region.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n📈 DIVERSITY SCORES:")
    if breakdown['diversity_scores']:
        avg_score = sum(breakdown['diversity_scores']) / len(breakdown['diversity_scores'])
        min_score = min(breakdown['diversity_scores'])
        max_score = max(breakdown['diversity_scores'])
        print(f"   Average diversity score: {avg_score:.3f}")
        print(f"   Min diversity score: {min_score:.3f}")
        print(f"   Max diversity score: {max_score:.3f}")
    
    print("\n" + "="*80)

def main():
    """Main function to run the diversity analysis."""
    # Test files - Full real-world files
    test_files = [
        "backend/tests/real-files/Full Files/the-10-cases.pdf",
        "backend/tests/real-files/Full Files/compagnie-des-vins-surnaturels-seven-dials.pdf", 
        "backend/tests/real-files/Full Files/nobleRot_LambsConduit_wine.pdf",
        "backend/tests/real-files/Full Files/Les-110-de-taillevent.pdf"
    ]
    
    all_results = {}
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            continue
            
        print(f"\n{'='*80}")
        print(f"📄 PROCESSING: {os.path.basename(test_file)}")
        print(f"{'='*80}")
        
        try:
            # Process PDF to wine blocks
            wine_blocks = process_pdf_to_wine_blocks(test_file)
            
            if not wine_blocks:
                print("❌ No wine blocks found in the PDF")
                continue
            
            # Test with sample size 15
            sample_size = 15
            print(f"\n🔍 Testing with sample size: {sample_size}")
            breakdown = analyze_sampler_diversity(wine_blocks, sample_size)
            print_diversity_report(breakdown)
            
            # Store results for comparison
            all_results[os.path.basename(test_file)] = breakdown
            
        except Exception as e:
            print(f"❌ Error processing {test_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print comparison summary
    if all_results:
        print_comparison_summary(all_results)
    
    print("\n✅ Diversity analysis completed for all files!")

def print_comparison_summary(all_results: Dict[str, Dict[str, Any]]):
    """Print a comparison summary across all files."""
    print(f"\n{'='*80}")
    print("📊 COMPARISON SUMMARY ACROSS ALL FILES")
    print(f"{'='*80}")
    
    print(f"\n📈 OVERVIEW COMPARISON:")
    print(f"{'File':<50} {'Entries':<8} {'Sample':<8} {'Ratio':<8} {'Avg Score':<10}")
    print("-" * 90)
    
    for filename, breakdown in all_results.items():
        avg_score = sum(breakdown['diversity_scores']) / len(breakdown['diversity_scores']) if breakdown['diversity_scores'] else 0
        ratio = breakdown['sample_size'] / breakdown['total_entries'] * 100
        print(f"{filename:<50} {breakdown['total_entries']:<8} {breakdown['sample_size']:<8} {ratio:<7.1f}% {avg_score:<9.3f}")
    
    print(f"\n🎯 SELECTION REASON COMPARISON:")
    all_reasons = set()
    for breakdown in all_results.values():
        all_reasons.update(breakdown['selection_reasons'].keys())
    
    print(f"{'File':<50}", end="")
    for reason in sorted(all_reasons):
        print(f" {reason.replace('_', ' ').title():<12}", end="")
    print()
    print("-" * (50 + len(all_reasons) * 13))
    
    for filename, breakdown in all_results.items():
        print(f"{filename:<50}", end="")
        for reason in sorted(all_reasons):
            count = breakdown['selection_reasons'].get(reason, 0)
            percentage = count / breakdown['sample_size'] * 100 if breakdown['sample_size'] > 0 else 0
            print(f" {percentage:<11.1f}%", end="")
        print()
    
    print(f"\n📏 LENGTH DIVERSITY COMPARISON:")
    print(f"{'File':<50} {'Short':<8} {'Medium':<8} {'Long':<8}")
    print("-" * 80)
    
    for filename, breakdown in all_results.items():
        length_counts = defaultdict(int)
        for length_cat in breakdown['axes']['length']:
            length_counts[length_cat] += 1
        
        short_pct = length_counts.get('short', 0) / len(breakdown['axes']['length']) * 100
        medium_pct = length_counts.get('medium', 0) / len(breakdown['axes']['length']) * 100
        long_pct = length_counts.get('long', 0) / len(breakdown['axes']['length']) * 100
        
        print(f"{filename:<50} {short_pct:<7.1f}% {medium_pct:<7.1f}% {long_pct:<7.1f}%")
    
    print(f"\n🍷 WINE TYPE DIVERSITY COMPARISON:")
    all_wine_types = set()
    for breakdown in all_results.values():
        all_wine_types.update(breakdown['axes']['wine_type'])
    
    print(f"{'File':<50}", end="")
    for wine_type in sorted(all_wine_types):
        print(f" {wine_type.title():<10}", end="")
    print()
    print("-" * (50 + len(all_wine_types) * 11))
    
    for filename, breakdown in all_results.items():
        wine_type_counts = defaultdict(int)
        for wine_type in breakdown['axes']['wine_type']:
            wine_type_counts[wine_type] += 1
        
        print(f"{filename:<50}", end="")
        for wine_type in sorted(all_wine_types):
            count = wine_type_counts.get(wine_type, 0)
            percentage = count / len(breakdown['axes']['wine_type']) * 100 if breakdown['axes']['wine_type'] else 0
            print(f" {percentage:<9.1f}%", end="")
        print()
    
    print(f"\n💰 PRICE RANGE DIVERSITY COMPARISON:")
    all_price_ranges = set()
    for breakdown in all_results.values():
        all_price_ranges.update(breakdown['axes']['price_range'])
    
    print(f"{'File':<50}", end="")
    for price_range in sorted(all_price_ranges):
        print(f" {price_range.title():<10}", end="")
    print()
    print("-" * (50 + len(all_price_ranges) * 11))
    
    for filename, breakdown in all_results.items():
        price_counts = defaultdict(int)
        for price_range in breakdown['axes']['price_range']:
            price_counts[price_range] += 1
        
        print(f"{filename:<50}", end="")
        for price_range in sorted(all_price_ranges):
            count = price_counts.get(price_range, 0)
            percentage = count / len(breakdown['axes']['price_range']) * 100 if breakdown['axes']['price_range'] else 0
            print(f" {percentage:<9.1f}%", end="")
        print()
    
    print(f"\n🌍 REGIONAL DIVERSITY COMPARISON:")
    all_regions = set()
    for breakdown in all_results.values():
        all_regions.update(breakdown['axes']['region'])
    
    print(f"{'File':<50}", end="")
    for region in sorted(all_regions):
        print(f" {region.title():<12}", end="")
    print()
    print("-" * (50 + len(all_regions) * 13))
    
    for filename, breakdown in all_results.items():
        region_counts = defaultdict(int)
        for region in breakdown['axes']['region']:
            region_counts[region] += 1
        
        print(f"{filename:<50}", end="")
        for region in sorted(all_regions):
            count = region_counts.get(region, 0)
            percentage = count / len(breakdown['axes']['region']) * 100 if breakdown['axes']['region'] else 0
            print(f" {percentage:<11.1f}%", end="")
        print()
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main() 