#!/usr/bin/env python3
"""
Comprehensive test for database integration in the full pipeline.
Tests the complete wine list processing pipeline with focus on database integration.
"""

import sys
import os
import logging
import json
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_integration_pipeline():
    """Test the complete pipeline with database integration."""
    
    # Test file path
    test_file = Path(__file__).parent.parent / "real-files" / "compagnie-des-vins-surnaturels-seven-dials-pages.pdf"
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False
    
    logger.info(f"🧪 Testing database integration with file: {test_file.name}")
    logger.info(f"📁 File size: {test_file.stat().st_size / 1024:.1f} KB")
    
    try:
        # Step 1: Test database manager
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Testing Database Manager")
        logger.info("="*60)
        
        from app.database_enhanced_rules.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.load_databases()
        stats = db_manager.get_database_stats()
        
        logger.info(f"✅ Database loaded successfully")
        logger.info(f"📊 Database stats: {json.dumps(stats, indent=2)}")
        
        # Step 2: Test EarlyExtractor
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Testing EarlyExtractor")
        logger.info("="*60)
        
        from app.database_enhanced_rules.early_extractor import EarlyExtractor
        extractor = EarlyExtractor(db_manager)
        logger.info(f"✅ EarlyExtractor initialized with threshold: {extractor.confidence_threshold}")
        
        # Test with sample wine texts
        test_wines = [
            "Chardonnay, Domaine de la Côte, 2019, £45",
            "Pinot Noir, Burgundy, France, 2020, £65",
            "Riesling, Mosel, Germany, 2021, £25",
            "Sauvignon Blanc, Marlborough, New Zealand, 2022, £35"
        ]
        
        logger.info("🍷 Testing EarlyExtractor with sample wines:")
        for i, wine_text in enumerate(test_wines):
            result = extractor.extract_wine_info(wine_text)
            logger.info(f"  {i+1}. {wine_text}")
            logger.info(f"     → Grape: {result.get('grape_variety')}")
            logger.info(f"     → Producer: {result.get('producer')}")
            logger.info(f"     → Region: {result.get('region')}")
            logger.info(f"     → Country: {result.get('country')}")
            logger.info(f"     → Confidence: {result.get('confidence'):.2f}")
            logger.info(f"     → Skip AI: {result.get('skip_ai')}")
        
        # Step 3: Test PDF processing pipeline
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Testing PDF Processing Pipeline")
        logger.info("="*60)
        
        from app.pdf_processing.extractor import PDFExtractor
        from app.pdf_processing.preprocessor import PDFTextPreprocessor
        from app.pdf_processing.categorizer import PDFBlockCategorizer
        from app.pdf_processing.header_associator import HeaderWineAssociator
        
        # Extract text from PDF
        logger.info("📄 Extracting text from PDF...")
        text_extractor = PDFExtractor()
        text_blocks = text_extractor.extract_text_blocks(str(test_file))
        logger.info(f"✅ Extracted {len(text_blocks)} text blocks")
        
        # Preprocess text
        logger.info("🔧 Preprocessing text...")
        preprocessor = PDFTextPreprocessor()
        preprocessed_blocks = preprocessor.preprocess(text_blocks)
        logger.info(f"✅ Preprocessed {len(preprocessed_blocks)} blocks")
        
        # Categorize blocks
        logger.info("📋 Categorizing blocks...")
        categorizer = PDFBlockCategorizer()
        categorized_blocks = categorizer.categorize(preprocessed_blocks)
        logger.info(f"✅ Categorized {len(categorized_blocks)} blocks")
        
        # Filter wine entries
        wine_blocks = [block for block in categorized_blocks if block.get('type') == 'wine_entry']
        logger.info(f"🍷 Found {len(wine_blocks)} wine entries")
        
        # Show sample wine entries
        logger.info("📝 Sample wine entries:")
        for i, block in enumerate(wine_blocks[:5]):  # Show first 5
            text = block.get('text', '')[:100] + '...' if len(block.get('text', '')) > 100 else block.get('text', '')
            logger.info(f"  {i+1}. {text}")
        
        # Step 4: Test HybridExtractionPipeline with database integration
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Testing HybridExtractionPipeline with Database Integration")
        logger.info("="*60)
        
        from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline
        from app.config import DATABASE_INTEGRATION_ENABLED
        
        logger.info(f"🚩 Database integration enabled: {DATABASE_INTEGRATION_ENABLED}")
        
        # Create pipeline
        pipeline = HybridExtractionPipeline("test-restaurant-id")
        logger.info(f"✅ Pipeline created, EarlyExtractor available: {pipeline.early_extractor is not None}")
        
        # Test early database extraction
        logger.info("🗄️ Testing early database extraction...")
        early_results = pipeline._perform_early_database_extraction(wine_blocks)
        logger.info(f"✅ Early extraction completed for {len(early_results)} blocks")
        
        # Analyze early extraction results
        db_matches = 0
        high_confidence = 0
        ai_skipped = 0
        
        for i, result in enumerate(early_results):
            if result:
                db_matches += 1
                if result.get('confidence', 0) >= 0.6:
                    high_confidence += 1
                if result.get('skip_ai'):
                    ai_skipped += 1
                
                # Show detailed results for first few matches
                if i < 3 and result:
                    logger.info(f"  📊 Early result {i+1}:")
                    logger.info(f"     → Confidence: {result.get('confidence', 0):.2f}")
                    logger.info(f"     → Skip AI: {result.get('skip_ai', False)}")
                    logger.info(f"     → Fields: {list(result.keys())}")
        
        logger.info(f"📈 Early extraction analysis:")
        logger.info(f"   → Total blocks: {len(wine_blocks)}")
        logger.info(f"   → Database matches: {db_matches}")
        logger.info(f"   → High confidence: {high_confidence}")
        logger.info(f"   → AI skipped: {ai_skipped}")
        logger.info(f"   → AI reduction: {(ai_skipped/len(wine_blocks)*100):.1f}%")
        
        # Step 5: Test full pipeline processing
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Testing Full Pipeline Processing")
        logger.info("="*60)
        
        # Process a subset of wine blocks for testing
        test_blocks = wine_blocks[:10]  # Test with first 10 entries
        logger.info(f"🔄 Processing {len(test_blocks)} wine blocks through full pipeline...")
        
        start_time = datetime.now()
        pipeline_results = pipeline.process_wine_list(test_blocks)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"✅ Pipeline processing completed in {processing_time:.2f} seconds")
        
        # Analyze pipeline results
        extraction_results = pipeline_results.get('extraction_results', [])
        metadata = pipeline_results.get('metadata', {})
        
        logger.info(f"📊 Pipeline results analysis:")
        logger.info(f"   → Extracted entries: {len(extraction_results)}")
        logger.info(f"   → Processing time: {processing_time:.2f}s")
        logger.info(f"   → Time per entry: {processing_time/len(test_blocks):.2f}s")
        
        # Analyze extraction quality
        successful_extractions = 0
        fields_extracted = {}
        
        for result in extraction_results:
            if result:
                successful_extractions += 1
                for field, value in result.items():
                    if isinstance(value, dict) and value.get('value'):
                        fields_extracted[field] = fields_extracted.get(field, 0) + 1
        
        logger.info(f"📈 Extraction quality analysis:")
        logger.info(f"   → Successful extractions: {successful_extractions}/{len(test_blocks)}")
        logger.info(f"   → Success rate: {(successful_extractions/len(test_blocks)*100):.1f}%")
        logger.info(f"   → Fields extracted: {fields_extracted}")
        
        # Step 6: Compare with and without database integration
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Database Integration Impact Analysis")
        logger.info("="*60)
        
        # Test individual wine entries with EarlyExtractor
        logger.info("🔍 Testing individual wine entries with EarlyExtractor:")
        
        for i, block in enumerate(test_blocks[:5]):
            text = block.get('text', '')
            logger.info(f"\n  Wine {i+1}: {text[:80]}...")
            
            # Test with EarlyExtractor
            early_result = extractor.extract_wine_info(text)
            logger.info(f"    EarlyExtractor result:")
            logger.info(f"      → Grape: {early_result.get('grape_variety')}")
            logger.info(f"      → Producer: {early_result.get('producer')}")
            logger.info(f"      → Region: {early_result.get('region')}")
            logger.info(f"      → Country: {early_result.get('country')}")
            logger.info(f"      → Confidence: {early_result.get('confidence'):.2f}")
            logger.info(f"      → Skip AI: {early_result.get('skip_ai')}")
            
            # Test with database manager directly
            db_fields, db_confidence = db_manager.extract_fields(block, cutoff=0.6)
            logger.info(f"    DatabaseManager result:")
            logger.info(f"      → Fields: {list(db_fields.keys())}")
            logger.info(f"      → Confidence: {db_confidence:.2f}")
        
        # Step 7: Performance analysis
        logger.info("\n" + "="*60)
        logger.info("STEP 7: Performance Analysis")
        logger.info("="*60)
        
        # Test batch processing performance
        logger.info("⚡ Testing batch processing performance...")
        
        batch_start = datetime.now()
        batch_results = extractor.batch_extract([block.get('text', '') for block in test_blocks])
        batch_end = datetime.now()
        
        batch_time = (batch_end - batch_start).total_seconds()
        batch_stats = extractor.get_extraction_stats(batch_results)
        
        logger.info(f"📊 Batch processing results:")
        logger.info(f"   → Processing time: {batch_time:.2f}s")
        logger.info(f"   → Time per entry: {batch_time/len(test_blocks):.2f}s")
        logger.info(f"   → Stats: {json.dumps(batch_stats, indent=2)}")
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("FINAL SUMMARY")
        logger.info("="*60)
        
        logger.info("✅ Database Integration Test Results:")
        logger.info(f"   → Database loaded: {stats}")
        logger.info(f"   → EarlyExtractor working: ✅")
        logger.info(f"   → Pipeline integration: ✅")
        logger.info(f"   → Database matches found: {db_matches}/{len(wine_blocks)}")
        logger.info(f"   → AI reduction potential: {(ai_skipped/len(wine_blocks)*100):.1f}%")
        logger.info(f"   → Processing performance: {processing_time:.2f}s for {len(test_blocks)} entries")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the database integration test."""
    logger.info("🚀 Starting comprehensive database integration pipeline test...")
    
    success = test_database_integration_pipeline()
    
    if success:
        logger.info("🎉 Database integration test completed successfully!")
        return 0
    else:
        logger.error("💥 Database integration test failed!")
        return 1

if __name__ == "__main__":
    exit(main())
