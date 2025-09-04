"""
Analysis Service for handling wine list extraction analysis and confidence calculations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .base_service import BaseService
from app.models import WineListFile, WineEntry, WineEntryStatus
from app.rules.confidence_calculator import ConfidenceCalculator
from app.rules.intelligent_sampler import IntelligentSampler
# Integrate with contracts
from app.contracts import DataProcessor

logger = logging.getLogger(__name__)


class AnalysisService(BaseService, DataProcessor):
    """Service for handling wine list extraction analysis and confidence calculations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.confidence_calculator = ConfidenceCalculator()
        self.intelligent_sampler = IntelligentSampler()
    
    # Implement DataProcessor contract methods
    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process data for analysis (implements DataProcessor contract)."""
        if isinstance(data, str) and data.startswith('file_id:'):
            file_id = data.replace('file_id:', '')
            user_id = context.get('user_id') if context else None
            if not user_id:
                raise ValueError("user_id required in context for file analysis")
            return await self.analyze_extraction_quality(file_id, user_id)
        elif isinstance(data, dict) and 'file_id' in data:
            user_id = context.get('user_id') if context else None
            if not user_id:
                raise ValueError("user_id required in context for file analysis")
            return await self.analyze_extraction_quality(data['file_id'], user_id)
        else:
            raise ValueError("Data must be file_id string or dict with file_id")
    
    async def validate_result(self, result: Any) -> bool:
        """Validate analysis result (implements DataProcessor contract)."""
        if not isinstance(result, dict):
            return False
        
        required_keys = ['file_id', 'total_entries', 'quality_score', 'analysis_timestamp']
        return all(key in result for key in required_keys)
    
    async def analyze_extraction_quality(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """Analyze the quality of wine list extraction and provide insights."""
        try:
            # Get wine list file
            wine_list = self.db.query(WineListFile).filter(WineListFile.id == file_id).first()
            if not wine_list:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Wine list file not found"
                )
            
            # Get all wine entries for this file
            wine_entries = self.db.query(WineEntry).filter(
                WineEntry.wine_list_file_id == file_id
            ).all()
            
            if not wine_entries:
                return {
                    'file_id': file_id,
                    'total_entries': 0,
                    'analysis': 'No wine entries found for analysis'
                }
            
            # Analyze confidence distribution
            confidence_analysis = self._analyze_confidence_distribution(wine_entries)
            
            # Analyze field extraction quality
            field_analysis = self._analyze_field_extraction_quality(wine_entries)
            
            # Identify potential issues
            issues = self._identify_extraction_issues(wine_entries)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(confidence_analysis, field_analysis, issues)
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(confidence_analysis, field_analysis, issues)
            
            analysis_result = {
                'file_id': file_id,
                'restaurant_id': str(wine_list.restaurant_id),
                'total_entries': len(wine_entries),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'quality_score': quality_score,
                'confidence_analysis': confidence_analysis,
                'field_analysis': field_analysis,
                'identified_issues': issues,
                'recommendations': recommendations,
                'processing_metadata': {
                    'file_status': wine_list.status.value,
                    'uploaded_at': wine_list.uploaded_at.isoformat(),
                    'parsed_date': wine_list.parsed_date.isoformat() if wine_list.parsed_date else None
                }
            }
            
            # Store analysis results in wine list file
            if not wine_list.learning_results:
                wine_list.learning_results = {}
            
            wine_list.learning_results['extraction_analysis'] = analysis_result
            wine_list.learning_results['last_analysis'] = datetime.utcnow().isoformat()
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action="analyzed_extraction_quality",
                entity_type="wine_list_file",
                entity_id=file_id,
                new_value={'quality_score': quality_score, 'total_entries': len(wine_entries)}
            )
            
            return analysis_result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to analyze extraction quality: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze extraction quality"
            )
    
    def _analyze_confidence_distribution(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Analyze the distribution of confidence scores across wine entries."""
        confidence_scores = [entry.row_confidence or 0.0 for entry in wine_entries]
        
        if not confidence_scores:
            return {'error': 'No confidence scores available'}
        
        # Calculate statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        
        # Categorize by confidence levels
        high_confidence = len([c for c in confidence_scores if c >= 0.8])
        medium_confidence = len([c for c in confidence_scores if 0.5 <= c < 0.8])
        low_confidence = len([c for c in confidence_scores if c < 0.5])
        
        # Identify confidence gaps
        confidence_gaps = []
        sorted_scores = sorted(confidence_scores)
        for i in range(len(sorted_scores) - 1):
            gap = sorted_scores[i + 1] - sorted_scores[i]
            if gap > 0.2:  # Significant gap threshold
                confidence_gaps.append({
                    'position': i,
                    'gap_size': gap,
                    'lower_bound': sorted_scores[i],
                    'upper_bound': sorted_scores[i + 1]
                })
        
        return {
            'total_entries': len(confidence_scores),
            'statistics': {
                'average': round(avg_confidence, 3),
                'minimum': round(min_confidence, 3),
                'maximum': round(max_confidence, 3),
                'standard_deviation': round(self._calculate_standard_deviation(confidence_scores), 3)
            },
            'distribution': {
                'high_confidence': {'count': high_confidence, 'percentage': round(high_confidence / len(confidence_scores) * 100, 1)},
                'medium_confidence': {'count': medium_confidence, 'percentage': round(medium_confidence / len(confidence_scores) * 100, 1)},
                'low_confidence': {'count': low_confidence, 'percentage': round(low_confidence / len(confidence_scores) * 100, 1)}
            },
            'confidence_gaps': confidence_gaps
        }
    
    def _analyze_field_extraction_quality(self, wine_entries: List[WineEntry]) -> Dict[str, Any]:
        """Analyze the quality of individual field extractions."""
        field_stats = {}
        total_entries = len(wine_entries)
        
        # Define important fields to analyze
        important_fields = ['producer', 'cuvee', 'type', 'vintage', 'price', 'grape_variety', 'country', 'region']
        
        for field in important_fields:
            field_values = []
            field_confidences = []
            
            for entry in wine_entries:
                # Get field value
                field_value = getattr(entry, field, None)
                if field_value:
                    field_values.append(field_value)
                
                # Get field confidence if available
                if entry.field_confidence and field in entry.field_confidence:
                    field_confidences.append(entry.field_confidence[field])
            
            # Calculate field statistics
            extraction_rate = len(field_values) / total_entries if total_entries > 0 else 0
            avg_confidence = sum(field_confidences) / len(field_confidences) if field_confidences else 0
            
            field_stats[field] = {
                'extraction_rate': round(extraction_rate, 3),
                'extracted_count': len(field_values),
                'missing_count': total_entries - len(field_values),
                'average_confidence': round(avg_confidence, 3) if field_confidences else None,
                'unique_values': len(set(field_values)) if field_values else 0
            }
        
        return {
            'total_entries': total_entries,
            'field_statistics': field_stats,
            'overall_extraction_rate': round(sum([stats['extraction_rate'] for stats in field_stats.values()]) / len(field_stats), 3)
        }
    
    def _identify_extraction_issues(self, wine_entries: List[WineEntry]) -> List[Dict[str, Any]]:
        """Identify potential issues in the extraction results."""
        issues = []
        
        # Check for entries with very low confidence
        low_confidence_entries = [entry for entry in wine_entries if (entry.row_confidence or 0) < 0.3]
        if low_confidence_entries:
            issues.append({
                'type': 'low_confidence',
                'severity': 'high',
                'description': f"{len(low_confidence_entries)} entries have very low confidence (< 0.3)",
                'affected_entries': [str(entry.id) for entry in low_confidence_entries[:5]],  # Limit to first 5
                'recommendation': 'Review these entries manually or adjust extraction rules'
            })
        
        # Check for missing critical fields
        critical_fields = ['producer', 'cuvee', 'type']
        for field in critical_fields:
            missing_field_entries = [entry for entry in wine_entries if not getattr(entry, field, None)]
            if len(missing_field_entries) > len(wine_entries) * 0.5:  # More than 50% missing
                issues.append({
                    'type': 'missing_critical_field',
                    'severity': 'medium',
                    'description': f"Critical field '{field}' is missing in {len(missing_field_entries)} entries",
                    'affected_entries': [str(entry.id) for entry in missing_field_entries[:5]],
                    'recommendation': f'Improve extraction rules for field "{field}"'
                })
        
        # Check for inconsistent data patterns
        producer_patterns = {}
        for entry in wine_entries:
            if entry.producer:
                producer_patterns[entry.producer] = producer_patterns.get(entry.producer, 0) + 1
        
        # Flag if too many unique producers (might indicate extraction issues)
        if len(producer_patterns) > len(wine_entries) * 0.8:  # More than 80% unique producers
            issues.append({
                'type': 'inconsistent_producer_extraction',
                'severity': 'medium',
                'description': f"High number of unique producers ({len(producer_patterns)}) suggests extraction inconsistencies",
                'affected_entries': [],
                'recommendation': 'Review producer extraction rules and consider standardization'
            })
        
        return issues
    
    def _generate_recommendations(self, confidence_analysis: Dict, field_analysis: Dict, 
                                issues: List[Dict]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Confidence-based recommendations
        if confidence_analysis.get('distribution', {}).get('low_confidence', {}).get('percentage', 0) > 30:
            recommendations.append({
                'priority': 'high',
                'category': 'confidence',
                'title': 'Improve Low Confidence Entries',
                'description': 'More than 30% of entries have low confidence scores',
                'action': 'Review and refine extraction rules, consider AI-assisted extraction for low-confidence entries',
                'expected_impact': 'Increase overall extraction quality by 15-25%'
            })
        
        # Field extraction recommendations
        for field, stats in field_analysis.get('field_statistics', {}).items():
            if stats['extraction_rate'] < 0.7:  # Less than 70% extraction rate
                recommendations.append({
                    'priority': 'medium',
                    'category': 'field_extraction',
                    'title': f'Improve {field.title()} Extraction',
                    'description': f'Only {stats["extraction_rate"]*100:.1f}% of entries have {field} extracted',
                    'action': f'Review extraction rules for {field}, consider adding specific patterns',
                    'expected_impact': f'Increase {field} extraction rate to 85%+'
                })
        
        # Issue-based recommendations
        for issue in issues:
            if issue['severity'] == 'high':
                recommendations.append({
                    'priority': 'high',
                    'category': 'issue_resolution',
                    'title': f'Resolve {issue["type"].replace("_", " ").title()}',
                    'description': issue['description'],
                    'action': issue['recommendation'],
                    'expected_impact': 'Resolve critical extraction issues'
                })
        
        return recommendations
    
    def _calculate_quality_score(self, confidence_analysis: Dict, field_analysis: Dict, 
                               issues: List[Dict]) -> float:
        """Calculate an overall quality score (0.0 to 1.0)."""
        try:
            # Base score from confidence distribution
            confidence_score = 0.0
            if 'distribution' in confidence_analysis:
                dist = confidence_analysis['distribution']
                confidence_score = (
                    dist.get('high_confidence', {}).get('percentage', 0) * 0.8 +
                    dist.get('medium_confidence', {}).get('percentage', 0) * 0.5 +
                    dist.get('low_confidence', {}).get('percentage', 0) * 0.2
                ) / 100
            
            # Field extraction score
            field_score = field_analysis.get('overall_extraction_rate', 0.0)
            
            # Issue penalty
            issue_penalty = 0.0
            for issue in issues:
                if issue['severity'] == 'high':
                    issue_penalty += 0.1
                elif issue['severity'] == 'medium':
                    issue_penalty += 0.05
            
            # Calculate final score
            final_score = (confidence_score * 0.6 + field_score * 0.4) - issue_penalty
            
            return max(0.0, min(1.0, final_score))  # Clamp between 0.0 and 1.0
            
        except Exception as e:
            logger.error(f"Failed to calculate quality score: {e}")
            return 0.5  # Default score on error
    
    def _calculate_standard_deviation(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def get_analysis_status(self, file_id: str) -> Dict[str, Any]:
        """Get the current analysis status for a wine list file."""
        wine_list = self.db.query(WineListFile).filter(WineListFile.id == file_id).first()
        if not wine_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wine list file not found"
            )
        
        if not wine_list.learning_results or 'extraction_analysis' not in wine_list.learning_results:
            return {
                'file_id': file_id,
                'status': 'not_analyzed',
                'message': 'No analysis has been performed yet'
            }
        
        analysis = wine_list.learning_results['extraction_analysis']
        return {
            'file_id': file_id,
            'status': 'analyzed',
            'last_analysis': wine_list.learning_results.get('last_analysis'),
            'quality_score': analysis.get('quality_score'),
            'total_entries': analysis.get('total_entries'),
            'summary': {
                'confidence_level': analysis.get('confidence_analysis', {}).get('distribution', {}).get('high_confidence', {}).get('percentage', 0),
                'extraction_rate': analysis.get('field_analysis', {}).get('overall_extraction_rate', 0),
                'issues_count': len(analysis.get('identified_issues', []))
            }
        }
