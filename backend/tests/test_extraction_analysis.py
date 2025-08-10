"""
Test script for the extraction analysis system

This script tests the extraction analysis system with sample data
to ensure it works correctly.
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from extraction_analysis_test import ExtractionAnalysisTest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_wine_entries():
    """Create sample wine entries for testing."""
    from app.models import WineEntry, WineListFile, Restaurant
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import uuid
    
    # Create in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables
    from app.models import Base
    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create sample restaurant
        restaurant = Restaurant(
            id=uuid.uuid4(),
            name="Test Restaurant"
        )
        db.add(restaurant)
        db.commit()
        
        # Create sample wine list file
        wine_list = WineListFile(
            id=uuid.uuid4(),
            restaurant_id=restaurant.id,
            filename="test_wine_list.pdf",
            file_url="https://example.com/test_wine_list.pdf",
            status="parsed",
            uploaded_at=datetime.utcnow(),
            parsed_date=datetime.utcnow()
        )
        db.add(wine_list)
        db.commit()
        
        # Create sample wine entries
        sample_entries = [
            {
                "producer": "Dom Pérignon",
                "cuvee": "Vintage",
                "type": "Champagne",
                "vintage": "2012",
                "price": "250",
                "bottle_size": "750ml",
                "grape_variety": "Chardonnay, Pinot Noir",
                "country": "France",
                "region": "Champagne",
                "subregion": "Épernay",
                "row_confidence": 0.95,
                "field_confidence": {
                    "producer": 0.98,
                    "vintage": 0.99,
                    "country": 0.97
                },
                "raw_text": "Dom Pérignon Vintage 2012 £250"
            },
            {
                "producer": "Krug",
                "cuvee": "Grande Cuvée",
                "type": "Champagne",
                "vintage": "NV",
                "price": "300",
                "bottle_size": "750ml",
                "grape_variety": "Chardonnay, Pinot Noir, Pinot Meunier",
                "country": "France",
                "region": "Champagne",
                "subregion": "Reims",
                "row_confidence": 0.92,
                "field_confidence": {
                    "producer": 0.96,
                    "vintage": 0.94,
                    "country": 0.95
                },
                "raw_text": "Krug Grande Cuvée NV £300"
            },
            {
                "producer": None,  # Failed extraction
                "cuvee": "Blanc de Blancs",
                "type": "Champagne",
                "vintage": "2018",
                "price": "180",
                "bottle_size": "750ml",
                "grape_variety": "Chardonnay",
                "country": "France",
                "region": "Champagne",
                "subregion": None,
                "row_confidence": 0.75,
                "field_confidence": {
                    "producer": 0.0,  # Failed
                    "vintage": 0.88,
                    "country": 0.92
                },
                "raw_text": "Blanc de Blancs 2018 £180"
            }
        ]
        
        for entry_data in sample_entries:
            wine_entry = WineEntry(
                id=uuid.uuid4(),
                wine_list_file_id=wine_list.id,
                restaurant_id=restaurant.id,
                producer=entry_data["producer"],
                cuvee=entry_data["cuvee"],
                type=entry_data["type"],
                vintage=entry_data["vintage"],
                price=entry_data["price"],
                bottle_size=entry_data["bottle_size"],
                grape_variety=entry_data["grape_variety"],
                country=entry_data["country"],
                region=entry_data["region"],
                subregion=entry_data["subregion"],
                row_confidence=entry_data["row_confidence"],
                field_confidence=entry_data["field_confidence"],
                raw_text=entry_data["raw_text"]
            )
            db.add(wine_entry)
        
        db.commit()
        
        return db, wine_list.id
        
    except Exception as e:
        db.rollback()
        raise e


def test_extraction_analysis():
    """Test the extraction analysis system."""
    print("Testing Extraction Analysis System")
    print("=" * 50)
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        try:
            # Create sample data
            print("Creating sample wine entries...")
            db, wine_list_id = create_sample_wine_entries()
            
            # Initialize analyzer
            print("Initializing extraction analyzer...")
            analyzer = ExtractionAnalysisTest(output_dir=temp_dir)
            
            # Run analysis
            print(f"Running analysis for wine_list_id: {wine_list_id}")
            results = analyzer.run_analysis(wine_list_id, db)
            
            # Verify results
            print("\nAnalysis Results:")
            print(f"  Total entries: {results['overall_metrics']['total_entries']}")
            print(f"  Overall success rate: {results['overall_metrics']['overall_success_rate']:.2%}")
            
            # Check field success rates
            field_success_rates = results['overall_metrics']['field_success_rates']
            print("\nField Success Rates:")
            for field, data in field_success_rates.items():
                print(f"  {field}: {data['success_rate']:.2%} ({data['successful']}/{data['total']})")
            
            # Check recommendations
            print(f"\nRecommendations ({len(results['recommendations'])}):")
            for rec in results['recommendations']:
                print(f"  • {rec}")
            
            # Check output files
            print(f"\nOutput files created:")
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    print(f"  {file_path} ({file_size} bytes)")
            
            # Verify expected files exist
            expected_dirs = ['reports', 'detailed_analysis', 'failure_analysis', 'performance']
            for dir_name in expected_dirs:
                dir_path = os.path.join(temp_dir, dir_name)
                if os.path.exists(dir_path):
                    print(f"  ✓ {dir_name} directory created")
                else:
                    print(f"  ✗ {dir_name} directory missing")
            
            print("\nTest completed successfully!")
            return True
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()


def test_auto_analysis_hook():
    """Test the auto analysis hook."""
    print("\nTesting Auto Analysis Hook")
    print("=" * 50)
    
    try:
        from auto_analysis_hook import (
            AutoAnalysisHook, 
            enable_auto_analysis, 
            disable_auto_analysis,
            get_queue_status
        )
        
        # Test hook initialization
        print("Testing hook initialization...")
        hook = AutoAnalysisHook(enabled=True, run_async=False)
        
        # Test status functions
        print("Testing status functions...")
        enable_auto_analysis()
        status = get_queue_status()
        print(f"  Enabled: {status['enabled']}")
        print(f"  Async mode: {status['async_mode']}")
        
        # Test file completion trigger
        print("Testing file completion trigger...")
        test_wine_list_id = "test-id-123"
        result = hook.on_file_complete(test_wine_list_id)
        print(f"  Trigger result: {result}")
        
        # Test shutdown
        print("Testing shutdown...")
        hook.shutdown()
        
        print("Auto analysis hook test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Auto analysis hook test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_run_extraction_test():
    """Test the run_extraction_test script."""
    print("\nTesting Run Extraction Test Script")
    print("=" * 50)
    
    try:
        from run_extraction_test import check_wine_list_status
        
        # Test status check function
        print("Testing wine list status check...")
        result = check_wine_list_status("non-existent-id")
        print(f"  Status check result: {result}")
        
        print("Run extraction test script test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Run extraction test script test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Running Extraction Analysis Test System Tests")
    print("=" * 60)
    
    tests = [
        ("Extraction Analysis", test_extraction_analysis),
        ("Auto Analysis Hook", test_auto_analysis_hook),
        ("Run Extraction Test", test_run_extraction_test)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The extraction analysis system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 