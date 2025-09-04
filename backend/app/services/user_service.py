"""
User Service for handling user operations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.models import User, Restaurant, UserRole

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for handling user operations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def list_users(self) -> List[User]:
        """List all users."""
        return self.db.query(User).order_by(User.email).all()
    
    def get_user(self, user_id: str) -> User:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        self.validate_entity_exists(user, user_id, "User")
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_supabase_id(self, supabase_user_id: str) -> Optional[User]:
        """Get user by Supabase user ID."""
        return self.db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    
    def create_user(self, data: Dict[str, Any], current_user_id: str) -> User:
        """Create a new user."""
        try:
            # Check if user with same email already exists
            existing_email = self.get_user_by_email(data['email'])
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Check if user with same Supabase ID already exists
            if 'supabase_user_id' in data and data['supabase_user_id']:
                existing_supabase = self.get_user_by_supabase_id(data['supabase_user_id'])
                if existing_supabase:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this Supabase ID already exists"
                    )
            
            # Validate restaurant exists if provided
            if 'restaurant_id' in data and data['restaurant_id']:
                restaurant = self.db.query(Restaurant).filter(Restaurant.id == data['restaurant_id']).first()
                if not restaurant:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Restaurant not found"
                    )
            
            # Validate role
            role = data.get('role', 'staff')
            if role not in [r.value for r in UserRole]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
            
            user = User(
                email=data['email'],
                supabase_user_id=data.get('supabase_user_id', ''),
                name=data.get('name'),
                role=UserRole(role),
                restaurant_id=data.get('restaurant_id')
            )
            
            self.db.add(user)
            self.db.commit()
            
            self.log_operation("created", "user", str(user.id), current_user_id)
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "creating", "user")
    
    def update_user(self, user_id: str, data: Dict[str, Any], current_user_id: str) -> User:
        """Update a user."""
        try:
            user = self.get_user(user_id)
            
            # Store old values for audit log
            old_values = {
                'name': user.name,
                'role': user.role.value if user.role else None,
                'restaurant_id': str(user.restaurant_id) if user.restaurant_id else None
            }
            
            # Update fields
            if 'name' in data and data['name'] is not None:
                user.name = data['name']
            
            if 'role' in data and data['role'] is not None:
                if data['role'] not in [r.value for r in UserRole]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid role"
                    )
                user.role = UserRole(data['role'])
            
            if 'restaurant_id' in data:
                if data['restaurant_id'] is not None:
                    # Validate restaurant exists
                    restaurant = self.db.query(Restaurant).filter(Restaurant.id == data['restaurant_id']).first()
                    if not restaurant:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Restaurant not found"
                        )
                user.restaurant_id = data['restaurant_id']
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=current_user_id,
                action="update_user",
                entity_type="user",
                entity_id=user_id,
                old_value=old_values,
                new_value=data
            )
            
            self.log_operation("updated", "user", user_id, current_user_id)
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "updating", "user")
    
    def delete_user(self, user_id: str, current_user_id: str) -> bool:
        """Delete a user."""
        try:
            user = self.get_user(user_id)
            
            # Prevent self-deletion
            if user_id == current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete your own account"
                )
            
            # Check if user has associated data that would prevent deletion
            # This could include audit logs, etc.
            
            self.db.delete(user)
            self.db.commit()
            
            self.log_operation("deleted", "user", user_id, current_user_id)
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "deleting", "user")
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information."""
        user = self.get_user(user_id)
        
        profile = {
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'role': user.role.value if user.role else None,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'restaurant': None
        }
        
        if user.restaurant_id:
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == user.restaurant_id).first()
            if restaurant:
                profile['restaurant'] = {
                    'id': str(restaurant.id),
                    'name': restaurant.name
                }
        
        return profile
    
    def list_users_by_restaurant(self, restaurant_id: str) -> List[User]:
        """List all users for a specific restaurant."""
        # Validate restaurant exists
        restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        return self.db.query(User).filter(User.restaurant_id == restaurant_id).order_by(User.email).all()
    
    def list_users_by_role(self, role: str) -> List[User]:
        """List all users with a specific role."""
        if role not in [r.value for r in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
        
        return self.db.query(User).filter(User.role == UserRole(role)).order_by(User.email).all()
    
    def search_users(self, search_term: str) -> List[User]:
        """Search users by name or email."""
        return self.db.query(User).filter(
            (User.name.ilike(f"%{search_term}%")) |
            (User.email.ilike(f"%{search_term}%"))
        ).order_by(User.email).all()
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        total_users = self.db.query(User).count()
        
        # Count by role
        role_counts = {}
        for role in UserRole:
            count = self.db.query(User).filter(User.role == role).count()
            role_counts[role.value] = count
        
        # Count by restaurant
        users_with_restaurant = self.db.query(User).filter(User.restaurant_id.isnot(None)).count()
        users_without_restaurant = total_users - users_with_restaurant
        
        return {
            'total_users': total_users,
            'role_counts': role_counts,
            'restaurant_assignment': {
                'with_restaurant': users_with_restaurant,
                'without_restaurant': users_without_restaurant
            }
        }
