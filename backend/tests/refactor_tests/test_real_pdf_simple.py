#!/usr/bin/env python3
"""
Simple test for database integration with real PDF file.
"""

import sys
import os
import logging
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_real_pdf_simple():
    """Test database integration with real PDF file."""
    
    # Test file path
    test_file = Path(__file__).parent.parent / "real-files" / "compagnie-des-vins-surnaturels-seven-dials-pages.pdf"
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False
    
    logger.info(f"🧪 Testing database integration with REAL PDF: {test_file.name}")
    logger.info(f"📁 File size: {test_file.stat().st_size / 1024:.1f} KB")
    logger.info("="*80)
    
    try:
        # Step 1: Extract text from PDF
        logger.info("STEP 1: Extracting text from PDF")
        logger.info("-" * 50)
        
        from app.pdf_processing.extractor import PDFExtractor
        text_extractor = PDFExtractor()
        text_blocks = text_extractor.extract_text_blocks(str(test_file))
        logger.info(f"✅ Extracted {len(text_blocks)} text blocks from PDF")
        
        # Show the structure of the data
        logger.info("📄 Data structure analysis:")
        if text_blocks:
            logger.info(f"  First block type: {type(text_blocks[0])}")
            logger.info(f"  First block content: {str(text_blocks[0])[:200]}...")
        
        # Step 2: Process the text blocks to extract wine entries
        logger.info("\nSTEP 2: Processing text blocks for wine entries")
        logger.info("-" * 50)
        
        # Convert the complex structure to simple text blocks
        wine_entries = []
        
        for i, block in enumerate(text_blocks):
            if isinstance(block, list):
                # This is a list of text elements
                for j, element in enumerate(block):
                    if isinstance(element, dict) and 'text' in element:
                        text = element['text'].strip()
                        if text and len(text) > 10:  # Filter out very short text
                            wine_entries.append({
                                'text': text,
                                'page': element.get('page', i),
                                'bbox': element.get('bbox', [])
                            })
            elif isinstance(block, dict) and 'text' in block:
                text = block['text'].strip()
                if text and len(text) > 10:
                    wine_entries.append({
                        'text': text,
                        'page': block.get('page', i),
                        'bbox': block.get('bbox', [])
                    })
        
        logger.info(f"✅ Extracted {len(wine_entries)} potential wine entries")
        
        # Show sample wine entries
        logger.info("\n📝 Sample wine entries from the real PDF:")
        for i, entry in enumerate(wine_entries[:10]):
            text = entry['text'][:100] + '...' if len(entry['text']) > 100 else entry['text']
            logger.info(f"  {i+1}. {text}")
        
        # Step 3: Test database integration with real wine entries
        logger.info("\nSTEP 3: Testing database integration with real wine entries")
        logger.info("-" * 50)
        
        from app.database_enhanced_rules.early_extractor import EarlyExtractor
        from app.database_enhanced_rules.database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        db_manager.load_databases()
        extractor = EarlyExtractor(db_manager)
        
        logger.info(f"✅ EarlyExtractor initialized with threshold: {extractor.confidence_threshold}")
        
        # Test each wine entry from the real PDF
        logger.info("\n🔍 Testing each wine entry from the real PDF:")
        
        db_matches = 0
        ai_skipped = 0
        grape_matches = 0
        producer_matches = 0
        region_matches = 0
        
        for i, entry in enumerate(wine_entries[:20]):  # Test first 20 entries
            text = entry['text']
            logger.info(f"\n  Wine {i+1}: {text}")
            
            # Test with EarlyExtractor
            result = extractor.extract_wine_info(text)
            
            logger.info(f"    EarlyExtractor result:")
            logger.info(f"      → Grape: {result.get('grape_variety')}")
            logger.info(f"      → Producer: {result.get('producer')}")
            logger.info(f"      → Region: {result.get('region')}")
            logger.info(f"      → Country: {result.get('country')}")
            logger.info(f"      → Confidence: {result.get('confidence'):.2f}")
            logger.info(f"      → Skip AI: {result.get('skip_ai')}")
            
            # Count matches
            if result.get('confidence', 0) > 0:
                db_matches += 1
            if result.get('skip_ai'):
                ai_skipped += 1
            if result.get('grape_variety'):
                grape_matches += 1
            if result.get('producer'):
                producer_matches += 1
            if result.get('region'):
                region_matches += 1
            
            # Test with database manager directly
            db_fields, db_confidence = db_manager.extract_fields(entry, cutoff=0.6)
            logger.info(f"    DatabaseManager result:")
            logger.info(f"      → Fields found: {list(db_fields.keys())}")
            logger.info(f"      → Confidence: {db_confidence:.2f}")
            
            # Show detailed field results
            for field, value in db_fields.items():
                if isinstance(value, dict) and value.get('value'):
                    logger.info(f"        → {field}: {value['value']} (conf: {value.get('confidence', 0):.2f})")
        
        # Step 4: Analyze why grapes and producers aren't matching
        logger.info("\nSTEP 4: Analyzing grape and producer matching issues")
        logger.info("-" * 50)
        
        # Test grape variety matching specifically
        logger.info("🍇 Testing grape variety matching:")
        
        # Get some grape varieties from the database
        grape_db = db_manager._databases.get('grape_varieties', {})
        sample_grapes = []
        for country_data in grape_db.values():
            if isinstance(country_data, list):
                sample_grapes.extend(country_data[:3])
            elif isinstance(country_data, dict):
                for region_data in country_data.values():
                    if isinstance(region_data, list):
                        sample_grapes.extend(region_data[:2])
            if len(sample_grapes) >= 20:
                break
        
        logger.info(f"📊 Sample grape varieties in database: {sample_grapes[:10]}")
        
        # Test producer matching specifically
        logger.info("\n🏭 Testing producer matching:")
        
        producers_db = db_manager._databases.get('producers', {})
        sample_producers = list(producers_db.keys())[:10]
        logger.info(f"📊 Sample producers in database: {sample_producers}")
        
        # Test with some wine entries that should match
        test_entries = [
            "Chardonnay, Domaine de la Côte, 2019, £45",
            "Pinot Noir, Burgundy, France, 2020, £65",
            "Riesling, Mosel, Germany, 2021, £25"
        ]
        
        logger.info("\n🧪 Testing with known wine entries:")
        for entry in test_entries:
            logger.info(f"\n  Testing: {entry}")
            
            # Test grape variety search
            grape_results = db_manager.search_grape_variety(entry, threshold=0.6)
            logger.info(f"    Grape search results: {grape_results[:3]}")
            
            # Test producer search
            producer_results = db_manager.search_producer(entry, threshold=0.6)
            logger.info(f"    Producer search results: {producer_results[:3]}")
            
            # Test EarlyExtractor
            result = extractor.extract_wine_info(entry)
            logger.info(f"    EarlyExtractor: grape={result.get('grape_variety')}, producer={result.get('producer')}")
        
        # Step 5: Test batch processing with real wine entries
        logger.info("\nSTEP 5: Batch processing with real wine entries")
        logger.info("-" * 50)
        
        # Test with first 20 wine entries from the real PDF
        test_wine_texts = [entry['text'] for entry in wine_entries[:20]]
        batch_results = extractor.batch_extract(test_wine_texts)
        batch_stats = extractor.get_extraction_stats(batch_results)
        
        logger.info(f"✅ Batch processing completed for {len(test_wine_texts)} real wine entries")
        logger.info(f"📊 Batch stats: {json.dumps(batch_stats, indent=2)}")
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("FINAL RESULTS - REAL PDF TEST")
        logger.info("="*80)
        
        logger.info("✅ Real PDF Database Integration Test Results:")
        logger.info(f"   → PDF file: {test_file.name} ({test_file.stat().st_size / 1024:.1f} KB)")
        logger.info(f"   → Text blocks extracted: {len(text_blocks)}")
        logger.info(f"   → Wine entries found: {len(wine_entries)}")
        logger.info(f"   → Database matches: {db_matches}/{min(20, len(wine_entries))}")
        logger.info(f"   → Grape matches: {grape_matches}/{min(20, len(wine_entries))}")
        logger.info(f"   → Producer matches: {producer_matches}/{min(20, len(wine_entries))}")
        logger.info(f"   → Region matches: {region_matches}/{min(20, len(wine_entries))}")
        logger.info(f"   → AI reduction: {(ai_skipped/min(20, len(wine_entries))*100):.1f}%")
        
        # Analysis of issues
        logger.info("\n🔍 Analysis of matching issues:")
        logger.info(f"   → Grape variety matching: {grape_matches}/{min(20, len(wine_entries))} ({grape_matches/min(20, len(wine_entries))*100:.1f}%)")
        logger.info(f"   → Producer matching: {producer_matches}/{min(20, len(wine_entries))} ({producer_matches/min(20, len(wine_entries))*100:.1f}%)")
        logger.info(f"   → Region matching: {region_matches}/{min(20, len(wine_entries))} ({region_matches/min(20, len(wine_entries))*100:.1f}%)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the real PDF database integration test."""
    success = test_real_pdf_simple()
    
    if success:
        logger.info("\n🎉 Real PDF database integration test completed successfully!")
        return 0
    else:
        logger.error("\n💥 Real PDF database integration test failed!")
        return 1

if __name__ == "__main__":
    exit(main())
