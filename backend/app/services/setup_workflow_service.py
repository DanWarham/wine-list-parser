"""
Setup Workflow Service for managing restaurant setup process.
This service guides users through the complete restaurant setup workflow.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .base_service import BaseService
from .unified_restaurant_service import UnifiedRestaurantService
from .rule_service import RuleService
from .analysis_service import AnalysisService
from app.models import Restaurant, WineListFile, WineEntry, Ruleset, User
# Integrate with contracts
from app.contracts import ProcessingPipeline, ProcessingStatus, ProcessingStage

logger = logging.getLogger(__name__)


class SetupWorkflowService(BaseService, ProcessingPipeline):
    """Service for managing restaurant setup workflow."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.unified_service = UnifiedRestaurantService(db)
        self.rule_service = RuleService(db)
        self.analysis_service = AnalysisService(db)
        # Initialize setup workflow stages
        self._stages = [
            ProcessingStage.SETUP_INIT,
            ProcessingStage.RESTAURANT_CONFIG,
            ProcessingStage.RULESET_CONFIG,
            ProcessingStage.WINE_LIST_UPLOAD,
            ProcessingStage.QUALITY_ASSESSMENT,
            ProcessingStage.OPTIMIZATION
        ]
    
    # Implement ProcessingPipeline contract methods
    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process setup workflow data (implements ProcessingPipeline contract)."""
        if isinstance(data, dict) and 'restaurant_id' in data:
            action = context.get('action') if context else 'get_status'
            if action == 'get_status':
                return self.get_setup_status(data['restaurant_id'])
            elif action == 'complete_step':
                step_key = context.get('step_key')
                user_id = context.get('user_id')
                step_data = context.get('step_data')
                if not step_key or not user_id:
                    raise ValueError("step_key and user_id required in context for completing setup step")
                return self.complete_setup_step(data['restaurant_id'], step_key, user_id, step_data)
            else:
                raise ValueError(f"Unknown action: {action}")
        else:
            raise ValueError("Data must be dict with restaurant_id for setup workflow processing")
    
    async def get_pipeline_stages(self) -> List[ProcessingStage]:
        """Get pipeline stages (implements ProcessingPipeline contract)."""
        return self._stages.copy()
    
    async def get_stage_status(self, stage: ProcessingStage) -> ProcessingStatus:
        """Get status of a specific stage (implements ProcessingPipeline contract)."""
        # This would typically track status per restaurant setup
        # For now, return a default status
        return ProcessingStatus.COMPLETED
    
    async def update_stage_status(self, stage: ProcessingStage, status: ProcessingStatus) -> None:
        """Update status of a specific stage (implements ProcessingPipeline contract)."""
        logger.info(f"Setup stage {stage.value} status updated to {status.value}")
    
    def get_setup_status(self, restaurant_id: str) -> Dict[str, Any]:
        """Get the current setup status for a restaurant."""
        try:
            # Get restaurant
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            # Check setup steps
            setup_steps = self._check_setup_steps(restaurant_id)
            
            # Calculate completion percentage
            completed_steps = sum(1 for step in setup_steps.values() if step['completed'])
            total_steps = len(setup_steps)
            completion_percentage = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
            
            # Determine setup status
            if completion_percentage == 100:
                setup_status = 'complete'
            elif completion_percentage >= 75:
                setup_status = 'nearly_complete'
            elif completion_percentage >= 50:
                setup_status = 'in_progress'
            elif completion_percentage >= 25:
                setup_status = 'started'
            else:
                setup_status = 'not_started'
            
            return {
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant.name,
                'setup_status': setup_status,
                'completion_percentage': round(completion_percentage, 1),
                'completed_steps': completed_steps,
                'total_steps': total_steps,
                'setup_steps': setup_steps,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get setup status: {e}")
            raise
    
    def _check_setup_steps(self, restaurant_id: str) -> Dict[str, Dict[str, Any]]:
        """Check completion status of each setup step."""
        setup_steps = {
            'restaurant_created': {
                'name': 'Restaurant Created',
                'description': 'Basic restaurant information has been added',
                'completed': False,
                'priority': 1
            },
            'ruleset_configured': {
                'name': 'Extraction Rules Configured',
                'description': 'Initial extraction rules have been set up',
                'completed': False,
                'priority': 2
            },
            'first_wine_list_uploaded': {
                'name': 'First Wine List Uploaded',
                'description': 'At least one wine list has been uploaded and processed',
                'completed': False,
                'priority': 3
            },
            'extraction_quality_assessed': {
                'name': 'Extraction Quality Assessed',
                'description': 'Initial extraction quality has been analyzed',
                'completed': False,
                'priority': 4
            },
            'rules_refined': {
                'name': 'Rules Refined',
                'description': 'Extraction rules have been refined based on initial results',
                'completed': False,
                'priority': 5
            },
            'setup_validated': {
                'name': 'Setup Validated',
                'description': 'Complete setup has been validated and approved',
                'completed': False,
                'priority': 6
            }
        }
        
        # Check restaurant creation
        restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if restaurant:
            setup_steps['restaurant_created']['completed'] = True
            setup_steps['restaurant_created']['completed_at'] = restaurant.date_created.isoformat()
        
        # Check ruleset configuration
        ruleset = self.db.query(Ruleset).filter(Ruleset.restaurant_id == restaurant_id).first()
        if ruleset and ruleset.rules_json:
            setup_steps['ruleset_configured']['completed'] = True
            setup_steps['ruleset_configured']['completed_at'] = ruleset.last_updated.isoformat()
        
        # Check first wine list upload
        wine_lists = self.db.query(WineListFile).filter(WineListFile.restaurant_id == restaurant_id).all()
        if wine_lists:
            setup_steps['first_wine_list_uploaded']['completed'] = True
            setup_steps['first_wine_list_uploaded']['completed_at'] = wine_lists[0].uploaded_at.isoformat()
            setup_steps['first_wine_list_uploaded']['wine_list_count'] = len(wine_lists)
        
        # Check extraction quality assessment
        if wine_lists:
            # Check if any wine list has been analyzed
            for wine_list in wine_lists:
                if wine_list.learning_results and 'extraction_analysis' in wine_list.learning_results:
                    setup_steps['extraction_quality_assessed']['completed'] = True
                    setup_steps['extraction_quality_assessed']['completed_at'] = wine_list.learning_results.get('last_analysis')
                    break
        
        # Check rules refinement
        if ruleset and wine_lists:
            # Check if rules have been updated after first wine list
            first_wine_list_date = min(wl.uploaded_at for wl in wine_lists)
            if ruleset.last_updated > first_wine_list_date:
                setup_steps['rules_refined']['completed'] = True
                setup_steps['rules_refined']['completed_at'] = ruleset.last_updated.isoformat()
        
        # Check setup validation
        if all(step['completed'] for step in setup_steps.values() if step['priority'] < 6):
            setup_steps['setup_validated']['completed'] = True
            setup_steps['setup_validated']['completed_at'] = datetime.utcnow().isoformat()
        
        return setup_steps
    
    def get_next_setup_step(self, restaurant_id: str) -> Dict[str, Any]:
        """Get the next recommended setup step for a restaurant."""
        try:
            setup_status = self.get_setup_status(restaurant_id)
            setup_steps = setup_status['setup_steps']
            
            # Find the next incomplete step
            next_step = None
            for step_key, step_data in setup_steps.items():
                if not step_data['completed']:
                    next_step = {
                        'step_key': step_key,
                        **step_data
                    }
                    break
            
            if not next_step:
                return {
                    'message': 'Setup is complete!',
                    'next_action': 'monitor_and_optimize',
                    'recommendations': self._get_optimization_recommendations(restaurant_id)
                }
            
            # Get specific guidance for the next step
            step_guidance = self._get_step_guidance(next_step['step_key'], restaurant_id)
            
            return {
                'next_step': next_step,
                'guidance': step_guidance,
                'estimated_time': step_guidance.get('estimated_time', '5-15 minutes'),
                'difficulty': step_guidance.get('difficulty', 'medium')
            }
            
        except Exception as e:
            logger.error(f"Failed to get next setup step: {e}")
            raise
    
    def _get_step_guidance(self, step_key: str, restaurant_id: str) -> Dict[str, Any]:
        """Get specific guidance for a setup step."""
        guidance_map = {
            'restaurant_created': {
                'title': 'Restaurant Information',
                'description': 'Add basic restaurant details to get started',
                'actions': [
                    'Enter restaurant name',
                    'Add wine list URL if available',
                    'Set up basic contact information'
                ],
                'estimated_time': '2-5 minutes',
                'difficulty': 'easy',
                'api_endpoint': f'/api/v2/restaurants/{restaurant_id}',
                'method': 'PUT'
            },
            'ruleset_configured': {
                'title': 'Configure Extraction Rules',
                'description': 'Set up initial rules for wine list extraction',
                'actions': [
                    'Choose extraction strategy (AI, Regex, or Hybrid)',
                    'Set confidence thresholds',
                    'Configure field extraction preferences'
                ],
                'estimated_time': '10-20 minutes',
                'difficulty': 'medium',
                'api_endpoint': f'/api/v2/restaurants/{restaurant_id}/ruleset',
                'method': 'PUT',
                'tips': [
                    'Start with hybrid strategy for best results',
                    'Use default confidence threshold of 0.7',
                    'You can refine rules later based on results'
                ]
            },
            'first_wine_list_uploaded': {
                'title': 'Upload First Wine List',
                'description': 'Upload and process your first wine list to test extraction',
                'actions': [
                    'Prepare a PDF wine list file',
                    'Upload the file through the interface',
                    'Monitor processing status'
                ],
                'estimated_time': '5-15 minutes',
                'difficulty': 'easy',
                'api_endpoint': '/api/v2/wine-lists/upload',
                'method': 'POST',
                'tips': [
                    'Use a recent, clear wine list for best results',
                    'Ensure the PDF is readable and not scanned images',
                    'Processing time depends on file size and complexity'
                ]
            },
            'extraction_quality_assessed': {
                'title': 'Assess Extraction Quality',
                'description': 'Analyze the quality of your first extraction results',
                'actions': [
                    'Review extracted wine entries',
                    'Check confidence scores',
                    'Identify areas for improvement'
                ],
                'estimated_time': '15-30 minutes',
                'difficulty': 'medium',
                'api_endpoint': f'/api/v2/wine-lists/{{file_id}}/analyze',
                'method': 'POST',
                'tips': [
                    'Focus on entries with low confidence scores',
                    'Look for missing or incorrect field extractions',
                    'Note patterns that could be improved with rules'
                ]
            },
            'rules_refined': {
                'title': 'Refine Extraction Rules',
                'description': 'Improve rules based on initial extraction results',
                'actions': [
                    'Analyze extraction issues',
                    'Update or add new extraction rules',
                    'Test rule improvements'
                ],
                'estimated_time': '20-40 minutes',
                'difficulty': 'hard',
                'api_endpoint': f'/api/v2/restaurants/{restaurant_id}/ruleset',
                'method': 'PUT',
                'tips': [
                    'Use the analysis results to identify rule improvements',
                    'Start with simple pattern-based rules',
                    'Test changes with a small sample first'
                ]
            },
            'setup_validated': {
                'title': 'Validate Complete Setup',
                'description': 'Final validation of your complete setup',
                'actions': [
                    'Review all setup components',
                    'Test with additional wine lists',
                    'Confirm extraction quality meets requirements'
                ],
                'estimated_time': '10-20 minutes',
                'difficulty': 'easy',
                'tips': [
                    'Ensure all steps are completed successfully',
                    'Test with different wine list formats',
                    'Document any custom configurations'
                ]
            }
        }
        
        return guidance_map.get(step_key, {
            'title': 'Unknown Step',
            'description': 'Step guidance not available',
            'actions': [],
            'estimated_time': 'Unknown',
            'difficulty': 'unknown'
        })
    
    def _get_optimization_recommendations(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for completed setups."""
        try:
            # Get restaurant overview
            overview = self.unified_service.get_restaurant_overview(restaurant_id)
            
            recommendations = []
            
            # Check wine list count
            wine_list_count = overview['statistics'].get('wine_list_count', 0)
            if wine_list_count < 3:
                recommendations.append({
                    'category': 'data_volume',
                    'title': 'Increase Wine List Volume',
                    'description': f'Currently have {wine_list_count} wine list(s). More data improves learning.',
                    'action': 'Upload additional wine lists to improve rule learning',
                    'priority': 'medium'
                })
            
            # Check rule count
            rule_count = overview['rule_statistics'].get('total_rules', 0)
            if rule_count < 10:
                recommendations.append({
                    'category': 'rule_coverage',
                    'title': 'Expand Rule Coverage',
                    'description': f'Currently have {rule_count} rules. More rules improve extraction accuracy.',
                    'action': 'Add more specific extraction rules based on patterns',
                    'priority': 'medium'
                })
            
            # Check recent activity
            if overview['statistics'].get('latest_wine_list'):
                latest_date = datetime.fromisoformat(overview['statistics']['latest_wine_list']['uploaded_at'])
                days_ago = (datetime.utcnow() - latest_date).days
                if days_ago > 90:
                    recommendations.append({
                        'category': 'maintenance',
                        'title': 'Regular Maintenance',
                        'description': f'Last wine list uploaded {days_ago} days ago.',
                        'action': 'Upload new wine lists to keep rules current',
                        'priority': 'low'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    def complete_setup_step(self, restaurant_id: str, step_key: str, user_id: str, 
                           step_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mark a setup step as completed."""
        try:
            # Validate step key
            valid_steps = [
                'restaurant_created', 'ruleset_configured', 'first_wine_list_uploaded',
                'extraction_quality_assessed', 'rules_refined', 'setup_validated'
            ]
            
            if step_key not in valid_steps:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid step key: {step_key}"
                )
            
            # Get current setup status
            current_status = self.get_setup_status(restaurant_id)
            
            # Check if step is already completed
            if current_status['setup_steps'][step_key]['completed']:
                return {
                    'message': f'Step {step_key} is already completed',
                    'current_status': current_status
                }
            
            # Mark step as completed
            current_status['setup_steps'][step_key]['completed'] = True
            current_status['setup_steps'][step_key]['completed_at'] = datetime.utcnow().isoformat()
            
            # Update completion percentage
            completed_steps = sum(1 for step in current_status['setup_steps'].values() if step['completed'])
            total_steps = len(current_status['setup_steps'])
            completion_percentage = (completed_steps / total_steps) * 100
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action=f"completed_setup_step_{step_key}",
                entity_type="restaurant",
                entity_id=restaurant_id,
                new_value={
                    'step_key': step_key,
                    'completion_percentage': completion_percentage,
                    'step_data': step_data
                }
            )
            
            # Get next step guidance
            next_step = self.get_next_setup_step(restaurant_id)
            
            return {
                'message': f'Step {step_key} completed successfully',
                'completion_percentage': round(completion_percentage, 1),
                'next_step': next_step,
                'current_status': current_status
            }
            
        except Exception as e:
            logger.error(f"Failed to complete setup step: {e}")
            raise
    
    def get_setup_timeline(self, restaurant_id: str) -> Dict[str, Any]:
        """Get a timeline of setup activities for a restaurant."""
        try:
            # Get restaurant
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            timeline = []
            
            # Restaurant creation
            timeline.append({
                'date': restaurant.date_created.isoformat(),
                'event': 'Restaurant Created',
                'description': f'Restaurant "{restaurant.name}" was created',
                'type': 'creation'
            })
            
            # Ruleset updates
            ruleset = self.db.query(Ruleset).filter(Ruleset.restaurant_id == restaurant_id).first()
            if ruleset:
                timeline.append({
                    'date': ruleset.date_created.isoformat(),
                    'event': 'Initial Ruleset Created',
                    'description': 'Initial extraction rules were configured',
                    'type': 'configuration'
                })
                
                if ruleset.last_updated != ruleset.date_created:
                    timeline.append({
                        'date': ruleset.last_updated.isoformat(),
                        'event': 'Ruleset Updated',
                        'description': 'Extraction rules were updated',
                        'type': 'update'
                    })
            
            # Wine list uploads
            wine_lists = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).order_by(WineListFile.uploaded_at).all()
            
            for wine_list in wine_lists:
                timeline.append({
                    'date': wine_list.uploaded_at.isoformat(),
                    'event': 'Wine List Uploaded',
                    'description': f'Wine list "{wine_list.filename}" was uploaded',
                    'type': 'upload',
                    'file_id': str(wine_list.id)
                })
                
                # Check for analysis
                if wine_list.learning_results and 'last_analysis' in wine_list.learning_results:
                    timeline.append({
                        'date': wine_list.learning_results['last_analysis'],
                        'event': 'Quality Analysis Completed',
                        'description': f'Extraction quality analysis completed for "{wine_list.filename}"',
                        'type': 'analysis',
                        'file_id': str(wine_list.id)
                    })
            
            # Sort timeline by date
            timeline.sort(key=lambda x: x['date'])
            
            return {
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant.name,
                'timeline': timeline,
                'total_events': len(timeline),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get setup timeline: {e}")
            raise
