#!/usr/bin/env python3
"""
Detailed Test Script for Iterative Rule Generation

This script provides comprehensive analysis of the iterative rule generation system
by processing the Sager & Wilde-Test1.pdf file and analyzing each step in detail.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import required modules
from app.pdf_processing.extractor import PDFExtractor, ExtractionStrategy, ExtractionConfig
from app.pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
from app.pdf_processing.categorizer import PDFBlockCategorizer, CategorizerConfig
from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

def analyze_extraction_results(results: List[Dict[str, Any]], stage_name: str) -> Dict[str, Any]:
    """Analyze extraction results in detail."""
    analysis = {
        'stage': stage_name,
        'total_entries': len(results),
        'confidence_stats': {
            'min': 1.0,
            'max': 0.0,
            'avg': 0.0,
            'distribution': {'low': 0, 'medium': 0, 'high': 0}
        },
        'field_extraction': {},
        'provenance_breakdown': {},
        'failed_entries': 0,
        'successful_entries': 0
    }
    
    if not results:
        return analysis
    
    confidences = []
    total_fields = 0
    
    for result in results:
        confidence = result.get('confidence', 0.0)
        confidences.append(confidence)
        
        # Count fields
        fields = result.get('fields', {})
        extracted_fields = 0
        for field_name, field_data in fields.items():
            if field_name not in analysis['field_extraction']:
                analysis['field_extraction'][field_name] = {'extracted': 0, 'total': 0}
            
            analysis['field_extraction'][field_name]['total'] += 1
            if isinstance(field_data, dict):
                value = field_data.get('value')
            else:
                value = field_data
            
            if value and value != 'null' and value != '':
                analysis['field_extraction'][field_name]['extracted'] += 1
                extracted_fields += 1
        
        total_fields += extracted_fields
        
        # Track provenance
        provenance = result.get('provenance', 'unknown')
        analysis['provenance_breakdown'][provenance] = analysis['provenance_breakdown'].get(provenance, 0) + 1
        
        # Classify as failed/successful
        if confidence < 0.6 or extracted_fields < 3:
            analysis['failed_entries'] += 1
        else:
            analysis['successful_entries'] += 1
    
    # Calculate confidence statistics
    if confidences:
        analysis['confidence_stats']['min'] = min(confidences)
        analysis['confidence_stats']['max'] = max(confidences)
        analysis['confidence_stats']['avg'] = sum(confidences) / len(confidences)
        
        # Distribution
        for conf in confidences:
            if conf < 0.4:
                analysis['confidence_stats']['distribution']['low'] += 1
            elif conf < 0.7:
                analysis['confidence_stats']['distribution']['medium'] += 1
            else:
                analysis['confidence_stats']['distribution']['high'] += 1
    
    # Calculate field success rates
    for field_name, stats in analysis['field_extraction'].items():
        if stats['total'] > 0:
            stats['success_rate'] = stats['extracted'] / stats['total']
        else:
            stats['success_rate'] = 0.0
    
    analysis['avg_fields_per_entry'] = total_fields / len(results) if results else 0
    
    return analysis

def print_detailed_analysis(analysis: Dict[str, Any]):
    """Print detailed analysis of extraction results."""
    print(f"\n{'='*80}")
    print(f"📊 DETAILED ANALYSIS: {analysis['stage']}")
    print(f"{'='*80}")
    
    print(f"\n📈 OVERVIEW:")
    print(f"   Total entries: {analysis['total_entries']}")
    print(f"   Successful entries: {analysis['successful_entries']} ({analysis['successful_entries']/analysis['total_entries']*100:.1f}%)")
    print(f"   Failed entries: {analysis['failed_entries']} ({analysis['failed_entries']/analysis['total_entries']*100:.1f}%)")
    print(f"   Average fields per entry: {analysis['avg_fields_per_entry']:.2f}")
    
    print(f"\n🎯 CONFIDENCE ANALYSIS:")
    conf_stats = analysis['confidence_stats']
    print(f"   Average confidence: {conf_stats['avg']:.3f}")
    print(f"   Min confidence: {conf_stats['min']:.3f}")
    print(f"   Max confidence: {conf_stats['max']:.3f}")
    print(f"   Distribution:")
    print(f"     Low (<0.4): {conf_stats['distribution']['low']} ({conf_stats['distribution']['low']/analysis['total_entries']*100:.1f}%)")
    print(f"     Medium (0.4-0.7): {conf_stats['distribution']['medium']} ({conf_stats['distribution']['medium']/analysis['total_entries']*100:.1f}%)")
    print(f"     High (>0.7): {conf_stats['distribution']['high']} ({conf_stats['distribution']['high']/analysis['total_entries']*100:.1f}%)")
    
    print(f"\n🔧 PROVENANCE BREAKDOWN:")
    for provenance, count in analysis['provenance_breakdown'].items():
        percentage = count / analysis['total_entries'] * 100
        print(f"   {provenance}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 FIELD EXTRACTION SUCCESS:")
    for field_name, stats in analysis['field_extraction'].items():
        success_rate = stats.get('success_rate', 0.0)
        extracted = stats.get('extracted', 0)
        total = stats.get('total', 0)
        print(f"   {field_name}: {success_rate:.1%} ({extracted}/{total})")
    
    print(f"\n{'='*80}")

def compare_results(before_analysis: Dict[str, Any], after_analysis: Dict[str, Any]):
    """Compare results before and after iterative improvement."""
    print(f"\n{'='*80}")
    print("🔄 ITERATIVE IMPROVEMENT COMPARISON")
    print(f"{'='*80}")
    
    print(f"\n📊 OVERALL IMPROVEMENTS:")
    before_success = before_analysis['successful_entries'] / before_analysis['total_entries'] * 100
    after_success = after_analysis['successful_entries'] / after_analysis['total_entries'] * 100
    success_improvement = after_success - before_success
    
    before_avg_conf = before_analysis['confidence_stats']['avg']
    after_avg_conf = after_analysis['confidence_stats']['avg']
    confidence_improvement = after_avg_conf - before_avg_conf
    
    before_avg_fields = before_analysis['avg_fields_per_entry']
    after_avg_fields = after_analysis['avg_fields_per_entry']
    fields_improvement = after_avg_fields - before_avg_fields
    
    print(f"   Success rate: {before_success:.1f}% → {after_success:.1f}% ({success_improvement:+.1f}%)")
    print(f"   Average confidence: {before_avg_conf:.3f} → {after_avg_conf:.3f} ({confidence_improvement:+.3f})")
    print(f"   Average fields: {before_avg_fields:.2f} → {after_avg_fields:.2f} ({fields_improvement:+.2f})")
    
    print(f"\n📋 FIELD-SPECIFIC IMPROVEMENTS:")
    all_fields = set(before_analysis['field_extraction'].keys()) | set(after_analysis['field_extraction'].keys())
    
    for field_name in sorted(all_fields):
        before_stats = before_analysis['field_extraction'].get(field_name, {})
        after_stats = after_analysis['field_extraction'].get(field_name, {})
        
        before_rate = before_stats.get('success_rate', 0.0)
        after_rate = after_stats.get('success_rate', 0.0)
        improvement = after_rate - before_rate
        
        print(f"   {field_name}: {before_rate:.1%} → {after_rate:.1%} ({improvement:+.1%})")
    
    print(f"\n🎯 CONFIDENCE DISTRIBUTION CHANGES:")
    before_dist = before_analysis['confidence_stats']['distribution']
    after_dist = after_analysis['confidence_stats']['distribution']
    
    for level in ['low', 'medium', 'high']:
        before_count = before_dist.get(level, 0)
        after_count = after_dist.get(level, 0)
        before_pct = before_count / before_analysis['total_entries'] * 100
        after_pct = after_count / after_analysis['total_entries'] * 100
        change = after_pct - before_pct
        
        print(f"   {level.title()}: {before_pct:.1f}% → {after_pct:.1f}% ({change:+.1f}%)")
    
    print(f"\n{'='*80}")

def main():
    """Main function to test iterative rule generation in detail."""
    test_file = "backend/tests/real-files/Sager & Wilde-Test1.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"\n{'='*80}")
    print(f"🧪 DETAILED ITERATIVE RULE GENERATION TEST")
    print(f"📄 File: {os.path.basename(test_file)}")
    print(f"{'='*80}")
    
    try:
        # Process PDF to wine blocks
        wine_blocks = process_pdf_to_wine_blocks(test_file)
        
        if not wine_blocks:
            print("❌ No wine blocks found in the PDF")
            return
        
        print(f"\n📊 Wine blocks extracted: {len(wine_blocks)}")
        print(f"📝 Sample entries:")
        for i, block in enumerate(wine_blocks[:5]):
            text = block.get('text', '')[:100]
            print(f"   {i+1}. {text}...")
        
        # Test with hybrid pipeline (includes iterative generation)
        print(f"\n🚀 Starting hybrid pipeline with iterative generation...")
        start_time = datetime.now()
        
        pipeline = HybridExtractionPipeline(restaurant_id="test-restaurant-detailed")
        results = pipeline.process_wine_list(wine_blocks)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n⏱️ Processing completed in {processing_time:.2f} seconds")
        
        # Analyze results
        extraction_results = results.get('extraction_results', [])
        metadata = results.get('metadata', {})
        
        # Analyze final results
        final_analysis = analyze_extraction_results(extraction_results, "Final Results (After Iteration)")
        print_detailed_analysis(final_analysis)
        
        # Print iteration metadata
        print(f"\n🔄 ITERATION METADATA:")
        iteration_metadata = {
            'iterations_performed': metadata.get('iterations_performed', 0),
            'failed_entries_identified': metadata.get('failed_entries_identified', 0),
            'failed_entries_sampled': metadata.get('failed_entries_sampled', 0),
            'rules_improved': metadata.get('rules_improved', False),
            'confidence_improvement': metadata.get('confidence_improvement', 0.0),
            'field_coverage_improvement': metadata.get('field_coverage_improvement', 0.0),
            'original_avg_confidence': metadata.get('original_avg_confidence', 0.0),
            'improved_avg_confidence': metadata.get('improved_avg_confidence', 0.0),
            'original_field_coverage': metadata.get('original_field_coverage', 0.0),
            'improved_field_coverage': metadata.get('improved_field_coverage', 0.0)
        }
        
        for key, value in iteration_metadata.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.3f}")
            else:
                print(f"   {key}: {value}")
        
        # Overall pipeline statistics
        print(f"\n📈 PIPELINE STATISTICS:")
        print(f"   Total entries: {metadata.get('total_entries', 0)}")
        print(f"   AI fallback count: {metadata.get('ai_fallback_count', 0)}")
        print(f"   AI fallback rate: {metadata.get('ai_fallback_rate', 0):.1%}")
        print(f"   Average confidence: {metadata.get('average_confidence', 0):.3f}")
        print(f"   Processing method: {metadata.get('processing_method', 'unknown')}")
        
        # Save detailed results to file
        output_file = f"iterative_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        detailed_results = {
            'file_processed': os.path.basename(test_file),
            'processing_time_seconds': processing_time,
            'wine_blocks_count': len(wine_blocks),
            'final_analysis': final_analysis,
            'iteration_metadata': iteration_metadata,
            'pipeline_metadata': metadata,
            'sample_extraction_results': extraction_results[:5]  # First 5 results for inspection
        }
        
        with open(output_file, 'w') as f:
            json.dump(detailed_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        print(f"\n✅ Detailed iterative rule generation test completed!")
        
    except Exception as e:
        print(f"❌ Error during detailed test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 