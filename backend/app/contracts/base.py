"""
Base service contracts and interfaces.

This module defines the fundamental contracts that all services must implement,
ensuring consistency across the application architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Generic, TypeVar
from sqlalchemy.orm import Session
import logging

# Type variable for generic service results
T = TypeVar('T')

class BaseService(ABC):
    """
    Base contract for all services in the application.
    
    Provides common functionality like logging, database session management,
    and error handling patterns.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def validate_input(self, data: Any) -> bool:
        """Validate input data before processing."""
        pass
    
    @abstractmethod
    async def handle_error(self, error: Exception, context: str) -> Dict[str, Any]:
        """Handle and log errors consistently."""
        pass

class ServiceFactory(ABC):
    """
    Contract for service factory implementations.
    
    Ensures consistent service instantiation and dependency injection.
    """
    
    @abstractmethod
    def create_service(self, service_type: str, **kwargs) -> BaseService:
        """Create a service instance of the specified type."""
        pass
    
    @abstractmethod
    def get_service_dependencies(self, service_type: str) -> List[str]:
        """Get list of dependencies required for a service type."""
        pass

class DataProcessor(ABC, Generic[T]):
    """
    Generic contract for data processing operations.
    
    Defines the standard interface for processing data of type T
    and returning processed results.
    """
    
    @abstractmethod
    async def process(self, data: T) -> Dict[str, Any]:
        """Process input data and return results."""
        pass
    
    @abstractmethod
    async def validate_result(self, result: Dict[str, Any]) -> bool:
        """Validate processing results."""
        pass
    
    @abstractmethod
    async def get_processing_metadata(self) -> Dict[str, Any]:
        """Get metadata about the processing operation."""
        pass

class Configurable(ABC):
    """
    Contract for configurable components.
    
    Ensures components can be configured with different settings
    while maintaining consistent configuration patterns.
    """
    
    @abstractmethod
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update component configuration."""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration parameters."""
        pass

class Auditable(ABC):
    """
    Contract for auditable operations.
    
    Ensures operations can be tracked and logged for compliance
    and debugging purposes.
    """
    
    @abstractmethod
    async def log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log an operation for audit purposes."""
        pass
    
    @abstractmethod
    async def get_audit_trail(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail with optional filtering."""
        pass
