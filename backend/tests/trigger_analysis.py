"""
Trigger Analysis Script

Simple script to trigger extraction analysis when a wine list file completes processing.
This can be easily integrated into the existing API pipeline.
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import with error handling
try:
    from auto_analysis_hook import trigger_analysis, get_auto_analysis_hook
    from config import get_config
except ImportError:
    # Fallback imports
    try:
        from .auto_analysis_hook import trigger_analysis, get_auto_analysis_hook
        from .config import get_config
    except ImportError:
        # If both fail, create dummy functions
        def trigger_analysis(wine_list_id: str) -> bool:
            logger.warning(f"Trigger analysis not available for {wine_list_id}")
            return False
        
        def get_auto_analysis_hook():
            logger.warning("Auto analysis hook not available")
            return None
        
        def get_config():
            logger.warning("Config not available")
            return None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def trigger_extraction_analysis(wine_list_id: str) -> bool:
    """
    Trigger extraction analysis for a completed wine list.
    
    Args:
        wine_list_id: The ID of the wine list file that completed processing
        
    Returns:
        bool: True if analysis was triggered successfully, False otherwise
    """
    try:
        config = get_config()
        
        if not config.is_enabled():
            logger.info(f"Auto-analysis disabled, skipping analysis for {wine_list_id}")
            return False
        
        logger.info(f"Triggering extraction analysis for wine_list_id: {wine_list_id}")
        
        # Trigger the analysis
        result = trigger_analysis(wine_list_id)
        
        if result:
            logger.info(f"Extraction analysis triggered successfully for {wine_list_id}")
        else:
            logger.warning(f"Failed to trigger extraction analysis for {wine_list_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error triggering extraction analysis for {wine_list_id}: {e}")
        return False


def trigger_analysis_sync(wine_list_id: str) -> bool:
    """
    Trigger extraction analysis synchronously (blocking).
    
    Args:
        wine_list_id: The ID of the wine list file that completed processing
        
    Returns:
        bool: True if analysis completed successfully, False otherwise
    """
    try:
        config = get_config()
        
        if not config.is_enabled():
            logger.info(f"Auto-analysis disabled, skipping analysis for {wine_list_id}")
            return False
        
        logger.info(f"Triggering synchronous extraction analysis for wine_list_id: {wine_list_id}")
        
        # Get the hook and run analysis synchronously
        hook = get_auto_analysis_hook()
        
        # Temporarily disable async mode
        original_async = hook.run_async
        hook.run_async = False
        
        try:
            result = hook.on_file_complete(wine_list_id)
            return result
        finally:
            # Restore original async mode
            hook.run_async = original_async
        
    except Exception as e:
        logger.error(f"Error in synchronous extraction analysis for {wine_list_id}: {e}")
        return False


def check_analysis_status(wine_list_id: str) -> dict:
    """
    Check the status of analysis for a wine list.
    
    Args:
        wine_list_id: The ID of the wine list file
        
    Returns:
        dict: Status information about the analysis
    """
    try:
        hook = get_auto_analysis_hook()
        
        # Check if wine_list_id is in the queue
        in_queue = wine_list_id in hook.analysis_queue
        
        # Check if analysis files exist
        config = get_config()
        output_dir = config.get_output_dir()
        
        analysis_files = []
        if os.path.exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if wine_list_id in file:
                        analysis_files.append(os.path.join(root, file))
        
        return {
            "wine_list_id": wine_list_id,
            "in_queue": in_queue,
            "queue_position": hook.analysis_queue.index(wine_list_id) if in_queue else -1,
            "analysis_files_found": len(analysis_files),
            "analysis_files": analysis_files,
            "auto_analysis_enabled": config.is_enabled(),
            "async_mode": config.is_async()
        }
        
    except Exception as e:
        logger.error(f"Error checking analysis status for {wine_list_id}: {e}")
        return {
            "wine_list_id": wine_list_id,
            "error": str(e)
        }


def get_analysis_results(wine_list_id: str) -> dict:
    """
    Get analysis results for a wine list if they exist.
    
    Args:
        wine_list_id: The ID of the wine list file
        
    Returns:
        dict: Analysis results or error information
    """
    try:
        config = get_config()
        output_dir = config.get_output_dir()
        
        # Look for summary report
        summary_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if wine_list_id in file and "summary" in file and file.endswith(".json"):
                    summary_files.append(os.path.join(root, file))
        
        if not summary_files:
            return {
                "wine_list_id": wine_list_id,
                "error": "No analysis results found"
            }
        
        # Get the most recent summary file
        import json
        from datetime import datetime
        
        latest_file = max(summary_files, key=os.path.getctime)
        
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        return {
            "wine_list_id": wine_list_id,
            "summary_file": latest_file,
            "analysis_timestamp": results.get("analysis_timestamp"),
            "overall_success_rate": results.get("key_findings", {}).get("overall_success_rate"),
            "total_entries": results.get("key_findings", {}).get("total_entries"),
            "recommendations": results.get("recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting analysis results for {wine_list_id}: {e}")
        return {
            "wine_list_id": wine_list_id,
            "error": str(e)
        }


# Integration functions for easy use in the main API
def integrate_with_api_v2(wine_list_id: str) -> bool:
    """
    Integration function for api_v2.py
    
    Add this line to the process_pdf function after successful database save:
    
    from tests.trigger_analysis import integrate_with_api_v2
    integrate_with_api_v2(str(wine_list.id))
    """
    return trigger_extraction_analysis(wine_list_id)


def integrate_with_upload_endpoint(wine_list_id: str) -> bool:
    """
    Integration function for the upload endpoint
    
    Add this line to the upload endpoint after successful processing:
    
    from tests.trigger_analysis import integrate_with_upload_endpoint
    integrate_with_upload_endpoint(str(wine_list.id))
    """
    return trigger_extraction_analysis(wine_list_id)


def integrate_with_steps_status(wine_list_id: str, steps_status: dict) -> bool:
    """
    Integration function for steps_status updates
    
    Add this to any part of the pipeline that updates steps_status:
    
    from tests.trigger_analysis import integrate_with_steps_status
    if all(step.get('status') == 'completed' for step in steps_status.values()):
        integrate_with_steps_status(str(wine_list.id), steps_status)
    """
    # Check if all steps are completed
    all_completed = all(
        step.get('status') == 'completed' 
        for step in steps_status.values()
    )
    
    if all_completed:
        return trigger_extraction_analysis(wine_list_id)
    
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger extraction analysis')
    parser.add_argument('wine_list_id', help='The ID of the wine list file')
    parser.add_argument('--sync', action='store_true', help='Run analysis synchronously')
    parser.add_argument('--status', action='store_true', help='Check analysis status')
    parser.add_argument('--results', action='store_true', help='Get analysis results')
    
    args = parser.parse_args()
    
    if args.status:
        status = check_analysis_status(args.wine_list_id)
        print("Analysis Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    elif args.results:
        results = get_analysis_results(args.wine_list_id)
        print("Analysis Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
    
    else:
        if args.sync:
            result = trigger_analysis_sync(args.wine_list_id)
        else:
            result = trigger_extraction_analysis(args.wine_list_id)
        
        print(f"Analysis triggered: {result}") 