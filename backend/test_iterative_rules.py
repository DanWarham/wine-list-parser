#!/usr/bin/env python3
"""
Test script for Iterative Rule Generation

This script tests the iterative rule generation functionality by:
1. Processing a wine list through the hybrid pipeline
2. Checking if failed entries are identified
3. Verifying that improved rules are generated
4. Comparing results before and after iteration
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import required modules
from app.pdf_processing.extractor import PDFExtractor, ExtractionStrategy, ExtractionConfig
from app.pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
from app.pdf_processing.categorizer import PDFBlockCategorizer, CategorizerConfig
from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline

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

def analyze_iterative_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the results of iterative rule generation."""
    metadata = results.get('metadata', {})
    extraction_results = results.get('extraction_results', [])
    
    analysis = {
        'total_entries': len(extraction_results),
        'iterations_performed': metadata.get('iterations_performed', 0),
        'failed_entries_identified': metadata.get('failed_entries_identified', 0),
        'failed_entries_sampled': metadata.get('failed_entries_sampled', 0),
        'rules_improved': metadata.get('rules_improved', False),
        'confidence_improvement': metadata.get('confidence_improvement', 0.0),
        'field_coverage_improvement': metadata.get('field_coverage_improvement', 0.0),
        'original_avg_confidence': metadata.get('original_avg_confidence', 0.0),
        'improved_avg_confidence': metadata.get('improved_avg_confidence', 0.0),
        'original_field_coverage': metadata.get('original_field_coverage', 0.0),
        'improved_field_coverage': metadata.get('improved_field_coverage', 0.0),
        'ai_fallback_count': metadata.get('ai_fallback_count', 0),
        'ai_fallback_rate': metadata.get('ai_fallback_rate', 0.0),
        'average_confidence': metadata.get('average_confidence', 0.0),
        'processing_time_seconds': metadata.get('processing_time_seconds', 0.0)
    }
    
    # Analyze field extraction success
    field_analysis = {}
    for result in extraction_results:
        fields = result.get('fields', {})
        for field_name, field_data in fields.items():
            if field_name not in field_analysis:
                field_analysis[field_name] = {'extracted': 0, 'total': 0}
            
            field_analysis[field_name]['total'] += 1
            if isinstance(field_data, dict):
                value = field_data.get('value')
            else:
                value = field_data
            
            if value and value != 'null' and value != '':
                field_analysis[field_name]['extracted'] += 1
    
    # Calculate field success rates
    for field_name, stats in field_analysis.items():
        if stats['total'] > 0:
            stats['success_rate'] = stats['extracted'] / stats['total']
        else:
            stats['success_rate'] = 0.0
    
    analysis['field_analysis'] = field_analysis
    
    return analysis

def print_iterative_analysis(analysis: Dict[str, Any], filename: str):
    """Print a formatted analysis of iterative rule generation results."""
    print(f"\n{'='*80}")
    print(f"ITERATIVE RULE GENERATION ANALYSIS: {filename}")
    print(f"{'='*80}")
    
    print(f"\n📊 OVERVIEW:")
    print(f"   Total entries processed: {analysis['total_entries']}")
    print(f"   Processing time: {analysis['processing_time_seconds']:.2f} seconds")
    print(f"   AI fallback rate: {analysis['ai_fallback_rate']:.1%}")
    
    print(f"\n🔄 ITERATIVE GENERATION:")
    print(f"   Iterations performed: {analysis['iterations_performed']}")
    print(f"   Failed entries identified: {analysis['failed_entries_identified']}")
    print(f"   Failed entries sampled: {analysis['failed_entries_sampled']}")
    print(f"   Rules improved: {'✅ Yes' if analysis['rules_improved'] else '❌ No'}")
    
    if analysis['rules_improved']:
        print(f"\n📈 IMPROVEMENTS:")
        print(f"   Confidence improvement: {analysis['confidence_improvement']:+.3f}")
        print(f"   Field coverage improvement: {analysis['field_coverage_improvement']:+.3f}")
        print(f"   Original avg confidence: {analysis['original_avg_confidence']:.3f}")
        print(f"   Improved avg confidence: {analysis['improved_avg_confidence']:.3f}")
        print(f"   Original field coverage: {analysis['original_field_coverage']:.1%}")
        print(f"   Improved field coverage: {analysis['improved_field_coverage']:.1%}")
    else:
        print(f"\n📊 CURRENT PERFORMANCE:")
        print(f"   Average confidence: {analysis['average_confidence']:.3f}")
        print(f"   Field coverage: {analysis['field_coverage_improvement']:.1%}")
    
    print(f"\n🎯 FIELD EXTRACTION SUCCESS:")
    field_analysis = analysis.get('field_analysis', {})
    for field_name, stats in field_analysis.items():
        success_rate = stats.get('success_rate', 0.0)
        extracted = stats.get('extracted', 0)
        total = stats.get('total', 0)
        print(f"   {field_name}: {success_rate:.1%} ({extracted}/{total})")
    
    print(f"\n{'='*80}")

def main():
    """Main function to test iterative rule generation."""
    # Test files - Use smaller files for testing
    test_files = [
        "backend/tests/real-files/the-10-cases - Test2.pdf",
        "backend/tests/real-files/Sager & Wilde-Test1.pdf"
    ]
    
    all_analyses = {}
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            continue
            
        print(f"\n{'='*80}")
        print(f"📄 TESTING ITERATIVE RULES: {os.path.basename(test_file)}")
        print(f"{'='*80}")
        
        try:
            # Process PDF to wine blocks
            wine_blocks = process_pdf_to_wine_blocks(test_file)
            
            if not wine_blocks:
                print("❌ No wine blocks found in the PDF")
                continue
            
            # Test with hybrid pipeline (includes iterative generation)
            print(f"\n🔍 Testing hybrid pipeline with iterative generation...")
            pipeline = HybridExtractionPipeline(restaurant_id="test-restaurant")
            results = pipeline.process_wine_list(wine_blocks)
            
            # Analyze results
            analysis = analyze_iterative_results(results)
            print_iterative_analysis(analysis, os.path.basename(test_file))
            
            # Store analysis for comparison
            all_analyses[os.path.basename(test_file)] = analysis
            
        except Exception as e:
            print(f"❌ Error processing {test_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print comparison summary
    if all_analyses:
        print_comparison_summary(all_analyses)
    
    print("\n✅ Iterative rule generation testing completed!")

def print_comparison_summary(all_analyses: Dict[str, Dict[str, Any]]):
    """Print a comparison summary across all files."""
    print(f"\n{'='*80}")
    print("📊 ITERATIVE RULE GENERATION COMPARISON")
    print(f"{'='*80}")
    
    print(f"\n📈 OVERVIEW COMPARISON:")
    print(f"{'File':<50} {'Entries':<8} {'Failed':<8} {'Improved':<10} {'Conf Impr':<10} {'Coverage Impr':<12}")
    print("-" * 100)
    
    for filename, analysis in all_analyses.items():
        failed = analysis['failed_entries_identified']
        improved = "✅ Yes" if analysis['rules_improved'] else "❌ No"
        conf_impr = f"{analysis['confidence_improvement']:+.3f}" if analysis['rules_improved'] else "N/A"
        coverage_impr = f"{analysis['field_coverage_improvement']:+.1%}" if analysis['rules_improved'] else "N/A"
        
        print(f"{filename:<50} {analysis['total_entries']:<8} {failed:<8} {improved:<10} {conf_impr:<10} {coverage_impr:<12}")
    
    print(f"\n🎯 FIELD SUCCESS RATES COMPARISON:")
    all_fields = set()
    for analysis in all_analyses.values():
        all_fields.update(analysis.get('field_analysis', {}).keys())
    
    print(f"{'File':<50}", end="")
    for field in sorted(all_fields):
        print(f" {field:<12}", end="")
    print()
    print("-" * (50 + len(all_fields) * 13))
    
    for filename, analysis in all_analyses.items():
        field_analysis = analysis.get('field_analysis', {})
        print(f"{filename:<50}", end="")
        for field in sorted(all_fields):
            stats = field_analysis.get(field, {})
            success_rate = stats.get('success_rate', 0.0)
            print(f" {success_rate:<11.1%}", end="")
        print()
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main() 