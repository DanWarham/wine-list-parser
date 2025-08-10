"""
Wine List Parser Application

This module initializes the wine list parser application and its components.
"""

import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extraction analysis system
def initialize_extraction_analysis():
    """Initialize the extraction analysis test system."""
    try:
        # Add the tests directory to Python path
        backend_dir = Path(__file__).parent
        tests_dir = backend_dir.parent / "tests"  # Go up one level to backend/tests
        
        if not tests_dir.exists():
            logger.warning(f"Tests directory not found: {tests_dir}")
            return False
            
        import sys
        if str(tests_dir) not in sys.path:
            sys.path.insert(0, str(tests_dir))
        
        # Check if required files exist
        required_files = ["config.py", "auto_analysis_hook.py", "trigger_analysis.py"]
        for file in required_files:
            if not (tests_dir / file).exists():
                logger.warning(f"Required file not found: {file}")
                return False
        
        # Import and initialize the auto-analysis system
        try:
            logger.info("Attempting to import extraction analysis modules...")
            
            from tests.config import get_config, enable_auto_analysis
            logger.info("✅ Config module imported successfully")
            
            from tests.auto_analysis_hook import get_auto_analysis_hook
            logger.info("✅ Auto analysis hook module imported successfully")
            
            # Get configuration
            config = get_config()
            logger.info("✅ Configuration loaded successfully")
            
            # Enable auto-analysis by default
            enable_auto_analysis()
            logger.info("✅ Auto-analysis enabled")
            
            # Initialize the hook
            hook = get_auto_analysis_hook()
            logger.info("✅ Auto analysis hook initialized")
            
            logger.info("Extraction analysis system initialized successfully")
            logger.info(f"Auto-analysis enabled: {config.is_enabled()}")
            logger.info(f"Async mode: {config.is_async()}")
            
            return True
            
        except ImportError as import_error:
            logger.warning(f"Import error in extraction analysis system: {import_error}")
            logger.warning(f"Import error details: {type(import_error).__name__}: {import_error}")
            return False
        except Exception as init_error:
            logger.warning(f"Initialization error in extraction analysis system: {init_error}")
            logger.warning(f"Error details: {type(init_error).__name__}: {init_error}")
            return False
            
    except Exception as e:
        logger.warning(f"Could not initialize extraction analysis system: {e}")
        logger.warning("Extraction analysis will not be available")
        return False

# Initialize the system when the module is imported
# Use a try-catch to handle any initialization errors gracefully
try:
    extraction_analysis_initialized = initialize_extraction_analysis()
    
    if extraction_analysis_initialized:
        logger.info("✅ Extraction analysis system ready")
    else:
        logger.warning("⚠️ Extraction analysis system not available")
except Exception as e:
    logger.warning(f"⚠️ Extraction analysis system initialization failed: {e}")
    logger.warning("Extraction analysis will not be available")
    extraction_analysis_initialized = False
