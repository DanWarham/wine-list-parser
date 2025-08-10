#!/usr/bin/env python3
"""
Confidence Calculation Debug Test

This script analyzes confidence calculation issues across different extraction strategies
and identifies problems with confidence assignment that affect arbitration decisions.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.pdf_processing.extractor import PDFExtractor
from app.pdf_processing.preprocessor import PDFPreprocessor
from app.pdf_processing.categorizer import PDFBlockCategorizer
from app.fieldextractor.fieldextractor import FieldExtractor
from app.rules.rule_applicator import RuleApplicator
from app.rules.rule_manager import RuleManager
from app.database_enhanced_rules.early_extractor import EarlyExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfidenceCalculationAnalyzer:
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.pdf_preprocessor = PDFPreprocessor()
        self.pdf_categorizer = PDFBlockCategorizer()
        self.rule_applicator = RuleApplicator()
        self.early_extractor = EarlyExtractor()
        
    def analyze_confidence_issues(self, pdf_path: str, restaurant_id: str = "test-confidence-analysis"):
        """Analyze confidence calculation issues in detail."""
        logger.info(f"🔍 Starting confidence calculation analysis for {pdf_path}")
        
        # Step 1: Extract and preprocess PDF
        logger.info("📄 Step 1: Extracting PDF text...")
        try:
            pages, metadata = self.pdf_extractor.extract(pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return None
            
        if not pages:
            logger.error("No pages extracted from PDF")
            return None
            
        # Step 2: Preprocess text
        logger.info("🔧 Step 2: Preprocessing text...")
        preprocessed_pages = self.pdf_preprocessor.preprocess(pages)
        
        # Step 3: Categorize into wine blocks
        logger.info("🍷 Step 3: Categorizing wine blocks...")
        wine_blocks = self.pdf_categorizer.categorize(preprocessed_pages)
        
        logger.info(f"📊 Found {len(wine_blocks)} wine blocks")
        
        # Step 4: Analyze confidence issues
        confidence_analysis = self._analyze_confidence_by_strategy(wine_blocks, restaurant_id)
        
        # Step 5: Test rule application confidence
        rule_confidence_analysis = self._analyze_rule_confidence(wine_blocks, restaurant_id)
        
        # Step 6: Test field extractor confidence
        field_extractor_analysis = self._analyze_field_extractor_confidence(wine_blocks, restaurant_id)
        
        # Step 7: Test early database confidence
        early_db_analysis = self._analyze_early_database_confidence(wine_blocks)
        
        # Compile comprehensive analysis
        analysis_results = {
            "file_processed": os.path.basename(pdf_path),
            "restaurant_id": restaurant_id,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "wine_blocks_count": len(wine_blocks),
            "confidence_issues": confidence_analysis,
            "rule_confidence_analysis": rule_confidence_analysis,
            "field_extractor_analysis": field_extractor_analysis,
            "early_database_analysis": early_db_analysis,
            "recommendations": self._generate_recommendations(confidence_analysis, rule_confidence_analysis, field_extractor_analysis, early_db_analysis)
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"confidence_analysis_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)
            
        logger.info(f"💾 Analysis results saved to: {output_file}")
        
        # Print summary
        self._print_confidence_summary(analysis_results)
        
        return analysis_results
    
    def _analyze_confidence_by_strategy(self, wine_blocks: List[Dict[str, Any]], restaurant_id: str) -> Dict[str, Any]:
        """Analyze confidence calculation issues by strategy."""
        logger.info("🔍 Analyzing confidence by strategy...")
        
        field_extractor = FieldExtractor(restaurant_id=restaurant_id)
        confidence_issues = {
            "strategy_confidence_distribution": {},
            "low_confidence_fields": {},
            "confidence_inconsistencies": {},
            "strategy_agreement_issues": {},
            "sample_entries": []
        }
        
        # Analyze first 5 blocks in detail
        sample_blocks = wine_blocks[:5]
        
        for i, block in enumerate(sample_blocks):
            logger.info(f"📊 Analyzing block {i+1}/{len(sample_blocks)}")
            
            # Get individual strategy results
            strategy_results = {}
            for strategy in ['database', 'regex', 'ner', 'ai']:
                try:
                    if strategy == 'database':
                        # Test database strategy separately
                        db_result = self.early_extractor.extract_wine_info(block.get('text', ''))
                        strategy_results[strategy] = {
                            'fields': {
                                'grape_variety': {'value': db_result.get('grape_variety'), 'confidence': db_result.get('field_confidence', {}).get('grape_variety', 0.0)},
                                'producer_name': {'value': db_result.get('producer'), 'confidence': db_result.get('field_confidence', {}).get('producer', 0.0)},
                                'region': {'value': db_result.get('region'), 'confidence': db_result.get('field_confidence', {}).get('region', 0.0)},
                                'country': {'value': db_result.get('country'), 'confidence': db_result.get('field_confidence', {}).get('country', 0.0)}
                            },
                            'confidence': db_result.get('confidence', 0.0)
                        }
                    else:
                        # Use field extractor for other strategies
                        extractor = FieldExtractor(strategies=[strategy], restaurant_id=restaurant_id)
                        result = extractor.extract(block)
                        strategy_results[strategy] = {
                            'fields': result.get('fields', {}),
                            'confidence': result.get('confidence', 0.0)
                        }
                except Exception as e:
                    logger.error(f"Error testing {strategy} strategy: {e}")
                    strategy_results[strategy] = {'fields': {}, 'confidence': 0.0}
            
            # Analyze confidence distribution
            block_analysis = {
                "block_index": i,
                "text": block.get('text', '')[:100] + "...",
                "strategy_results": strategy_results,
                "confidence_issues": []
            }
            
            # Check for confidence issues
            for field_name in ['region', 'country', 'producer_name', 'wine_name', 'vintage', 'price', 'grape_variety']:
                field_confidences = {}
                for strategy, result in strategy_results.items():
                    fields = result.get('fields', {})
                    if field_name in fields:
                        field_data = fields[field_name]
                        if isinstance(field_data, dict):
                            field_confidences[strategy] = field_data.get('confidence', 0.0)
                        else:
                            field_confidences[strategy] = 0.0
                
                if field_confidences:
                    # Check for confidence inconsistencies
                    conf_values = list(field_confidences.values())
                    if max(conf_values) - min(conf_values) > 0.3:
                        block_analysis["confidence_issues"].append({
                            "field": field_name,
                            "issue": "high_confidence_variance",
                            "confidences": field_confidences,
                            "variance": max(conf_values) - min(conf_values)
                        })
                    
                    # Check for suspiciously high confidence
                    if any(conf > 0.95 for conf in conf_values):
                        block_analysis["confidence_issues"].append({
                            "field": field_name,
                            "issue": "suspiciously_high_confidence",
                            "confidences": field_confidences
                        })
                    
                    # Check for suspiciously low confidence
                    if all(conf < 0.3 for conf in conf_values):
                        block_analysis["confidence_issues"].append({
                            "field": field_name,
                            "issue": "suspiciously_low_confidence",
                            "confidences": field_confidences
                        })
            
            confidence_issues["sample_entries"].append(block_analysis)
        
        return confidence_issues
    
    def _analyze_rule_confidence(self, wine_blocks: List[Dict[str, Any]], restaurant_id: str) -> Dict[str, Any]:
        """Analyze rule application confidence issues."""
        logger.info("🔍 Analyzing rule application confidence...")
        
        rule_manager = RuleManager()
        rule_analysis = {
            "rule_confidence_distribution": {},
            "validation_confidence_issues": {},
            "threshold_issues": {},
            "sample_rule_applications": []
        }
        
        # Test with sample blocks
        sample_blocks = wine_blocks[:3]
        
        for i, block in enumerate(sample_blocks):
            logger.info(f"📊 Testing rule application on block {i+1}")
            
            # Test rule application with different confidence thresholds
            thresholds = [0.3, 0.5, 0.7, 0.9]
            threshold_results = {}
            
            for threshold in thresholds:
                try:
                    # Create a simple test rule
                    test_rules = {
                        "vintage": {
                            "regex_patterns": [r"\b(19|20)\d{2}\b"],
                            "confidence_threshold": threshold
                        },
                        "price": {
                            "regex_patterns": [r"(\d+(?:\.\d{2})?)\s*$"],
                            "confidence_threshold": threshold
                        }
                    }
                    
                    result = self.rule_applicator.apply_rules(block, test_rules)
                    threshold_results[threshold] = {
                        "fields_extracted": len(result.get('fields', {})),
                        "confidence": result.get('confidence', 0.0),
                        "fields": result.get('fields', {})
                    }
                    
                except Exception as e:
                    logger.error(f"Error testing threshold {threshold}: {e}")
                    threshold_results[threshold] = {"error": str(e)}
            
            rule_analysis["sample_rule_applications"].append({
                "block_index": i,
                "text": block.get('text', '')[:80] + "...",
                "threshold_results": threshold_results
            })
        
        return rule_analysis
    
    def _analyze_field_extractor_confidence(self, wine_blocks: List[Dict[str, Any]], restaurant_id: str) -> Dict[str, Any]:
        """Analyze field extractor confidence calculation."""
        logger.info("🔍 Analyzing field extractor confidence...")
        
        field_extractor = FieldExtractor(restaurant_id=restaurant_id)
        extractor_analysis = {
            "strategy_confidence_adjustments": {},
            "cross_strategy_boosting": {},
            "sample_extractions": []
        }
        
        # Test with sample blocks
        sample_blocks = wine_blocks[:3]
        
        for i, block in enumerate(sample_blocks):
            logger.info(f"📊 Testing field extractor on block {i+1}")
            
            try:
                result = field_extractor.extract(block)
                extractor_analysis["sample_extractions"].append({
                    "block_index": i,
                    "text": block.get('text', '')[:80] + "...",
                    "extracted_fields": result.get('fields', {}),
                    "overall_confidence": result.get('confidence', 0.0),
                    "provenance": result.get('provenance', 'unknown')
                })
                
                # Analyze field-level confidence
                for field_name, field_data in result.get('fields', {}).items():
                    if isinstance(field_data, dict):
                        confidence = field_data.get('confidence', 0.0)
                        provenance = field_data.get('provenance', 'unknown')
                        
                        if field_name not in extractor_analysis["strategy_confidence_adjustments"]:
                            extractor_analysis["strategy_confidence_adjustments"][field_name] = {}
                        
                        if provenance not in extractor_analysis["strategy_confidence_adjustments"][field_name]:
                            extractor_analysis["strategy_confidence_adjustments"][field_name][provenance] = []
                        
                        extractor_analysis["strategy_confidence_adjustments"][field_name][provenance].append(confidence)
                
            except Exception as e:
                logger.error(f"Error testing field extractor on block {i}: {e}")
        
        return extractor_analysis
    
    def _analyze_early_database_confidence(self, wine_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze early database extraction confidence."""
        logger.info("🔍 Analyzing early database confidence...")
        
        db_analysis = {
            "database_confidence_distribution": {},
            "high_confidence_matches": [],
            "low_confidence_matches": [],
            "sample_extractions": []
        }
        
        # Test with sample blocks
        sample_blocks = wine_blocks[:5]
        
        for i, block in enumerate(sample_blocks):
            logger.info(f"📊 Testing early database extraction on block {i+1}")
            
            try:
                result = self.early_extractor.extract_wine_info(block.get('text', ''))
                
                db_analysis["sample_extractions"].append({
                    "block_index": i,
                    "text": block.get('text', '')[:80] + "...",
                    "confidence": result.get('confidence', 0.0),
                    "fields": result.get('fields', {}),
                    "skip_ai": result.get('skip_ai', False)
                })
                
                # Categorize by confidence level
                confidence = result.get('confidence', 0.0)
                if confidence > 0.8:
                    db_analysis["high_confidence_matches"].append({
                        "block_index": i,
                        "confidence": confidence,
                        "fields": result.get('fields', {})
                    })
                elif confidence < 0.3:
                    db_analysis["low_confidence_matches"].append({
                        "block_index": i,
                        "confidence": confidence,
                        "fields": result.get('fields', {})
                    })
                
            except Exception as e:
                logger.error(f"Error testing early database extraction on block {i}: {e}")
        
        return db_analysis
    
    def _generate_recommendations(self, confidence_analysis: Dict[str, Any], 
                                rule_analysis: Dict[str, Any], 
                                field_analysis: Dict[str, Any], 
                                db_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for fixing confidence calculation issues."""
        recommendations = []
        
        # Analyze confidence issues
        sample_entries = confidence_analysis.get("sample_entries", [])
        confidence_issues_count = sum(len(entry.get("confidence_issues", [])) for entry in sample_entries)
        
        if confidence_issues_count > 0:
            recommendations.append(f"Found {confidence_issues_count} confidence calculation issues in sample entries")
            recommendations.append("Consider implementing confidence normalization across strategies")
            recommendations.append("Review strategy-specific confidence adjustments")
        
        # Analyze rule confidence
        rule_applications = rule_analysis.get("sample_rule_applications", [])
        if rule_applications:
            recommendations.append("Rule confidence thresholds may need adjustment based on field type")
            recommendations.append("Consider implementing dynamic confidence thresholds")
        
        # Analyze field extractor
        field_extractions = field_analysis.get("sample_extractions", [])
        if field_extractions:
            recommendations.append("Cross-strategy confidence boosting may need refinement")
            recommendations.append("Consider implementing field-specific confidence models")
        
        # Analyze database confidence
        db_extractions = db_analysis.get("sample_extractions", [])
        if db_extractions:
            high_conf_count = len(db_analysis.get("high_confidence_matches", []))
            low_conf_count = len(db_analysis.get("low_confidence_matches", []))
            
            if high_conf_count > 0:
                recommendations.append(f"Database extraction shows {high_conf_count} high-confidence matches")
            if low_conf_count > 0:
                recommendations.append(f"Database extraction shows {low_conf_count} low-confidence matches")
        
        if not recommendations:
            recommendations.append("No major confidence calculation issues detected")
        
        return recommendations
    
    def _print_confidence_summary(self, analysis_results: Dict[str, Any]):
        """Print a summary of confidence analysis results."""
        print("\n" + "="*80)
        print("🔍 CONFIDENCE CALCULATION ANALYSIS SUMMARY")
        print("="*80)
        
        print(f"📄 File: {analysis_results['file_processed']}")
        print(f"🏪 Restaurant ID: {analysis_results['restaurant_id']}")
        print(f"🍷 Wine Blocks: {analysis_results['wine_blocks_count']}")
        print(f"⏰ Analysis Time: {analysis_results['analysis_timestamp']}")
        
        # Confidence issues summary
        confidence_issues = analysis_results.get("confidence_issues", {})
        sample_entries = confidence_issues.get("sample_entries", [])
        total_issues = sum(len(entry.get("confidence_issues", [])) for entry in sample_entries)
        
        print(f"\n🔧 CONFIDENCE ISSUES DETECTED: {total_issues}")
        
        if total_issues > 0:
            print("   Issues found in sample entries:")
            for entry in sample_entries:
                issues = entry.get("confidence_issues", [])
                if issues:
                    print(f"   - Block {entry['block_index']}: {len(issues)} issues")
                    for issue in issues[:2]:  # Show first 2 issues
                        print(f"     * {issue['field']}: {issue['issue']}")
        
        # Recommendations
        recommendations = analysis_results.get("recommendations", [])
        print(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
        for rec in recommendations:
            print(f"   • {rec}")
        
        print("\n" + "="*80)
        print("✅ Confidence calculation analysis completed!")
        print("="*80)

def main():
    """Main function to run confidence calculation analysis."""
    if len(sys.argv) < 2:
        print("Usage: python test_confidence_calculation.py <pdf_file_path>")
        print("Example: python test_confidence_calculation.py backend/tests/real-files/Sager\\ \\&\\ Wilde-Test1.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    analyzer = ConfidenceCalculationAnalyzer()
    results = analyzer.analyze_confidence_issues(pdf_path)
    
    if results:
        print(f"\n🎯 Analysis completed successfully!")
        print(f"📊 Check the generated JSON file for detailed results.")
    else:
        print(f"\n❌ Analysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 