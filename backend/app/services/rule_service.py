"""
Rule Service for handling rule operations and rule management.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.models import Ruleset, Restaurant
from app.rules.rule_manager import RuleManager
from app.rules.rule_applicator import RuleApplicator
from app.rules.rule_learner import RuleLearner
from app.rules.rule_validator import RuleValidator
from app.rules.ai_rule_generator import AIRuleGenerator
from app.rules.confidence_calculator import ConfidenceCalculator
# Integrate with contracts
from app.contracts import Configurable

logger = logging.getLogger(__name__)


class RuleService(BaseService, Configurable):
    """Service for handling rule operations and rule management."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.rule_manager = RuleManager()
        self.rule_applicator = RuleApplicator()
        self.rule_learner = RuleLearner()
        self.rule_validator = RuleValidator()
        self.ai_rule_generator = AIRuleGenerator()
        self.confidence_calculator = ConfidenceCalculator()
        # Initialize configuration
        self._config = {
            'confidence_threshold': 0.7,
            'max_rules_per_ruleset': 100,
            'learning_enabled': True,
            'ai_generation_enabled': True
        }
    
    # Implement Configurable contract methods
    async def update_config(self, config: Dict[str, Any]) -> None:
        """Update service configuration (implements Configurable contract)."""
        # Validate configuration
        if not await self.validate_config(config):
            raise ValueError("Invalid configuration provided")
        
        # Update configuration
        self._config.update(config)
        logger.info(f"RuleService configuration updated: {config}")
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration (implements Configurable contract)."""
        # Check required fields
        if 'confidence_threshold' in config:
            threshold = config['confidence_threshold']
            if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                return False
        
        if 'max_rules_per_ruleset' in config:
            max_rules = config['max_rules_per_ruleset']
            if not isinstance(max_rules, int) or max_rules <= 0:
                return False
        
        if 'learning_enabled' in config:
            if not isinstance(config['learning_enabled'], bool):
                return False
        
        if 'ai_generation_enabled' in config:
            if not isinstance(config['ai_generation_enabled'], bool):
                return False
        
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()
    
    def get_ruleset(self, restaurant_id: str) -> Optional[Ruleset]:
        """Get ruleset for a restaurant."""
        # Validate restaurant exists
        restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        return self.db.query(Ruleset).filter(Ruleset.restaurant_id == restaurant_id).first()
    
    def create_or_update_ruleset(self, restaurant_id: str, rules_json: Dict[str, Any], 
                                user_id: str) -> Ruleset:
        """Create or update ruleset for a restaurant."""
        try:
            # Validate restaurant exists
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            # Validate rules
            validation_result = self.rule_validator.validate_rules(rules_json)
            if not validation_result['valid']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid rules: {validation_result['errors']}"
                )
            
            # Get existing ruleset or create new one
            ruleset = self.db.query(Ruleset).filter(Ruleset.restaurant_id == restaurant_id).first()
            
            if ruleset:
                # Store old values for audit log
                old_values = {'rules_json': ruleset.rules_json}
                
                # Update existing ruleset
                ruleset.rules_json = rules_json
                ruleset.last_updated = ruleset.last_updated  # Trigger onupdate
                
                self.db.commit()
                
                # Create audit log
                self.create_audit_log(
                    user_id=user_id,
                    action="update_ruleset",
                    entity_type="restaurant",
                    entity_id=restaurant_id,
                    old_value=old_values,
                    new_value={'rules_json': rules_json}
                )
                
                self.log_operation("updated", "ruleset", restaurant_id, user_id)
            else:
                # Create new ruleset
                ruleset = Ruleset(
                    restaurant_id=restaurant_id,
                    rules_json=rules_json
                )
                
                self.db.add(ruleset)
                self.db.commit()
                
                self.log_operation("created", "ruleset", restaurant_id, user_id)
            
            return ruleset
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "updating", "ruleset")
    
    def delete_ruleset(self, restaurant_id: str, user_id: str) -> bool:
        """Delete ruleset for a restaurant."""
        try:
            # Validate restaurant exists
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            ruleset = self.db.query(Ruleset).filter(Ruleset.restaurant_id == restaurant_id).first()
            if not ruleset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ruleset not found for this restaurant"
                )
            
            self.db.delete(ruleset)
            self.db.commit()
            
            self.log_operation("deleted", "ruleset", restaurant_id, user_id)
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "deleting", "ruleset")
    
    def apply_rules_to_text(self, text: str, restaurant_id: str) -> Dict[str, Any]:
        """Apply rules to text and extract wine information."""
        try:
            # Get ruleset for restaurant
            ruleset = self.get_ruleset(restaurant_id)
            if not ruleset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No ruleset found for this restaurant"
                )
            
            # Apply rules
            result = self.rule_applicator.apply_rules(text, ruleset.rules_json)
            
            # Calculate confidence
            confidence = self.confidence_calculator.calculate_confidence(result)
            
            return {
                'success': True,
                'extracted_data': result,
                'confidence': confidence,
                'rules_applied': len(ruleset.rules_json.get('rules', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to apply rules: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to apply rules to text"
            )
    
    def learn_from_samples(self, samples: List[Dict[str, Any]], restaurant_id: str, 
                          user_id: str) -> Dict[str, Any]:
        """Learn new rules from sample data."""
        try:
            # Validate restaurant exists
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            # Learn new rules
            learning_result = self.rule_learner.learn_from_samples(samples, restaurant_id)
            
            if learning_result['success'] and learning_result['new_rules']:
                # Get current ruleset
                ruleset = self.get_ruleset(restaurant_id)
                if ruleset:
                    # Merge new rules with existing ones
                    current_rules = ruleset.rules_json.get('rules', [])
                    new_rules = learning_result['new_rules']
                    
                    # Add new rules
                    current_rules.extend(new_rules)
                    
                    # Update ruleset
                    ruleset.rules_json['rules'] = current_rules
                    ruleset.rules_json['last_learning_update'] = learning_result['timestamp']
                    
                    self.db.commit()
                    
                    # Create audit log
                    self.create_audit_log(
                        user_id=user_id,
                        action="learned_rules",
                        entity_type="restaurant",
                        entity_id=restaurant_id,
                        new_value={
                            'new_rules_count': len(new_rules),
                            'total_rules': len(current_rules),
                            'learning_result': learning_result
                        }
                    )
                    
                    self.log_operation("learned", f"{len(new_rules)} new rules", restaurant_id, user_id)
            
            return learning_result
            
        except Exception as e:
            logger.error(f"Failed to learn from samples: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to learn from samples"
            )
    
    def generate_ai_rules(self, restaurant_id: str, context: str, user_id: str) -> Dict[str, Any]:
        """Generate AI-powered rules for a restaurant."""
        try:
            # Validate restaurant exists
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            # Generate AI rules
            ai_rules = self.ai_rule_generator.generate_rules(context, restaurant_id)
            
            if ai_rules['success'] and ai_rules['generated_rules']:
                # Get current ruleset
                ruleset = self.get_ruleset(restaurant_id)
                if ruleset:
                    # Merge AI-generated rules with existing ones
                    current_rules = ruleset.rules_json.get('rules', [])
                    generated_rules = ai_rules['generated_rules']
                    
                    # Add AI-generated rules
                    current_rules.extend(generated_rules)
                    
                    # Update ruleset
                    ruleset.rules_json['rules'] = current_rules
                    ruleset.rules_json['ai_generated_rules'] = generated_rules
                    ruleset.rules_json['last_ai_generation'] = ai_rules['timestamp']
                    
                    self.db.commit()
                    
                    # Create audit log
                    self.create_audit_log(
                        user_id=user_id,
                        action="generated_ai_rules",
                        entity_type="restaurant",
                        entity_id=restaurant_id,
                        new_value={
                            'ai_rules_count': len(generated_rules),
                            'total_rules': len(current_rules),
                            'ai_generation_result': ai_rules
                        }
                    )
                    
                    self.log_operation("generated", f"{len(generated_rules)} AI rules", restaurant_id, user_id)
            
            return ai_rules
            
        except Exception as e:
            logger.error(f"Failed to generate AI rules: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI rules"
            )
    
    def validate_rules(self, rules_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rules without saving them."""
        try:
            validation_result = self.rule_validator.validate_rules(rules_json)
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate rules: {e}")
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"]
            }
    
    def get_rule_statistics(self, restaurant_id: str) -> Dict[str, Any]:
        """Get statistics about rules for a restaurant."""
        try:
            ruleset = self.get_ruleset(restaurant_id)
            if not ruleset:
                return {
                    'restaurant_id': restaurant_id,
                    'has_ruleset': False,
                    'total_rules': 0,
                    'rule_types': {},
                    'last_updated': None
                }
            
            rules = ruleset.rules_json.get('rules', [])
            
            # Count rule types
            rule_types = {}
            for rule in rules:
                rule_type = rule.get('type', 'unknown')
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
            
            return {
                'restaurant_id': restaurant_id,
                'has_ruleset': True,
                'total_rules': len(rules),
                'rule_types': rule_types,
                'last_updated': ruleset.last_updated.isoformat() if ruleset.last_updated else None,
                'last_learning_update': ruleset.rules_json.get('last_learning_update'),
                'ai_generated_rules': len(ruleset.rules_json.get('ai_generated_rules', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to get rule statistics: {e}")
            return {
                'restaurant_id': restaurant_id,
                'error': str(e)
            }
