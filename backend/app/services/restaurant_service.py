"""
Restaurant Service for handling restaurant operations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.models import Restaurant, WineListFile, User, WineEntry

logger = logging.getLogger(__name__)


class RestaurantService(BaseService):
    """Service for handling restaurant operations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def list_restaurants(self) -> List[Restaurant]:
        """List all restaurants."""
        return self.db.query(Restaurant).order_by(Restaurant.name).all()
    
    def get_restaurant(self, restaurant_id: str) -> Restaurant:
        """Get restaurant by ID."""
        restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        self.validate_entity_exists(restaurant, restaurant_id, "Restaurant")
        return restaurant
    
    def create_restaurant(self, data: Dict[str, Any], user_id: str) -> Restaurant:
        """Create a new restaurant."""
        try:
            # Check if restaurant with same name already exists
            existing = self.db.query(Restaurant).filter(Restaurant.name == data['name']).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Restaurant with this name already exists"
                )
            
            restaurant = Restaurant(
                name=data['name'],
                wine_list_url=data.get('wine_list_url')
            )
            
            self.db.add(restaurant)
            self.db.commit()
            
            self.log_operation("created", "restaurant", str(restaurant.id), user_id)
            return restaurant
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "creating", "restaurant")
    
    def update_restaurant(self, restaurant_id: str, data: Dict[str, Any], user_id: str) -> Restaurant:
        """Update a restaurant."""
        try:
            restaurant = self.get_restaurant(restaurant_id)
            
            # Store old values for audit log
            old_values = {
                'name': restaurant.name,
                'wine_list_url': restaurant.wine_list_url
            }
            
            # Update fields
            if 'name' in data and data['name'] is not None:
                # Check if new name conflicts with existing restaurant
                existing = self.db.query(Restaurant).filter(
                    Restaurant.name == data['name'],
                    Restaurant.id != restaurant_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Restaurant with this name already exists"
                    )
                restaurant.name = data['name']
            
            if 'wine_list_url' in data:
                restaurant.wine_list_url = data['wine_list_url']
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action="update_restaurant",
                entity_type="restaurant",
                entity_id=restaurant_id,
                old_value=old_values,
                new_value=data
            )
            
            self.log_operation("updated", "restaurant", restaurant_id, user_id)
            return restaurant
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "updating", "restaurant")
    
    def delete_restaurant(self, restaurant_id: str, user_id: str) -> bool:
        """Delete a restaurant and all associated data."""
        try:
            restaurant = self.get_restaurant(restaurant_id)
            
            # Check if restaurant has associated data
            wine_list_count = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).count()
            
            user_count = self.db.query(User).filter(
                User.restaurant_id == restaurant_id
            ).count()
            
            if wine_list_count > 0 or user_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete restaurant with associated wine lists or users"
                )
            
            # Delete restaurant (cascade will handle ruleset)
            self.db.delete(restaurant)
            self.db.commit()
            
            self.log_operation("deleted", "restaurant", restaurant_id, user_id)
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "deleting", "restaurant")
    
    def get_restaurant_statistics(self, restaurant_id: str) -> Dict[str, Any]:
        """Get statistics for a restaurant."""
        try:
            restaurant = self.get_restaurant(restaurant_id)
            
            # Count wine lists
            wine_list_count = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).count()
            
            # Count wine entries
            wine_entry_count = self.db.query(WineEntry).filter(
                WineEntry.restaurant_id == restaurant_id
            ).count()
            
            # Count users
            user_count = self.db.query(User).filter(
                User.restaurant_id == restaurant_id
            ).count()
            
            # Get latest wine list
            latest_wine_list = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).order_by(WineListFile.uploaded_at.desc()).first()
            
            return {
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant.name,
                'wine_list_count': wine_list_count,
                'wine_entry_count': wine_entry_count,
                'user_count': user_count,
                'latest_wine_list': {
                    'id': str(latest_wine_list.id),
                    'filename': latest_wine_list.filename,
                    'uploaded_at': latest_wine_list.uploaded_at.isoformat() if latest_wine_list else None,
                    'status': latest_wine_list.status.value if latest_wine_list else None
                } if latest_wine_list else None
            }
        except Exception as e:
            self.handle_database_error(e, "getting statistics for", "restaurant")
            raise  # Re-raise the exception after handling
    
    def search_restaurants(self, search_term: str) -> List[Restaurant]:
        """Search restaurants by name."""
        return self.db.query(Restaurant).filter(
            Restaurant.name.ilike(f"%{search_term}%")
        ).order_by(Restaurant.name).all()
