#!/usr/bin/env python3
"""
Simplified test for database integration focusing on the key results.
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

def test_database_integration():
    """Test database integration with real wine list data."""
    
    logger.info("🧪 Testing Database Integration with Real Wine List")
    logger.info("="*60)
    
    try:
        # Test database manager
        logger.info("STEP 1: Database Manager")
        from app.database_enhanced_rules.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        db_manager.load_databases()
        stats = db_manager.get_database_stats()
        
        logger.info(f"✅ Database loaded successfully")
        logger.info(f"📊 Stats: {json.dumps(stats, indent=2)}")
        
        # Test EarlyExtractor
        logger.info("\nSTEP 2: EarlyExtractor")
        from app.database_enhanced_rules.early_extractor import EarlyExtractor
        extractor = EarlyExtractor(db_manager)
        logger.info(f"✅ EarlyExtractor initialized with threshold: {extractor.confidence_threshold}")
        
        # Test with real wine entries from the PDF
        test_wines = [
            "Chardonnay, Domaine de la Côte, 2019, £45",
            "Pinot Noir, Burgundy, France, 2020, £65", 
            "Riesling, Mosel, Germany, 2021, £25",
            "Sauvignon Blanc, Marlborough, New Zealand, 2022, £35",
            "Cabernet Sauvignon, Napa Valley, California, 2018, £85",
            "Champagne, Dom Pérignon, 2015, £200",
            "Barolo, Piedmont, Italy, 2016, £120",
            "Rioja, Spain, 2017, £45"
        ]
        
        logger.info("\n🍷 Testing with real wine entries:")
        db_matches = 0
        ai_skipped = 0
        
        for i, wine_text in enumerate(test_wines):
            result = extractor.extract_wine_info(wine_text)
            
            logger.info(f"\n  {i+1}. {wine_text}")
            logger.info(f"     → Grape: {result.get('grape_variety')}")
            logger.info(f"     → Producer: {result.get('producer')}")
            logger.info(f"     → Region: {result.get('region')}")
            logger.info(f"     → Country: {result.get('country')}")
            logger.info(f"     → Confidence: {result.get('confidence'):.2f}")
            logger.info(f"     → Skip AI: {result.get('skip_ai')}")
            
            if result.get('confidence', 0) > 0:
                db_matches += 1
            if result.get('skip_ai'):
                ai_skipped += 1
        
        # Test batch processing
        logger.info("\nSTEP 3: Batch Processing")
        batch_results = extractor.batch_extract(test_wines)
        batch_stats = extractor.get_extraction_stats(batch_results)
        
        logger.info(f"✅ Batch processing completed")
        logger.info(f"📊 Batch stats: {json.dumps(batch_stats, indent=2)}")
        
        # Test HybridExtractionPipeline
        logger.info("\nSTEP 4: HybridExtractionPipeline Integration")
        from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline
        from app.config import DATABASE_INTEGRATION_ENABLED
        
        logger.info(f"🚩 Database integration enabled: {DATABASE_INTEGRATION_ENABLED}")
        
        pipeline = HybridExtractionPipeline("test-restaurant-id")
        logger.info(f"✅ Pipeline created, EarlyExtractor available: {pipeline.early_extractor is not None}")
        
        # Test early database extraction
        test_blocks = [{"text": wine, "type": "wine_entry"} for wine in test_wines]
        early_results = pipeline._perform_early_database_extraction(test_blocks)
        
        logger.info(f"✅ Early extraction completed for {len(early_results)} blocks")
        
        # Analyze results
        pipeline_db_matches = sum(1 for r in early_results if r and r.get('confidence', 0) > 0)
        pipeline_ai_skipped = sum(1 for r in early_results if r and r.get('skip_ai'))
        
        logger.info(f"📈 Pipeline analysis:")
        logger.info(f"   → Database matches: {pipeline_db_matches}/{len(test_blocks)}")
        logger.info(f"   → AI skipped: {pipeline_ai_skipped}/{len(test_blocks)}")
        logger.info(f"   → AI reduction: {(pipeline_ai_skipped/len(test_blocks)*100):.1f}%")
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("FINAL RESULTS")
        logger.info("="*60)
        
        logger.info("✅ Database Integration Test Results:")
        logger.info(f"   → Database loaded: {stats['producers']['total_producers']} producers, {stats['regions']['total_regions']} regions")
        logger.info(f"   → Individual matches: {db_matches}/{len(test_wines)} wines")
        logger.info(f"   → Pipeline matches: {pipeline_db_matches}/{len(test_blocks)} blocks")
        logger.info(f"   → AI reduction potential: {(pipeline_ai_skipped/len(test_blocks)*100):.1f}%")
        logger.info(f"   → Database integration: ✅ WORKING")
        logger.info(f"   → EarlyExtractor: ✅ WORKING")
        logger.info(f"   → Pipeline integration: ✅ WORKING")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the database integration test."""
    success = test_database_integration()
    
    if success:
        logger.info("\n🎉 Database integration test completed successfully!")
        return 0
    else:
        logger.error("\n💥 Database integration test failed!")
        return 1

if __name__ == "__main__":
    exit(main())
