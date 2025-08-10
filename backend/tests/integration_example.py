"""
Integration Example for Extraction Analysis Test System

This file shows how to integrate the extraction analysis test system
into the existing API pipeline to automatically run analysis when files complete.
"""

import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def integrate_with_api_v2_example():
    """
    Example integration code for api_v2.py
    
    Add this code to the process_pdf function in backend/app/api_v2.py
    after the database save step is completed.
    """
    
    # Example code to add to api_v2.py:
    
    """
    # After successful database save in process_pdf function:
    
    # Import the auto-analysis hook
    try:
        from tests.auto_analysis_hook import trigger_analysis
        
        # Trigger analysis for the completed wine list
        logger.info(f"Triggering extraction analysis for wine_list_id: {wine_list.id}")
        analysis_triggered = trigger_analysis(str(wine_list.id))
        
        if analysis_triggered:
            logger.info(f"Extraction analysis triggered successfully for {wine_list.id}")
        else:
            logger.warning(f"Failed to trigger extraction analysis for {wine_list.id}")
            
    except Exception as e:
        logger.error(f"Error triggering extraction analysis: {e}")
        # Don't fail the main process if analysis fails
    """
    
    logger.info("Integration example for api_v2.py provided")


def integrate_with_upload_endpoint_example():
    """
    Example integration code for the upload endpoint
    
    Add this code to the upload endpoint in backend/app/api_v2.py
    after successful processing.
    """
    
    # Example code to add to upload endpoint:
    
    """
    # After successful processing in upload endpoint:
    
    # Import the auto-analysis hook
    try:
        from tests.auto_analysis_hook import trigger_analysis
        
        # Trigger analysis for the completed wine list
        logger.info(f"Triggering extraction analysis for wine_list_id: {wine_list.id}")
        analysis_triggered = trigger_analysis(str(wine_list.id))
        
        if analysis_triggered:
            logger.info(f"Extraction analysis triggered successfully for {wine_list.id}")
        else:
            logger.warning(f"Failed to trigger extraction analysis for {wine_list.id}")
            
    except Exception as e:
        logger.error(f"Error triggering extraction analysis: {e}")
        # Don't fail the main process if analysis fails
    """
    
    logger.info("Integration example for upload endpoint provided")


def integrate_with_steps_status_example():
    """
    Example integration code that triggers analysis when steps_status indicates completion
    
    This can be added to any part of the pipeline that updates steps_status.
    """
    
    # Example code:
    
    """
    # After updating steps_status to completed:
    
    # Check if all steps are completed
    if wine_list.steps_status:
        all_completed = all(
            step.get('status') == 'completed' 
            for step in wine_list.steps_status.values()
        )
        
        if all_completed:
            try:
                from tests.auto_analysis_hook import trigger_analysis
                
                # Trigger analysis for the completed wine list
                logger.info(f"All steps completed, triggering analysis for {wine_list.id}")
                analysis_triggered = trigger_analysis(str(wine_list.id))
                
                if analysis_triggered:
                    logger.info(f"Extraction analysis triggered successfully for {wine_list.id}")
                else:
                    logger.warning(f"Failed to trigger extraction analysis for {wine_list.id}")
                    
            except Exception as e:
                logger.error(f"Error triggering extraction analysis: {e}")
    """
    
    logger.info("Integration example for steps_status provided")


def manual_analysis_example():
    """
    Example of how to manually run analysis for testing or debugging
    """
    
    # Example code:
    
    """
    # Manual analysis example
    
    from tests.run_extraction_test import run_extraction_analysis
    
    # Run analysis for a specific wine list
    wine_list_id = "your-wine-list-id-here"
    
    try:
        results = run_extraction_analysis(wine_list_id)
        
        print(f"Analysis completed for {wine_list_id}")
        print(f"Overall success rate: {results['overall_metrics']['overall_success_rate']:.2%}")
        print(f"Total entries: {results['overall_metrics']['total_entries']}")
        
        # Print recommendations
        for rec in results.get('recommendations', []):
            print(f"Recommendation: {rec}")
            
    except Exception as e:
        print(f"Error running analysis: {e}")
    """
    
    logger.info("Manual analysis example provided")


def batch_analysis_example():
    """
    Example of how to run analysis on multiple wine lists
    """
    
    # Example code:
    
    """
    # Batch analysis example
    
    from tests.run_extraction_test import run_extraction_analysis
    from app.database import get_db
    from app.models import WineListFile
    
    # Get all completed wine lists
    db = next(get_db())
    completed_wine_lists = db.query(WineListFile).filter(
        WineListFile.status == 'parsed'
    ).all()
    
    print(f"Found {len(completed_wine_lists)} completed wine lists")
    
    for wine_list in completed_wine_lists:
        try:
            print(f"Analyzing {wine_list.filename}...")
            results = run_extraction_analysis(str(wine_list.id))
            
            success_rate = results['overall_metrics']['overall_success_rate']
            total_entries = results['overall_metrics']['total_entries']
            
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Total entries: {total_entries}")
            
        except Exception as e:
            print(f"  Error analyzing {wine_list.filename}: {e}")
    
    db.close()
    """
    
    logger.info("Batch analysis example provided")


def monitoring_example():
    """
    Example of how to monitor the analysis system
    """
    
    # Example code:
    
    """
    # Monitoring example
    
    from tests.auto_analysis_hook import get_queue_status, get_auto_analysis_hook
    
    # Get current status
    status = get_queue_status()
    print(f"Auto-analysis enabled: {status['enabled']}")
    print(f"Async mode: {status['async_mode']}")
    print(f"Queue length: {status['queue_length']}")
    print(f"Worker alive: {status['worker_alive']}")
    
    # Get hook instance for more detailed monitoring
    hook = get_auto_analysis_hook()
    print(f"Analysis queue: {hook.analysis_queue}")
    """
    
    logger.info("Monitoring example provided")


def configuration_example():
    """
    Example of how to configure the analysis system
    """
    
    # Example code:
    
    """
    # Configuration example
    
    from tests.auto_analysis_hook import (
        enable_auto_analysis,
        disable_auto_analysis,
        set_async_mode,
        clear_analysis_queue
    )
    
    # Enable auto-analysis
    enable_auto_analysis()
    
    # Set to synchronous mode (blocking)
    set_async_mode(False)
    
    # Clear any pending analysis
    clear_analysis_queue()
    
    # Disable auto-analysis
    # disable_auto_analysis()
    """
    
    logger.info("Configuration example provided")


if __name__ == "__main__":
    print("Extraction Analysis Test System - Integration Examples")
    print("=" * 60)
    
    integrate_with_api_v2_example()
    print()
    
    integrate_with_upload_endpoint_example()
    print()
    
    integrate_with_steps_status_example()
    print()
    
    manual_analysis_example()
    print()
    
    batch_analysis_example()
    print()
    
    monitoring_example()
    print()
    
    configuration_example()
    print()
    
    print("Integration examples completed. See the code comments for implementation details.") 