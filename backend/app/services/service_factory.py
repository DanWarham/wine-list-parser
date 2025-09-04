"""
Service Factory for creating and managing service instances.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from .base_service import BaseService
from .restaurant_service import RestaurantService
from .wine_list_service import WineListService
from .wine_entry_service import WineEntryService
from .user_service import UserService
from .processing_service import ProcessingService
from .rule_service import RuleService
from .analysis_service import AnalysisService
from .unified_restaurant_service import UnifiedRestaurantService
from .setup_workflow_service import SetupWorkflowService

# Integrate with contracts
from app.contracts import ServiceFactory as ContractServiceFactory

logger = logging.getLogger(__name__)


class ServiceFactory(ContractServiceFactory):
    """Factory for creating and managing service instances."""
    
    def __init__(self, db: Session):
        self.db = db
        self._services: Dict[str, BaseService] = {}
        self._service_classes = {
            'restaurant': RestaurantService,
            'wine_list': WineListService,
            'wine_entry': WineEntryService,
            'user': UserService,
            'processing': ProcessingService,
            'rule': RuleService,
            'analysis': AnalysisService,
            'unified_restaurant': UnifiedRestaurantService,
            'setup_workflow': SetupWorkflowService
        }
    
    def get_service(self, service_name: str) -> BaseService:
        """Get a service instance by name."""
        if service_name not in self._service_classes:
            raise ValueError(f"Unknown service: {service_name}")
        
        if service_name not in self._services:
            self._services[service_name] = self._service_classes[service_name](self.db)
        
        return self._services[service_name]

    # Contract methods
    def create_service(self, service_type: str, **kwargs) -> BaseService:  # type: ignore[override]
        return self.get_service(service_type)
    
    def get_service_dependencies(self, service_type: str) -> list[str]:  # type: ignore[override]
        # In future we could model dependencies explicitly; for now return empty
        return []
    
    def get_restaurant_service(self) -> RestaurantService:
        """Get restaurant service instance."""
        return self.get_service('restaurant')  # type: ignore[return-value]
    
    def get_wine_list_service(self) -> WineListService:
        """Get wine list service instance."""
        return self.get_service('wine_list')  # type: ignore[return-value]
    
    def get_wine_entry_service(self) -> WineEntryService:
        """Get wine entry service instance."""
        return self.get_service('wine_entry')  # type: ignore[return-value]
    
    def get_user_service(self) -> UserService:
        """Get user service instance."""
        return self.get_service('user')  # type: ignore[return-value]
    
    def get_processing_service(self) -> ProcessingService:
        """Get processing service instance."""
        return self.get_service('processing')  # type: ignore[return-value]
    
    def get_rule_service(self) -> RuleService:
        """Get rule service instance."""
        return self.get_service('rule')  # type: ignore[return-value]
    
    def get_analysis_service(self) -> AnalysisService:
        """Get analysis service instance."""
        return self.get_service('analysis')  # type: ignore[return-value]
    
    def get_unified_restaurant_service(self) -> UnifiedRestaurantService:
        """Get unified restaurant service instance."""
        return self.get_service('unified_restaurant')  # type: ignore[return-value]
    
    def get_setup_workflow_service(self) -> SetupWorkflowService:
        """Get setup workflow service instance."""
        return self.get_service('setup_workflow')  # type: ignore[return-value]
    
    def get_all_services(self) -> Dict[str, BaseService]:
        """Get all service instances."""
        for service_name in self._service_classes:
            if service_name not in self._services:
                self._services[service_name] = self._service_classes[service_name](self.db)
        
        return self._services.copy()
    
    def clear_services(self) -> None:
        """Clear all cached service instances."""
        self._services.clear()
        logger.info("All service instances cleared")
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available services."""
        service_info = {}
        
        for service_name, service_class in self._service_classes.items():
            service_info[service_name] = {
                'class_name': service_class.__name__,
                'module': service_class.__module__,
                'docstring': service_class.__doc__ or 'No documentation available',
                'is_instantiated': service_name in self._services,
                'base_class': service_class.__bases__[0].__name__ if service_class.__bases__ else 'None'
            }
        
        return service_info
    
    def validate_service_dependencies(self) -> Dict[str, bool]:
        """Validate that all services can be instantiated."""
        validation_results = {}
        
        for service_name, service_class in self._service_classes.items():
            try:
                # Try to instantiate the service
                service_instance = service_class(self.db)
                validation_results[service_name] = True
                logger.info(f"Service {service_name} validation: PASSED")
                
                # Clean up the test instance
                del service_instance
                
            except Exception as e:
                validation_results[service_name] = False
                logger.error(f"Service {service_name} validation: FAILED - {e}")
        
        return validation_results
    
    def reload_service(self, service_name: str) -> BaseService:
        """Reload a specific service instance."""
        if service_name in self._services:
            del self._services[service_name]
            logger.info(f"Service {service_name} instance cleared for reload")
        
        return self.get_service(service_name)
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        health_status = {
            'total_services': len(self._service_classes),
            'instantiated_services': len(self._services),
            'service_status': {},
            'overall_health': 'healthy'
        }
        
        # Check each service
        failed_services = 0
        for service_name in self._service_classes:
            try:
                service = self.get_service(service_name)
                health_status['service_status'][service_name] = {
                    'status': 'healthy',
                    'instance_type': type(service).__name__,
                    'database_connection': hasattr(service, 'db') and service.db is not None
                }
            except Exception as e:
                health_status['service_status'][service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                failed_services += 1
        
        # Determine overall health
        if failed_services == 0:
            health_status['overall_health'] = 'healthy'
        elif failed_services < len(self._service_classes) * 0.5:
            health_status['overall_health'] = 'degraded'
        else:
            health_status['overall_health'] = 'unhealthy'
        
        health_status['failed_services'] = failed_services
        
        return health_status


# Global service factory instance
_global_service_factory: Optional[ServiceFactory] = None


def create_service_factory(db: Session) -> ServiceFactory:
    """Create a new service factory instance."""
    return ServiceFactory(db)


def get_global_service_factory() -> ServiceFactory:
    """Get the global service factory instance."""
    global _global_service_factory
    if _global_service_factory is None:
        raise RuntimeError("Global service factory not initialized. Call set_global_service_factory first.")
    return _global_service_factory


def set_global_service_factory(factory: ServiceFactory) -> None:
    """Set the global service factory instance."""
    global _global_service_factory
    _global_service_factory = factory


def get_service(service_name: str) -> BaseService:
    """Get a service instance from the global factory."""
    return get_global_service_factory().get_service(service_name)
