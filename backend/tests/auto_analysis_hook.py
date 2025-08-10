"""
Auto Analysis Hook

This module provides hooks that can be integrated into the main processing pipeline
to automatically run extraction analysis when a wine list file completes processing.
"""

import os
import sys
import logging
import threading
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import with error handling - defer imports to avoid circular dependencies
_auto_run_analysis = None
_check_wine_list_status = None

def _load_analysis_functions():
    """Load analysis functions when needed to avoid circular imports."""
    global _auto_run_analysis, _check_wine_list_status
    
    if _auto_run_analysis is not None:
        return  # Already loaded
    
    try:
        from .run_extraction_test import auto_run_analysis, check_wine_list_status
        _auto_run_analysis = auto_run_analysis
        _check_wine_list_status = check_wine_list_status
    except ImportError:
        # Fallback import
        try:
            from run_extraction_test import auto_run_analysis, check_wine_list_status
            _auto_run_analysis = auto_run_analysis
            _check_wine_list_status = check_wine_list_status
        except ImportError:
            # If both fail, create dummy functions
            def auto_run_analysis(wine_list_id: str) -> bool:
                logger.warning(f"Auto analysis not available for {wine_list_id}")
                return False
            
            def check_wine_list_status(wine_list_id: str) -> bool:
                logger.warning(f"Status check not available for {wine_list_id}")
                return False
            
            _auto_run_analysis = auto_run_analysis
            _check_wine_list_status = check_wine_list_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoAnalysisHook:
    """
    Hook class that can be integrated into the processing pipeline
    to automatically run extraction analysis when files complete.
    """
    
    def __init__(self, enabled: bool = True, run_async: bool = True):
        """
        Initialize the auto analysis hook.
        
        Args:
            enabled: Whether auto-analysis is enabled
            run_async: Whether to run analysis asynchronously (non-blocking)
        """
        self.enabled = enabled
        self.run_async = run_async
        self.analysis_queue = []
        self.analysis_thread = None
        
        if self.enabled and self.run_async:
            self._start_analysis_thread()
        
        logger.info(f"AutoAnalysisHook initialized - enabled: {enabled}, async: {run_async}")
    
    def on_file_complete(self, wine_list_id: str) -> bool:
        """
        Called when a wine list file completes processing.
        
        Args:
            wine_list_id: The ID of the wine list file that completed
            
        Returns:
            bool: True if analysis was triggered successfully
        """
        if not self.enabled:
            logger.debug(f"Auto-analysis disabled, skipping analysis for {wine_list_id}")
            return False
        
        logger.info(f"File completion detected for wine_list_id: {wine_list_id}")
        
        if self.run_async:
            # Add to queue for async processing
            self.analysis_queue.append(wine_list_id)
            logger.info(f"Added {wine_list_id} to analysis queue")
            return True
        else:
            # Run analysis synchronously
            return self._run_analysis_sync(wine_list_id)
    
    def _run_analysis_sync(self, wine_list_id: str) -> bool:
        """Run analysis synchronously."""
        try:
            logger.info(f"Running synchronous analysis for {wine_list_id}")
            _load_analysis_functions()
            return _auto_run_analysis(wine_list_id)
        except Exception as e:
            logger.error(f"Error in synchronous analysis for {wine_list_id}: {e}")
            return False
    
    def _start_analysis_thread(self):
        """Start the background thread for async analysis."""
        if self.analysis_thread and self.analysis_thread.is_alive():
            return
        
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.info("Analysis worker thread started")
    
    def _analysis_worker(self):
        """Background worker that processes analysis queue."""
        logger.info("Analysis worker started")
        
        while True:
            try:
                if self.analysis_queue:
                    wine_list_id = self.analysis_queue.pop(0)
                    logger.info(f"Processing analysis for {wine_list_id}")
                    
                    # Load analysis functions
                    _load_analysis_functions()
                    
                    # Check if file is ready for analysis
                    if _check_wine_list_status(wine_list_id):
                        _auto_run_analysis(wine_list_id)
                    else:
                        logger.warning(f"Wine list {wine_list_id} not ready for analysis, skipping")
                
                # Sleep briefly to avoid busy waiting
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in analysis worker: {e}")
                import time
                time.sleep(5)  # Wait longer on error
    
    def shutdown(self):
        """Shutdown the analysis hook."""
        logger.info("Shutting down AutoAnalysisHook")
        self.enabled = False
        
        # Wait for analysis thread to finish
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=10)
            logger.info("Analysis worker thread stopped")


# Global instance for easy integration
_auto_analysis_hook = None


def get_auto_analysis_hook() -> AutoAnalysisHook:
    """Get the global auto analysis hook instance."""
    global _auto_analysis_hook
    if _auto_analysis_hook is None:
        _auto_analysis_hook = AutoAnalysisHook()
    return _auto_analysis_hook


def trigger_analysis(wine_list_id: str) -> bool:
    """
    Convenience function to trigger analysis for a wine list.
    
    Args:
        wine_list_id: The ID of the wine list file
        
    Returns:
        bool: True if analysis was triggered successfully
    """
    hook = get_auto_analysis_hook()
    return hook.on_file_complete(wine_list_id)


# Integration functions for the main processing pipeline
def integrate_with_api_v2():
    """
    Integration function to be called from api_v2.py after successful processing.
    """
    # This function should be called after the database save step is completed
    # in the process_pdf function in api_v2.py
    
    logger.info("Auto-analysis hook integrated with api_v2")
    
    # Example integration code (to be added to api_v2.py):
    """
    # After successful database save in process_pdf function:
    from tests.auto_analysis_hook import trigger_analysis
    
    # Trigger analysis for the completed wine list
    trigger_analysis(str(wine_list.id))
    """


def integrate_with_upload_endpoint():
    """
    Integration function to be called from the upload endpoint after successful processing.
    """
    # This function should be called after the upload endpoint completes processing
    
    logger.info("Auto-analysis hook integrated with upload endpoint")
    
    # Example integration code (to be added to upload endpoint):
    """
    # After successful processing in upload endpoint:
    from tests.auto_analysis_hook import trigger_analysis
    
    # Trigger analysis for the completed wine list
    trigger_analysis(str(wine_list.id))
    """


# Configuration functions
def enable_auto_analysis():
    """Enable auto-analysis."""
    hook = get_auto_analysis_hook()
    hook.enabled = True
    logger.info("Auto-analysis enabled")


def disable_auto_analysis():
    """Disable auto-analysis."""
    hook = get_auto_analysis_hook()
    hook.enabled = False
    logger.info("Auto-analysis disabled")


def set_async_mode(enabled: bool):
    """Set whether analysis runs asynchronously."""
    hook = get_auto_analysis_hook()
    hook.run_async = enabled
    logger.info(f"Async mode {'enabled' if enabled else 'disabled'}")


# Utility functions for monitoring
def get_queue_status() -> dict:
    """Get the current status of the analysis queue."""
    hook = get_auto_analysis_hook()
    return {
        "enabled": hook.enabled,
        "async_mode": hook.run_async,
        "queue_length": len(hook.analysis_queue),
        "worker_alive": hook.analysis_thread.is_alive() if hook.analysis_thread else False
    }


def clear_analysis_queue():
    """Clear the analysis queue."""
    hook = get_auto_analysis_hook()
    hook.analysis_queue.clear()
    logger.info("Analysis queue cleared")


if __name__ == "__main__":
    # Test the hook
    import uuid
    
    # Create a test wine list ID
    test_wine_list_id = str(uuid.uuid4())
    
    print("Testing AutoAnalysisHook...")
    
    # Enable auto-analysis
    enable_auto_analysis()
    
    # Trigger analysis
    result = trigger_analysis(test_wine_list_id)
    print(f"Analysis triggered: {result}")
    
    # Check queue status
    status = get_queue_status()
    print(f"Queue status: {status}")
    
    # Wait a moment for async processing
    import time
    time.sleep(2)
    
    # Check status again
    status = get_queue_status()
    print(f"Queue status after delay: {status}")
    
    print("Test completed") 