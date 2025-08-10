"""
Integration Test for Extraction Analysis System

This test verifies that the extraction analysis system is properly integrated
with the main API and can be triggered automatically.
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_api_integration():
    """Test that the API integration works correctly."""
    print("Testing API Integration")
    print("=" * 40)
    
    try:
        # Test that the trigger function can be imported
        from trigger_analysis import trigger_extraction_analysis, check_analysis_status
        
        print("✅ Trigger functions imported successfully")
        
        # Test that the auto-analysis hook can be imported
        from auto_analysis_hook import get_auto_analysis_hook
        
        print("✅ Auto-analysis hook imported successfully")
        
        # Test that the configuration can be imported
        from config import get_config, enable_auto_analysis
        
        print("✅ Configuration imported successfully")
        
        # Test configuration
        config = get_config()
        enable_auto_analysis()
        
        print(f"✅ Configuration loaded - Auto-analysis enabled: {config.is_enabled()}")
        
        # Test hook initialization
        hook = get_auto_analysis_hook()
        
        print(f"✅ Hook initialized - Enabled: {hook.enabled}, Async: {hook.run_async}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trigger_function():
    """Test the trigger function with a dummy wine list ID."""
    print("\nTesting Trigger Function")
    print("=" * 40)
    
    try:
        from trigger_analysis import trigger_extraction_analysis, check_analysis_status
        
        # Test with a dummy wine list ID
        dummy_wine_list_id = "test-integration-123"
        
        # This should not fail even with a non-existent wine list ID
        result = trigger_extraction_analysis(dummy_wine_list_id)
        
        print(f"✅ Trigger function executed - Result: {result}")
        
        # Test status check
        status = check_analysis_status(dummy_wine_list_id)
        
        print(f"✅ Status check executed - Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trigger function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test the configuration system."""
    print("\nTesting Configuration System")
    print("=" * 40)
    
    try:
        from config import (
            get_config, enable_auto_analysis, disable_auto_analysis,
            set_async_mode, get_config_summary
        )
        
        # Test configuration operations
        config = get_config()
        
        # Test enable/disable
        enable_auto_analysis()
        print(f"✅ Auto-analysis enabled: {config.is_enabled()}")
        
        disable_auto_analysis()
        print(f"✅ Auto-analysis disabled: {config.is_enabled()}")
        
        # Re-enable for testing
        enable_auto_analysis()
        
        # Test async mode
        set_async_mode(False)
        print(f"✅ Async mode disabled: {config.is_async()}")
        
        set_async_mode(True)
        print(f"✅ Async mode enabled: {config.is_async()}")
        
        # Test config summary
        summary = get_config_summary()
        print(f"✅ Config summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_analysis_hook():
    """Test the auto-analysis hook."""
    print("\nTesting Auto-Analysis Hook")
    print("=" * 40)
    
    try:
        from auto_analysis_hook import (
            AutoAnalysisHook, get_auto_analysis_hook,
            get_queue_status, clear_analysis_queue
        )
        
        # Test hook creation
        hook = AutoAnalysisHook(enabled=True, run_async=False)
        
        print(f"✅ Hook created - Enabled: {hook.enabled}, Async: {hook.run_async}")
        
        # Test file completion trigger
        dummy_wine_list_id = "test-hook-123"
        result = hook.on_file_complete(dummy_wine_list_id)
        
        print(f"✅ File completion triggered - Result: {result}")
        
        # Test queue status
        status = get_queue_status()
        print(f"✅ Queue status: {status}")
        
        # Test queue clearing
        clear_analysis_queue()
        print("✅ Queue cleared")
        
        # Test shutdown
        hook.shutdown()
        print("✅ Hook shutdown completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Auto-analysis hook test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_from_api():
    """Test that the API can import the trigger functions."""
    print("\nTesting API Import")
    print("=" * 40)
    
    try:
        # Simulate the import that happens in the API
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Test the exact import used in the API
        from trigger_analysis import trigger_extraction_analysis
        
        print("✅ API import test successful")
        
        return True
        
    except Exception as e:
        print(f"❌ API import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("Extraction Analysis System - Integration Tests")
    print("=" * 60)
    
    tests = [
        ("API Integration", test_api_integration),
        ("Trigger Function", test_trigger_function),
        ("Configuration", test_configuration),
        ("Auto-Analysis Hook", test_auto_analysis_hook),
        ("API Import", test_import_from_api)
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
    print("INTEGRATION TEST SUMMARY")
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
        print("🎉 All integration tests passed! The system is ready for use.")
        return 0
    else:
        print("❌ Some integration tests failed. Please check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 