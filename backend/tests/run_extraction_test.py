"""
Test Runner for Extraction Analysis

This script can be called automatically when a wine list file completes processing
to run comprehensive extraction analysis and generate detailed reports.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from extraction_analysis_test import ExtractionAnalysisTest, run_extraction_analysis
from app.database import get_db
from app.models import WineListFile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run extraction analysis."""
    parser = argparse.ArgumentParser(description='Run extraction analysis for a wine list file')
    parser.add_argument('wine_list_id', help='The ID of the wine list file to analyze')
    parser.add_argument('--output-dir', default='extraction_analysis_output', 
                       help='Directory where analysis results will be stored')
    parser.add_argument('--auto-run', action='store_true', 
                       help='Automatically run analysis when called')
    
    args = parser.parse_args()
    
    logger.info(f"Starting extraction analysis for wine_list_id: {args.wine_list_id}")
    logger.info(f"Output directory: {args.output_dir}")
    
    try:
        # Run the analysis
        results = run_extraction_analysis(args.wine_list_id, args.output_dir)
        
        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION ANALYSIS COMPLETE")
        print("="*60)
        print(f"Wine List ID: {args.wine_list_id}")
        print(f"Filename: {results['wine_list_info']['filename']}")
        print(f"Total Entries: {results['overall_metrics']['total_entries']}")
        print(f"Overall Success Rate: {results['overall_metrics']['overall_success_rate']:.2%}")
        
        if results['performance_metrics'].get('processing_time_minutes'):
            print(f"Processing Time: {results['performance_metrics']['processing_time_minutes']:.2f} minutes")
            print(f"Entries per Minute: {results['performance_metrics'].get('entries_per_minute', 0):.2f}")
        
        print(f"\nTop Performing Fields:")
        for field_info in results.get('top_field_success_rates', [])[:3]:
            print(f"  {field_info['field']}: {field_info['success_rate']:.2%}")
        
        print(f"\nRecommendations:")
        for rec in results.get('recommendations', []):
            print(f"  • {rec}")
        
        print(f"\nDetailed reports saved to: {args.output_dir}/")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error running extraction analysis: {e}")
        print(f"ERROR: {e}")
        return 1


def auto_run_analysis(wine_list_id: str) -> bool:
    """
    Function to be called automatically when a file completes processing.
    
    Args:
        wine_list_id: The ID of the wine list file that completed processing
        
    Returns:
        bool: True if analysis completed successfully, False otherwise
    """
    try:
        logger.info(f"Auto-running extraction analysis for wine_list_id: {wine_list_id}")
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"extraction_analysis_output/auto_run_{wine_list_id}_{timestamp}"
        
        # Ensure the base directory exists
        Path("extraction_analysis_output").mkdir(exist_ok=True)
        
        # Run analysis - ExtractionAnalysisTest will create the subdirectories
        results = run_extraction_analysis(wine_list_id, output_dir)
        
        # Log success
        logger.info(f"Auto-analysis completed successfully for {wine_list_id}")
        logger.info(f"Results saved to: {output_dir}")
        logger.info(f"Overall success rate: {results['overall_metrics']['overall_success_rate']:.2%}")
        
        return True
        
    except Exception as e:
        logger.error(f"Auto-analysis failed for {wine_list_id}: {e}")
        return False


def check_wine_list_status(wine_list_id: str) -> bool:
    """
    Check if a wine list file has completed processing and is ready for analysis.
    
    Args:
        wine_list_id: The ID of the wine list file to check
        
    Returns:
        bool: True if ready for analysis, False otherwise
    """
    try:
        db = next(get_db())
        wine_list = db.query(WineListFile).filter(WineListFile.id == wine_list_id).first()
        
        if not wine_list:
            logger.warning(f"Wine list {wine_list_id} not found")
            return False
        
        # Check if processing is complete
        if wine_list.status.value == 'parsed':
            logger.info(f"Wine list {wine_list_id} is ready for analysis")
            return True
        elif wine_list.status.value == 'error':
            logger.warning(f"Wine list {wine_list_id} has error status")
            return False
        else:
            logger.info(f"Wine list {wine_list_id} still processing (status: {wine_list.status.value})")
            return False
            
    except Exception as e:
        logger.error(f"Error checking wine list status: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main()) 