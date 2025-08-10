#!/usr/bin/env python3
"""
Comprehensive test script to process the complex "the-10-cases.pdf" file
and analyze the output with respect to recent changes and issues.
"""

import os
import sys
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import traceback

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models import Restaurant, WineListFile, WineListFileStatus, WineEntry
from app.api_v2 import process_pdf
from app.storage import save_file
from fastapi import UploadFile
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComplexFileAnalyzer:
    def __init__(self):
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "file_info": {},
            "extraction_results": {},
            "quality_analysis": {},
            "issues_found": [],
            "recommendations": []
        }
    
    async def create_mock_upload_file(self, file_path: str) -> UploadFile:
        """Create a mock UploadFile object from a file path."""
        filename = os.path.basename(file_path)
        
        class MockUploadFile:
            def __init__(self, file_path: str, filename: str):
                self.file_path = file_path
                self.filename = filename
                self.content_type = "application/pdf"
                self.size = os.path.getsize(file_path)
            
            async def read(self):
                with open(self.file_path, 'rb') as f:
                    return f.read()
        
        return MockUploadFile(file_path, filename)
    
    async def get_or_create_restaurant(self, db, name: str = "Ten Cases") -> Restaurant:
        """Get or create restaurant for testing."""
        restaurant = db.query(Restaurant).filter(Restaurant.name == name).first()
        if not restaurant:
            restaurant = Restaurant(
                name=name,
                location="London",
                cuisine_type="Wine Bar",
                description="Test restaurant for complex file analysis"
            )
            db.add(restaurant)
            db.commit()
            db.refresh(restaurant)
        return restaurant
    
    def analyze_extraction_quality(self, extracted_fields: List[Dict], wine_blocks: List[Dict]) -> Dict:
        """Analyze the quality of extracted fields."""
        analysis = {
            "total_entries": len(extracted_fields),
            "total_blocks": len(wine_blocks),
            "field_completion_rates": {},
            "confidence_distribution": {},
            "common_issues": [],
            "sample_entries": []
        }
        
        if not extracted_fields:
            analysis["common_issues"].append("No fields extracted")
            return analysis
        
        # Analyze field completion rates
        field_names = ['producer_name', 'wine_name', 'vintage', 'price', 'grape_variety', 
                      'country', 'region', 'type', 'bottle_size']
        
        for field in field_names:
            completed = sum(1 for entry in extracted_fields if entry and entry.get(field))
            rate = (completed / len(extracted_fields)) * 100 if extracted_fields else 0
            analysis["field_completion_rates"][field] = {
                "completed": completed,
                "total": len(extracted_fields),
                "rate": round(rate, 2)
            }
        
        # Analyze confidence distribution
        confidences = []
        for entry in extracted_fields:
            if entry and 'confidence' in entry:
                confidences.append(entry['confidence'])
        
        if confidences:
            analysis["confidence_distribution"] = {
                "min": min(confidences),
                "max": max(confidences),
                "avg": sum(confidences) / len(confidences),
                "high_confidence": sum(1 for c in confidences if c >= 0.8),
                "medium_confidence": sum(1 for c in confidences if 0.5 <= c < 0.8),
                "low_confidence": sum(1 for c in confidences if c < 0.5)
            }
        
        # Sample entries for manual review
        sample_size = min(5, len(extracted_fields))
        analysis["sample_entries"] = extracted_fields[:sample_size]
        
        return analysis
    
    def identify_issues(self, extracted_fields: List[Dict], wine_blocks: List[Dict], 
                       learning_results: Dict) -> List[str]:
        """Identify potential issues in the extraction."""
        issues = []
        
        # Check for empty extractions
        if not extracted_fields:
            issues.append("No fields extracted from PDF")
        
        # Check for low completion rates
        if extracted_fields:
            completion_rates = {}
            field_names = ['producer_name', 'wine_name', 'vintage', 'price']
            
            for field in field_names:
                completed = sum(1 for entry in extracted_fields if entry and entry.get(field))
                rate = (completed / len(extracted_fields)) * 100
                completion_rates[field] = rate
                
                if rate < 50:
                    issues.append(f"Low completion rate for {field}: {rate:.1f}%")
        
        # Check for confidence issues
        if extracted_fields:
            low_confidence_count = sum(1 for entry in extracted_fields 
                                     if entry and entry.get('confidence', 1.0) < 0.5)
            if low_confidence_count > len(extracted_fields) * 0.3:
                issues.append(f"High number of low-confidence extractions: {low_confidence_count}")
        
        # Check learning results
        if learning_results:
            if 'rules_generated' in learning_results:
                if learning_results['rules_generated'] == 0:
                    issues.append("No rules generated during learning")
            
            if 'confidence_improvement' in learning_results:
                if learning_results['confidence_improvement'] < 0.1:
                    issues.append("Minimal confidence improvement from learning")
        
        return issues
    
    def generate_recommendations(self, analysis: Dict, issues: List[str]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Based on completion rates
        for field, stats in analysis.get("field_completion_rates", {}).items():
            if stats["rate"] < 70:
                recommendations.append(f"Improve extraction strategy for {field} field")
        
        # Based on confidence
        conf_dist = analysis.get("confidence_distribution", {})
        if conf_dist.get("low_confidence", 0) > conf_dist.get("high_confidence", 0):
            recommendations.append("Focus on improving confidence scoring and validation")
        
        # Based on issues
        if "No rules generated" in str(issues):
            recommendations.append("Enhance rule generation algorithm")
        
        if "low completion rate" in str(issues).lower():
            recommendations.append("Review and improve field extraction patterns")
        
        return recommendations
    
    async def process_complex_file(self, file_path: str) -> Dict:
        """Process the complex file and return comprehensive analysis."""
        logger.info(f"Starting comprehensive analysis of {file_path}")
        
        try:
            # Get database session
            db = next(get_db())
            
            # Get or create restaurant
            restaurant = await self.get_or_create_restaurant(db)
            
            # Create mock upload file
            upload_file = await self.create_mock_upload_file(file_path)
            
            # Save file to storage
            file_url = await save_file(upload_file, f"wine-lists/{restaurant.id}")
            if not file_url:
                raise Exception("Failed to save file")
            
            # Create wine list entry
            wine_list = WineListFile(
                restaurant_id=restaurant.id,
                filename=upload_file.filename,
                file_url=file_url,
                status=WineListFileStatus.processing,
                metadata={}
            )
            db.add(wine_list)
            db.commit()
            db.refresh(wine_list)
            
            logger.info(f"Created wine list entry: {wine_list.id}")
            
            # Process the PDF
            logger.info("Processing PDF with enhanced pipeline...")
            extracted_fields, metadata, learning_results, wine_blocks = await process_pdf(
                file_path, 
                str(restaurant.id), 
                str(wine_list.id), 
                db
            )
            
            # Update wine list with results
            wine_list.status = WineListFileStatus.parsed
            wine_list.metadata = metadata
            wine_list.learning_results = learning_results
            wine_list.learning_date = datetime.utcnow()
            wine_list.parsed_date = datetime.utcnow()
            db.commit()
            
            # Analyze results
            logger.info("Analyzing extraction quality...")
            quality_analysis = self.analyze_extraction_quality(extracted_fields, wine_blocks)
            
            # Identify issues
            logger.info("Identifying potential issues...")
            issues = self.identify_issues(extracted_fields, wine_blocks, learning_results)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(quality_analysis, issues)
            
            # Compile results
            self.analysis_results.update({
                "file_info": {
                    "filename": upload_file.filename,
                    "file_size": upload_file.size,
                    "restaurant": restaurant.name,
                    "wine_list_id": str(wine_list.id)
                },
                "extraction_results": {
                    "total_extracted": len(extracted_fields),
                    "total_blocks": len(wine_blocks),
                    "metadata": metadata,
                    "learning_results": learning_results
                },
                "quality_analysis": quality_analysis,
                "issues_found": issues,
                "recommendations": recommendations
            })
            
            # Save sample entries to database for review
            logger.info("Saving sample entries to database...")
            self.save_sample_entries(db, wine_list, restaurant, extracted_fields, wine_blocks)
            
            logger.info("Analysis completed successfully")
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            logger.error(traceback.format_exc())
            self.analysis_results["error"] = str(e)
            return self.analysis_results
    
    def save_sample_entries(self, db, wine_list, restaurant, extracted_fields, wine_blocks):
        """Save sample entries to database for manual review."""
        def extract_value(field_data):
            if field_data is None:
                return None
            elif isinstance(field_data, dict):
                return field_data.get('value')
            else:
                return str(field_data)
        
        for i, entry in enumerate(extracted_fields[:10]):  # Save first 10 entries
            if entry is None:
                continue
                
            raw_text = wine_blocks[i].get('text') if i < len(wine_blocks) else None
            
            wine_entry = WineEntry(
                wine_list_file_id=wine_list.id,
                restaurant_id=restaurant.id,
                producer=extract_value(entry.get('producer_name') or entry.get('producer_title')),
                cuvee=extract_value(entry.get('wine_name')),
                type=extract_value(entry.get('type')),
                vintage=extract_value(entry.get('vintage')),
                price=extract_value(entry.get('price')),
                bottle_size=extract_value(entry.get('bottle_size')),
                grape_variety=extract_value(entry.get('grape_variety')),
                country=extract_value(entry.get('country')),
                region=extract_value(entry.get('region')),
                subregion=extract_value(entry.get('sub_region')),
                row_confidence=extract_value(entry.get('row_confidence')) or entry.get('confidence', 0.0),
                field_confidence=entry.get('field_confidence') if entry.get('field_confidence') is not None else {},
                section_header=extract_value(entry.get('section_header')),
                subheader=extract_value(entry.get('subheader')),
                raw_text=raw_text,
                status=None,
                designation=extract_value(entry.get('designation')),
                classification=extract_value(entry.get('classification')),
                sub_type=extract_value(entry.get('sub_type'))
            )
            db.add(wine_entry)
        
        db.commit()
        logger.info(f"Saved {min(10, len(extracted_fields))} sample entries to database")

async def main():
    """Main function to run the complex file analysis."""
    logger.info("Starting comprehensive analysis of 'the-10-cases.pdf'")
    
    # File path
    file_path = r"C:\Users\Dan\Projects\wine-list-parser\backend\tests\real-files\Full Files\the-10-cases.pdf"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    # Create analyzer and process file
    analyzer = ComplexFileAnalyzer()
    results = await analyzer.process_complex_file(file_path)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"complex_analysis_the_10_cases_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("COMPREHENSIVE ANALYSIS SUMMARY")
    logger.info("="*60)
    
    if "error" in results:
        logger.error(f"❌ Analysis failed: {results['error']}")
        return
    
    file_info = results["file_info"]
    extraction_results = results["extraction_results"]
    quality_analysis = results["quality_analysis"]
    
    logger.info(f"📄 File: {file_info['filename']}")
    logger.info(f"🏪 Restaurant: {file_info['restaurant']}")
    logger.info(f"📊 Extracted entries: {extraction_results['total_extracted']}")
    logger.info(f"📋 Total blocks: {extraction_results['total_blocks']}")
    
    # Field completion summary
    logger.info("\n📈 Field Completion Rates:")
    for field, stats in quality_analysis.get("field_completion_rates", {}).items():
        logger.info(f"  {field}: {stats['rate']}% ({stats['completed']}/{stats['total']})")
    
    # Confidence summary
    conf_dist = quality_analysis.get("confidence_distribution", {})
    if conf_dist:
        logger.info(f"\n🎯 Confidence Distribution:")
        logger.info(f"  Average: {conf_dist.get('avg', 0):.3f}")
        logger.info(f"  High (≥0.8): {conf_dist.get('high_confidence', 0)}")
        logger.info(f"  Medium (0.5-0.8): {conf_dist.get('medium_confidence', 0)}")
        logger.info(f"  Low (<0.5): {conf_dist.get('low_confidence', 0)}")
    
    # Issues and recommendations
    if results["issues_found"]:
        logger.info(f"\n⚠️  Issues Found ({len(results['issues_found'])}):")
        for issue in results["issues_found"]:
            logger.info(f"  • {issue}")
    
    if results["recommendations"]:
        logger.info(f"\n💡 Recommendations ({len(results['recommendations'])}):")
        for rec in results["recommendations"]:
            logger.info(f"  • {rec}")
    
    logger.info(f"\n📁 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main()) 