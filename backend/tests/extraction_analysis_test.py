"""
Extraction Analysis Test System

This module provides comprehensive testing and analysis of wine list extraction results.
It analyzes the success of database entry extraction and provides detailed field assignment analysis.
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import application modules
from app.models import WineListFile, WineEntry, Restaurant
from app.database import get_db
from app.storage import get_processing_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractionAnalysisTest:
    """
    Comprehensive test system for analyzing wine list extraction results.
    
    This class provides:
    1. Success rate analysis for each field
    2. Field assignment analysis with confidence scores
    3. Failure analysis with reasons
    4. Performance metrics
    5. Detailed reports stored in organized folders
    """
    
    def __init__(self, output_dir: str = "extraction_analysis_output"):
        """
        Initialize the extraction analysis test system.
        
        Args:
            output_dir: Directory where analysis results will be stored
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different types of analysis
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.detailed_analysis_dir = self.output_dir / "detailed_analysis"
        self.detailed_analysis_dir.mkdir(exist_ok=True)
        
        self.failure_analysis_dir = self.output_dir / "failure_analysis"
        self.failure_analysis_dir.mkdir(exist_ok=True)
        
        self.performance_dir = self.output_dir / "performance"
        self.performance_dir.mkdir(exist_ok=True)
        
        logger.info(f"ExtractionAnalysisTest initialized with output directory: {self.output_dir}")
    
    def run_analysis(self, wine_list_id: str, db: Session) -> Dict[str, Any]:
        """
        Run comprehensive analysis on a completed wine list extraction.
        
        Args:
            wine_list_id: The ID of the wine list file to analyze
            db: Database session
            
        Returns:
            Dict containing comprehensive analysis results
        """
        logger.info(f"Starting extraction analysis for wine_list_id: {wine_list_id}")
        
        # Get wine list file
        wine_list = db.query(WineListFile).filter(WineListFile.id == wine_list_id).first()
        if not wine_list:
            raise ValueError(f"Wine list with ID {wine_list_id} not found")
        
        # Get all wine entries for this file
        wine_entries = db.query(WineEntry).filter(WineEntry.wine_list_file_id == wine_list_id).all()
        
        if not wine_entries:
            logger.warning(f"No wine entries found for wine_list_id: {wine_list_id}")
            return self._create_empty_analysis_result(wine_list)
        
        logger.info(f"Found {len(wine_entries)} wine entries to analyze")
        
        # Run comprehensive analysis
        analysis_results = {
            "wine_list_info": self._analyze_wine_list_info(wine_list),
            "overall_metrics": self._calculate_overall_metrics(wine_entries),
            "field_analysis": self._analyze_field_extraction(wine_entries),
            "confidence_analysis": self._analyze_confidence_scores(wine_entries),
            "failure_analysis": self._analyze_failures(wine_entries),
            "processing_analysis": self._analyze_processing_data(wine_list_id),
            "performance_metrics": self._calculate_performance_metrics(wine_list, wine_entries),
            "recommendations": self._generate_recommendations(wine_entries)
        }
        
        # Generate timestamp for this analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_results["analysis_timestamp"] = timestamp
        analysis_results["analysis_metadata"] = {
            "total_entries_analyzed": len(wine_entries),
            "wine_list_filename": wine_list.filename,
            "restaurant_id": str(wine_list.restaurant_id)
        }
        
        # Save detailed reports
        self._save_detailed_reports(analysis_results, wine_list_id, timestamp)
        
        # Save summary report
        self._save_summary_report(analysis_results, wine_list_id, timestamp)
        
        logger.info(f"Extraction analysis completed for wine_list_id: {wine_list_id}")
        return analysis_results
    
    def _analyze_wine_list_info(self, wine_list: WineListFile) -> Dict[str, Any]:
        """Analyze basic wine list file information."""
        return {
            "filename": wine_list.filename,
            "status": wine_list.status.value if wine_list.status else None,
            "uploaded_at": wine_list.uploaded_at.isoformat() if wine_list.uploaded_at else None,
            "parsed_date": wine_list.parsed_date.isoformat() if wine_list.parsed_date else None,
            "restaurant_id": str(wine_list.restaurant_id),
            "file_url": wine_list.file_url,
            "notes": wine_list.notes,
            "learning_results": wine_list.learning_results,
            "steps_status": wine_list.steps_status
        }
    
    def _calculate_overall_metrics(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Calculate overall extraction metrics."""
        total_entries = len(wine_entries)
        if total_entries == 0:
            return {"total_entries": 0, "success_rate": 0.0}
        
        # Define fields to analyze
        fields_to_analyze = [
            'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
            'grape_variety', 'country', 'region', 'subregion', 'designation',
            'classification', 'sub_type'
        ]
        
        # Calculate success rates for each field
        field_success_rates = {}
        for field in fields_to_analyze:
            successful_extractions = sum(1 for entry in wine_entries if getattr(entry, field))
            field_success_rates[field] = {
                "successful": successful_extractions,
                "total": total_entries,
                "success_rate": successful_extractions / total_entries if total_entries > 0 else 0.0
            }
        
        # Calculate overall success rate (average of all fields)
        overall_success_rate = sum(
            field_success_rates[field]["success_rate"] for field in fields_to_analyze
        ) / len(fields_to_analyze)
        
        return {
            "total_entries": total_entries,
            "overall_success_rate": overall_success_rate,
            "field_success_rates": field_success_rates,
            "entries_with_any_data": sum(1 for entry in wine_entries if any(getattr(entry, field) for field in fields_to_analyze)),
            "completely_empty_entries": sum(1 for entry in wine_entries if not any(getattr(entry, field) for field in fields_to_analyze))
        }
    
    def _analyze_field_extraction(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Analyze field extraction patterns and quality."""
        fields_to_analyze = [
            'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
            'grape_variety', 'country', 'region', 'subregion', 'designation',
            'classification', 'sub_type'
        ]
        
        field_analysis = {}
        
        for field in fields_to_analyze:
            field_values = [getattr(entry, field) for entry in wine_entries if getattr(entry, field)]
            
            # Basic statistics
            field_analysis[field] = {
                "total_extracted": len(field_values),
                "unique_values": len(set(field_values)),
                "most_common_values": self._get_most_common_values(field_values, top_n=5),
                "average_length": sum(len(str(v)) for v in field_values) / len(field_values) if field_values else 0,
                "confidence_stats": self._analyze_field_confidence(wine_entries, field)
            }
        
        return field_analysis
    
    def _analyze_confidence_scores(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Analyze confidence scores for field extraction."""
        confidence_analysis = {
            "row_confidence_stats": self._calculate_confidence_stats([entry.row_confidence for entry in wine_entries if entry.row_confidence]),
            "field_confidence_analysis": {}
        }
        
        # Analyze field-specific confidence scores
        fields_to_analyze = [
            'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
            'grape_variety', 'country', 'region', 'subregion', 'designation',
            'classification', 'sub_type'
        ]
        
        for field in fields_to_analyze:
            field_confidences = []
            for entry in wine_entries:
                if entry.field_confidence and field in entry.field_confidence:
                    field_confidences.append(entry.field_confidence[field])
            
            if field_confidences:
                confidence_analysis["field_confidence_analysis"][field] = self._calculate_confidence_stats(field_confidences)
        
        return confidence_analysis
    
    def _analyze_failures(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Analyze extraction failures and their potential causes."""
        fields_to_analyze = [
            'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
            'grape_variety', 'country', 'region', 'subregion', 'designation',
            'classification', 'sub_type'
        ]
        
        failure_analysis = {
            "failed_fields": {},
            "common_failure_patterns": [],
            "entries_with_multiple_failures": []
        }
        
        # Analyze failures by field
        for field in fields_to_analyze:
            failed_entries = [entry for entry in wine_entries if not getattr(entry, field)]
            if failed_entries:
                failure_analysis["failed_fields"][field] = {
                    "count": len(failed_entries),
                    "percentage": len(failed_entries) / len(wine_entries),
                    "sample_raw_texts": [entry.raw_text[:100] + "..." for entry in failed_entries[:5]]
                }
        
        # Find entries with multiple field failures
        for entry in wine_entries:
            failed_fields = [field for field in fields_to_analyze if not getattr(entry, field)]
            if len(failed_fields) >= 5:  # Consider it a major failure if 5+ fields failed
                failure_analysis["entries_with_multiple_failures"].append({
                    "entry_id": str(entry.id),
                    "failed_fields": failed_fields,
                    "raw_text": entry.raw_text,
                    "row_confidence": entry.row_confidence
                })
        
        return failure_analysis
    
    def _analyze_processing_data(self, wine_list_id: str) -> Dict[str, Any]:
        """Analyze processing data from storage if available."""
        try:
            # Try to get processing data from storage
            processing_data = {}
            
            # Get data from different processing stages
            stages = ["extractor", "preprocessor", "categorizer", "field_extractor"]
            for stage in stages:
                try:
                    stage_data = get_processing_data(wine_list_id, stage)
                    if stage_data:
                        processing_data[stage] = {
                            "available": True,
                            "data_keys": list(stage_data.keys()) if isinstance(stage_data, dict) else ["data"]
                        }
                    else:
                        processing_data[stage] = {"available": False}
                except Exception as e:
                    logger.warning(f"Could not retrieve {stage} data: {e}")
                    processing_data[stage] = {"available": False, "error": str(e)}
            
            return processing_data
            
        except Exception as e:
            logger.error(f"Error analyzing processing data: {e}")
            return {"error": str(e)}
    
    def _calculate_performance_metrics(self, wine_list: WineListFile, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Calculate performance metrics for the extraction process."""
        if not wine_list.uploaded_at or not wine_list.parsed_date:
            return {"processing_time": None, "entries_per_minute": None}
        
        processing_time = (wine_list.parsed_date - wine_list.uploaded_at).total_seconds()
        entries_per_minute = len(wine_entries) / (processing_time / 60) if processing_time > 0 else 0
        
        return {
            "processing_time_seconds": processing_time,
            "processing_time_minutes": processing_time / 60,
            "entries_per_minute": entries_per_minute,
            "entries_per_second": len(wine_entries) / processing_time if processing_time > 0 else 0
        }
    
    def _generate_recommendations(self, wine_entries: List[WineEntry]) -> List[str]:
        """Generate recommendations for improving extraction."""
        recommendations = []
        
        # Analyze field success rates
        fields_to_analyze = [
            'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
            'grape_variety', 'country', 'region', 'subregion', 'designation',
            'classification', 'sub_type'
        ]
        
        field_success_rates = {}
        for field in fields_to_analyze:
            successful = sum(1 for entry in wine_entries if getattr(entry, field))
            success_rate = successful / len(wine_entries) if wine_entries else 0
            field_success_rates[field] = success_rate
        
        # Generate specific recommendations
        low_success_fields = [field for field, rate in field_success_rates.items() if rate < 0.5]
        if low_success_fields:
            recommendations.append(f"Low extraction success for fields: {', '.join(low_success_fields)}. Consider improving extraction rules for these fields.")
        
        # Check for confidence issues
        low_confidence_entries = [entry for entry in wine_entries if entry.row_confidence and entry.row_confidence < 0.5]
        if low_confidence_entries:
            recommendations.append(f"{len(low_confidence_entries)} entries have low confidence scores (< 0.5). Review extraction quality for these entries.")
        
        # Check for completely empty entries
        empty_entries = [entry for entry in wine_entries if not any(getattr(entry, field) for field in fields_to_analyze)]
        if empty_entries:
            recommendations.append(f"{len(empty_entries)} entries have no extracted data. Review raw text for these entries to understand extraction failures.")
        
        if not recommendations:
            recommendations.append("Extraction quality appears good. No major issues detected.")
        
        return recommendations
    
    def _save_detailed_reports(self, analysis_results: Dict[str, Any], wine_list_id: str, timestamp: str):
        """Save detailed analysis reports to files."""
        # Save field analysis as CSV
        field_analysis_file = self.detailed_analysis_dir / f"field_analysis_{wine_list_id}_{timestamp}.csv"
        self._save_field_analysis_csv(analysis_results["field_analysis"], field_analysis_file)
        
        # Save failure analysis as JSON
        failure_analysis_file = self.failure_analysis_dir / f"failure_analysis_{wine_list_id}_{timestamp}.json"
        with open(failure_analysis_file, 'w') as f:
            json.dump(analysis_results["failure_analysis"], f, indent=2, default=str)
        
        # Save confidence analysis as JSON
        confidence_file = self.detailed_analysis_dir / f"confidence_analysis_{wine_list_id}_{timestamp}.json"
        with open(confidence_file, 'w') as f:
            json.dump(analysis_results["confidence_analysis"], f, indent=2, default=str)
        
        # Save performance metrics as JSON
        performance_file = self.performance_dir / f"performance_metrics_{wine_list_id}_{timestamp}.json"
        with open(performance_file, 'w') as f:
            json.dump(analysis_results["performance_metrics"], f, indent=2, default=str)
        
        logger.info(f"Detailed reports saved to {self.output_dir}")
    
    def _save_summary_report(self, analysis_results: Dict[str, Any], wine_list_id: str, timestamp: str):
        """Save a comprehensive summary report."""
        summary_file = self.reports_dir / f"extraction_summary_{wine_list_id}_{timestamp}.json"
        
        # Create a summary version with key metrics
        summary = {
            "analysis_timestamp": analysis_results["analysis_timestamp"],
            "wine_list_info": analysis_results["wine_list_info"],
            "overall_metrics": analysis_results["overall_metrics"],
            "key_findings": {
                "total_entries": analysis_results["overall_metrics"]["total_entries"],
                "overall_success_rate": analysis_results["overall_metrics"]["overall_success_rate"],
                "processing_time_minutes": analysis_results["performance_metrics"].get("processing_time_minutes"),
                "entries_per_minute": analysis_results["performance_metrics"].get("entries_per_minute")
            },
            "top_field_success_rates": self._get_top_field_success_rates(analysis_results["overall_metrics"]["field_success_rates"]),
            "recommendations": analysis_results["recommendations"]
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Summary report saved to {summary_file}")
    
    def _save_field_analysis_csv(self, field_analysis: Dict[str, Any], filepath: Path):
        """Save field analysis as CSV for easy review."""
        rows = []
        for field, analysis in field_analysis.items():
            row = {
                "field": field,
                "total_extracted": analysis["total_extracted"],
                "unique_values": analysis["unique_values"],
                "average_length": analysis["average_length"],
                "most_common_values": "; ".join([f"{v}:{c}" for v, c in analysis["most_common_values"]])
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
    
    def _get_most_common_values(self, values: List[str], top_n: int = 5) -> List[Tuple[str, int]]:
        """Get the most common values from a list."""
        from collections import Counter
        counter = Counter(values)
        return counter.most_common(top_n)
    
    def _analyze_field_confidence(self, wine_entries: List[WineEntry], field: str) -> Dict[str, Any]:
        """Analyze confidence scores for a specific field."""
        confidences = []
        for entry in wine_entries:
            if entry.field_confidence and field in entry.field_confidence:
                confidences.append(entry.field_confidence[field])
        
        if not confidences:
            return {"available": False}
        
        return {
            "available": True,
            "stats": self._calculate_confidence_stats(confidences)
        }
    
    def _calculate_confidence_stats(self, confidences: List[float]) -> Dict[str, float]:
        """Calculate statistics for confidence scores."""
        if not confidences:
            return {}
        
        return {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "count": len(confidences)
        }
    
    def _get_top_field_success_rates(self, field_success_rates: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get the top performing fields by success rate."""
        sorted_fields = sorted(
            field_success_rates.items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )
        
        return [
            {
                "field": field,
                "success_rate": data["success_rate"],
                "successful": data["successful"],
                "total": data["total"]
            }
            for field, data in sorted_fields[:top_n]
        ]
    
    def _create_empty_analysis_result(self, wine_list: WineListFile) -> Dict[str, Any]:
        """Create an empty analysis result when no wine entries are found."""
        return {
            "wine_list_info": self._analyze_wine_list_info(wine_list),
            "overall_metrics": {"total_entries": 0, "success_rate": 0.0},
            "field_analysis": {},
            "confidence_analysis": {},
            "failure_analysis": {},
            "processing_analysis": {},
            "performance_metrics": {},
            "recommendations": ["No wine entries found to analyze"],
            "analysis_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "analysis_metadata": {
                "total_entries_analyzed": 0,
                "wine_list_filename": wine_list.filename,
                "restaurant_id": str(wine_list.restaurant_id)
            }
        }


def run_extraction_analysis(wine_list_id: str, output_dir: str = "extraction_analysis_output") -> Dict[str, Any]:
    """
    Convenience function to run extraction analysis for a wine list.
    
    Args:
        wine_list_id: The ID of the wine list file to analyze
        output_dir: Directory where analysis results will be stored
        
    Returns:
        Dict containing comprehensive analysis results
    """
    analyzer = ExtractionAnalysisTest(output_dir)
    
    # Get database session
    db = next(get_db())
    try:
        results = analyzer.run_analysis(wine_list_id, db)
        return results
    finally:
        db.close()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python extraction_analysis_test.py <wine_list_id>")
        sys.exit(1)
    
    wine_list_id = sys.argv[1]
    results = run_extraction_analysis(wine_list_id)
    
    print("Extraction Analysis Complete!")
    print(f"Results saved to: extraction_analysis_output/")
    print(f"Overall success rate: {results['overall_metrics']['overall_success_rate']:.2%}")
    print(f"Total entries analyzed: {results['overall_metrics']['total_entries']}")
    print(f"Processing time: {results['performance_metrics'].get('processing_time_minutes', 'N/A'):.2f} minutes") 