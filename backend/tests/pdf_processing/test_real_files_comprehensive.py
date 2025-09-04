#!/usr/bin/env python3
"""
Comprehensive test for real PDF files processing pipeline.
Tests all 4 real PDF files and provides detailed analysis of each processing stage.
"""

import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

# Add the parent app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pdf_processing.extractor import PDFExtractor, ExtractionConfig, ExtractionStrategy
from pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
from pdf_processing.metadata import PDFMetadataExtractor
from pdf_processing.categorizer import PDFBlockCategorizer
from pdf_processing.header_associator import HeaderWineAssociator
from pdf_processing.exceptions import PDFProcessingError

class ComprehensivePDFTest:
    """Comprehensive test suite for real PDF files processing."""
    
    def __init__(self):
        self.real_files_dir = Path(__file__).parent.parent / "real-files"
        self.results = {}
        self.start_time = None
        
    def run_comprehensive_test(self):
        """Run comprehensive test on all real PDF files."""
        print("🚀 STARTING COMPREHENSIVE PDF PROCESSING TEST")
        print("=" * 80)
        print(f"📁 Testing files from: {self.real_files_dir}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Get all PDF files
        pdf_files = list(self.real_files_dir.glob("*.pdf"))
        print(f"📄 Found {len(pdf_files)} PDF files to process")
        
        if not pdf_files:
            print("❌ No PDF files found in real-files directory!")
            return
        
        # Process each file
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n{'='*60}")
            print(f"📋 PROCESSING FILE {i}/{len(pdf_files)}: {pdf_file.name}")
            print(f"{'='*60}")
            
            try:
                self.process_single_file(pdf_file)
            except Exception as e:
                print(f"❌ Error processing {pdf_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
        
        # Save results to JSON file
        self.save_results_to_json()
        
    def save_results_to_json(self):
        """Save all test results to a JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"comprehensive_test_results_{timestamp}.json"
        
        # Convert Path objects to strings for JSON serialization
        serializable_results = {}
        for filename, result in self.results.items():
            serializable_results[filename] = result
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    def process_single_file(self, pdf_file: Path):
        """Process a single PDF file through the complete pipeline."""
        file_results = {
            'filename': pdf_file.name,
            'file_size_mb': pdf_file.stat().st_size / (1024 * 1024),
            'stages': {},
            'errors': [],
            'warnings': []
        }
        
        print(f"📊 File size: {file_results['file_size_mb']:.2f} MB")
        
        # Stage 1: PDF Extraction
        print("\n🔍 STAGE 1: PDF EXTRACTION")
        print("-" * 40)
        stage_start = time.time()
        
        try:
            extractor = PDFExtractor()
            extraction_config = ExtractionConfig(
                strategy=ExtractionStrategy.TEXT,
                dpi=300,
                ocr_lang="eng+fra",
                min_confidence=0.5
            )
            
            extracted_data = extractor.extract_text_blocks(str(pdf_file))
            
            stage_time = time.time() - stage_start
            file_results['stages']['extraction'] = {
                'success': True,
                'time_seconds': stage_time,
                'pages_extracted': len(extracted_data),
                'total_text_blocks': sum(len(page) for page in extracted_data),
                'extraction_strategy': extraction_config.strategy.value
            }
            
            print(f"✅ Extraction successful in {stage_time:.2f}s")
            print(f"   📄 Pages extracted: {len(extracted_data)}")
            print(f"   📝 Total text blocks: {sum(len(page) for page in extracted_data)}")
            
        except Exception as e:
            stage_time = time.time() - stage_start
            file_results['stages']['extraction'] = {
                'success': False,
                'time_seconds': stage_time,
                'error': str(e)
            }
            file_results['errors'].append(f"Extraction failed: {e}")
            print(f"❌ Extraction failed in {stage_time:.2f}s: {e}")
            return
        
        # Stage 2: Preprocessing
        print("\n🧹 STAGE 2: PREPROCESSING")
        print("-" * 40)
        stage_start = time.time()
        
        try:
            preprocessor = PDFPreprocessor()
            preprocessing_config = PreprocessingConfig(
                remove_headers=True,
                remove_footers=True,
                normalize_whitespace=True,
                normalize_unicode=True,
                min_line_length=3,
                max_line_length=1000
            )
            
            preprocessed_data = preprocessor.preprocess(extracted_data)
            
            stage_time = time.time() - stage_start
            file_results['stages']['preprocessing'] = {
                'success': True,
                'time_seconds': stage_time,
                'pages_preprocessed': len(preprocessed_data),
                'total_blocks_after': sum(len(page) for page in preprocessed_data),
                'blocks_removed': file_results['stages']['extraction']['total_text_blocks'] - 
                                sum(len(page) for page in preprocessed_data)
            }
            
            print(f"✅ Preprocessing successful in {stage_time:.2f}s")
            print(f"   📄 Pages preprocessed: {len(preprocessed_data)}")
            print(f"   📝 Blocks after preprocessing: {sum(len(page) for page in preprocessed_data)}")
            print(f"   🗑️  Blocks removed: {file_results['stages']['preprocessing']['blocks_removed']}")
            
        except Exception as e:
            stage_time = time.time() - stage_start
            file_results['stages']['preprocessing'] = {
                'success': False,
                'time_seconds': stage_time,
                'error': str(e)
            }
            file_results['errors'].append(f"Preprocessing failed: {e}")
            print(f"❌ Preprocessing failed in {stage_time:.2f}s: {e}")
            return
        
        # Stage 3: Metadata Extraction
        print("\n📋 STAGE 3: METADATA EXTRACTION")
        print("-" * 40)
        stage_start = time.time()
        
        try:
            metadata_extractor = PDFMetadataExtractor()
            metadata = metadata_extractor.extract_metadata(pdf_file)
            
            stage_time = time.time() - stage_start
            file_results['stages']['metadata'] = {
                'success': True,
                'time_seconds': stage_time,
                'title': metadata.get('title', 'N/A'),
                'author': metadata.get('author', 'N/A'),
                'subject': metadata.get('subject', 'N/A'),
                'creator': metadata.get('creator', 'N/A'),
                'producer': metadata.get('producer', 'N/A'),
                'pages': metadata.get('pages', 'N/A')
            }
            
            print(f"✅ Metadata extraction successful in {stage_time:.2f}s")
            print(f"   📖 Title: {metadata.get('title', 'N/A')}")
            print(f"   👤 Author: {metadata.get('author', 'N/A')}")
            print(f"   📄 Pages: {metadata.get('pages', 'N/A')}")
            
        except Exception as e:
            stage_time = time.time() - stage_start
            file_results['stages']['metadata'] = {
                'success': False,
                'time_seconds': stage_time,
                'error': str(e)
            }
            file_results['warnings'].append(f"Metadata extraction failed: {e}")
            print(f"⚠️  Metadata extraction failed in {stage_time:.2f}s: {e}")
        
        # Stage 4: Block Categorization
        print("\n🏷️  STAGE 4: BLOCK CATEGORIZATION")
        print("-" * 40)
        stage_start = time.time()
        
        try:
            categorizer = PDFBlockCategorizer()
            categorized_blocks = categorizer.categorize(preprocessed_data)
            
            stage_time = time.time() - stage_start
            
            # Count categories
            category_counts = {}
            for block in categorized_blocks:
                category = block.get('category', 'unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            file_results['stages']['categorization'] = {
                'success': True,
                'time_seconds': stage_time,
                'total_categorized_blocks': len(categorized_blocks),
                'category_breakdown': category_counts
            }
            
            print(f"✅ Categorization successful in {stage_time:.2f}s")
            print(f"   📊 Total categorized blocks: {len(categorized_blocks)}")
            print(f"   🏷️  Category breakdown:")
            for category, count in category_counts.items():
                print(f"      - {category}: {count}")
            
        except Exception as e:
            stage_time = time.time() - stage_start
            file_results['stages']['categorization'] = {
                'success': False,
                'time_seconds': stage_time,
                'error': str(e)
            }
            file_results['errors'].append(f"Categorization failed: {e}")
            print(f"❌ Categorization failed in {stage_time:.2f}s: {e}")
            return
        
        # Stage 5: Header-Wine Association
        print("\n🔗 STAGE 5: HEADER-WINE ASSOCIATION")
        print("-" * 40)
        stage_start = time.time()
        
        try:
            # Convert categorized blocks to format expected by header associator
            text_blocks = []
            for block in categorized_blocks:
                if 'text' in block:
                    text_blocks.append({
                        'text': block['text'],
                        'bbox': block.get('bbox', [0, 0, 100, 20]),
                        'page': block.get('page', 1),
                        'source': 'text',
                        'confidence': block.get('confidence', 1.0)
                    })
            
            header_associator = HeaderWineAssociator()
            association_result = header_associator.analyze_wine_list_structure(text_blocks)
            
            stage_time = time.time() - stage_start
            
            # Capture all headers and wines with their details
            all_headers = []
            all_wines = []
            
            # Extract all headers
            headers = association_result.get('headers', [])
            for header in headers:
                all_headers.append({
                    'text': header.get('text', 'N/A'),
                    'header_type': header.get('header_type', 'N/A'),
                    'confidence': header.get('confidence', 0.0),
                    'bbox': header.get('bbox', []),
                    'page': header.get('page', 1)
                })
            
            # Extract all wine entries
            wine_entries = association_result.get('wine_entries', [])
            for wine in wine_entries:
                all_wines.append({
                    'text': wine.get('text', 'N/A'),
                    'confidence': wine.get('confidence', 0.0),
                    'bbox': wine.get('bbox', []),
                    'page': wine.get('page', 1),
                    'associated_header': wine.get('associated_header', 'N/A')
                })
            
            file_results['stages']['header_association'] = {
                'success': True,
                'time_seconds': stage_time,
                'headers_identified': len(all_headers),
                'wine_entries_identified': len(all_wines),
                'structure_levels': len(association_result.get('structure', {})) if association_result.get('structure') else 0,
                'all_headers': all_headers,
                'all_wines': all_wines
            }
            
            print(f"✅ Header association successful in {stage_time:.2f}s")
            print(f"   🏷️  Headers identified: {len(all_headers)}")
            print(f"   🍷 Wine entries identified: {len(all_wines)}")
            print(f"   📊 Structure levels: {file_results['stages']['header_association']['structure_levels']}")
            
            # Show all headers
            if all_headers:
                print(f"   📋 All headers:")
                for header in all_headers:
                    print(f"   - {header['text']} ({header['header_type']})")
            
            # Show all wine entries (first 10 to avoid overwhelming output)
            if all_wines:
                print(f"   🍷 Wine entries (showing first 10):")
                for wine in all_wines[:10]:
                    print(f"      - {wine['text']}")
                if len(all_wines) > 10:
                    print(f"      ... and {len(all_wines) - 10} more")
            
        except Exception as e:
            stage_time = time.time() - stage_start
            file_results['stages']['header_association'] = {
                'success': False,
                'time_seconds': stage_time,
                'error': str(e)
            }
            file_results['errors'].append(f"Header association failed: {e}")
            print(f"❌ Header association failed in {stage_time:.2f}s: {e}")
        
        # Calculate total processing time
        total_time = sum(stage.get('time_seconds', 0) for stage in file_results['stages'].values())
        file_results['total_processing_time'] = total_time
        file_results['success'] = all(stage.get('success', False) for stage in file_results['stages'].values())
        
        print(f"\n⏱️  Total processing time: {total_time:.2f}s")
        print(f"✅ Overall success: {'Yes' if file_results['success'] else 'No'}")
        
        # Store results
        self.results[pdf_file.name] = file_results
        
    def generate_comprehensive_report(self):
        """Generate a comprehensive report of all test results."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        # Summary statistics
        total_files = len(self.results)
        successful_files = sum(1 for r in self.results.values() if r['success'])
        failed_files = total_files - successful_files
        
        print(f"📈 SUMMARY STATISTICS:")
        print(f"   📄 Total files processed: {total_files}")
        print(f"   ✅ Successful: {successful_files}")
        print(f"   ❌ Failed: {failed_files}")
        if total_files > 0:
            print(f"   📊 Success rate: {(successful_files/total_files)*100:.1f}%")
        else:
            print(f"   📊 Success rate: N/A (no files processed)")
        
        # Performance analysis
        print(f"\n⚡ PERFORMANCE ANALYSIS:")
        total_time = sum(r.get('total_processing_time', 0) for r in self.results.values())
        avg_time = total_time / total_files if total_files > 0 else 0
        
        print(f"   ⏱️  Total processing time: {total_time:.2f}s")
        print(f"   📊 Average time per file: {avg_time:.2f}s")
        
        # Stage-by-stage analysis
        print(f"\n🔍 STAGE-BY-STAGE ANALYSIS:")
        stages = ['extraction', 'preprocessing', 'metadata', 'categorization', 'header_association']
        
        for stage in stages:
            stage_success = sum(1 for r in self.results.values() 
                              if r['stages'].get(stage, {}).get('success', False))
            stage_time = sum(r['stages'].get(stage, {}).get('time_seconds', 0) 
                           for r in self.results.values())
            
            print(f"   {stage.upper()}:")
            if total_files > 0:
                print(f"      ✅ Success rate: {(stage_success/total_files)*100:.1f}%")
                print(f"      ⏱️  Average time: {stage_time/total_files:.2f}s")
            else:
                print(f"      ✅ Success rate: N/A")
                print(f"      ⏱️  Average time: N/A")
        
        # Detailed file results
        print(f"\n📋 DETAILED FILE RESULTS:")
        for filename, result in self.results.items():
            print(f"\n   📄 {filename}:")
            print(f"      📊 Size: {result['file_size_mb']:.2f} MB")
            print(f"      ⏱️  Processing time: {result.get('total_processing_time', 0):.2f}s")
            print(f"      ✅ Success: {'Yes' if result['success'] else 'No'}")
            
            if result['errors']:
                print(f"      ❌ Errors: {len(result['errors'])}")
                for error in result['errors'][:2]:  # Show first 2 errors
                    print(f"         - {error}")
            
            if result['warnings']:
                print(f"      ⚠️  Warnings: {len(result['warnings'])}")
                for warning in result['warnings'][:2]:  # Show first 2 warnings
                    print(f"         - {warning}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed_files > 0:
            print(f"   ❌ {failed_files} files failed processing - investigate errors")
        
        # Performance recommendations
        slow_stages = []
        if total_files > 0:
            for stage in stages:
                avg_time = sum(r['stages'].get(stage, {}).get('time_seconds', 0) 
                              for r in self.results.values()) / total_files
                if avg_time > 5.0:  # Flag stages taking more than 5 seconds
                    slow_stages.append((stage, avg_time))
        
        if slow_stages:
            print(f"   ⚡ Performance optimization needed for:")
            for stage, avg_time in slow_stages:
                print(f"      - {stage}: {avg_time:.2f}s average")
        
        print(f"\n🎯 TEST COMPLETED AT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

def main():
    """Main test execution function."""
    test_suite = ComprehensivePDFTest()
    test_suite.run_comprehensive_test()

if __name__ == "__main__":
    main()
