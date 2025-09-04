"""
Base service class that provides common functionality for all services.
"""

import logging
from typing import Optional, Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

# Integrate with contracts without breaking existing usages
from app.contracts import BaseService as ContractBaseService

logger = logging.getLogger(__name__)


class BaseService(ContractBaseService):
    """Base service class with common CRUD operations and error handling."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    # Existing sync helpers remain for current call-sites
    def handle_database_error(self, error: Exception, operation: str, entity: str) -> None:
        """Handle database errors and raise appropriate HTTP exceptions."""
        logger.error(f"Database error during {operation} {entity}: {error}")
        
        if isinstance(error, SQLAlchemyError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error during {operation} {entity}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during {operation} {entity}"
            )
    
    def validate_entity_exists(self, entity: Any, entity_id: str, entity_name: str) -> None:
        """Validate that an entity exists, raise 404 if not."""
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name} with id {entity_id} not found"
            )
    
    def log_operation(self, operation: str, entity: str, entity_id: str, user_id: Optional[str] = None) -> None:
        """Log an operation for audit purposes."""
        user_info = f" by user {user_id}" if user_id else ""
        logger.info(f"{operation} {entity} {entity_id}{user_info}")
    
    def create_audit_log(self, user_id: str, action: str, entity_type: str, 
                         entity_id: str, old_value: Optional[Dict] = None, 
                         new_value: Optional[Dict] = None) -> None:
        """Create an audit log entry."""
        try:
            from app.models import AuditLog
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                old_value=old_value,
                new_value=new_value
            )
            
            # Set the appropriate entity ID based on entity type
            if entity_type == "wine_entry":
                audit_log.wine_entry_id = entity_id
            elif entity_type == "wine_list_file":
                audit_log.wine_list_file_id = entity_id
            
            self.db.add(audit_log)
            self.db.commit()
            logger.info(f"Audit log created for {action} on {entity_type} {entity_id}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't fail the main operation if audit logging fails
            self.db.rollback()

    # Implement contract-required async methods (non-breaking defaults)
    async def validate_input(self, data: Any) -> bool:  # type: ignore[override]
        """Default permissive validation; override in subclasses as needed."""
        return True

    async def handle_error(self, error: Exception, context: str) -> Dict[str, Any]:  # type: ignore[override]
        """Default error handler that logs and returns a standardized dict."""
        logger.error(f"Service error in {context}: {type(error).__name__}: {error}")
        return {
            "context": context,
            "error_type": type(error).__name__,
            "message": str(error)
        }
