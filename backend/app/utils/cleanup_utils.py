"""
Utility functions for cleaning up restaurant data and associated files.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Restaurant, WineListFile, WineEntry, Ruleset, AuditLog
from app.storage import cleanup_wine_list_data, delete_processing_data
from app.database import get_db

logger = logging.getLogger(__name__)

class RestaurantCleanupManager:
    """
    Manages comprehensive cleanup of restaurant data and associated files.
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db or next(get_db())
    
    async def cleanup_restaurant_completely(self, restaurant_id: str) -> Dict[str, Any]:
        """
        Perform complete cleanup of a restaurant and all associated data.
        
        Args:
            restaurant_id: The ID of the restaurant to clean up
            
        Returns:
            Dict containing cleanup results and statistics
        """
        logger.info(f"Starting complete cleanup for restaurant {restaurant_id}")
        
        cleanup_results = {
            "restaurant_id": restaurant_id,
            "wine_list_files_cleaned": 0,
            "storage_files_deleted": 0,
            "processing_data_cleaned": 0,
            "audit_logs_deleted": 0,
            "rules_deleted": 0,
            "errors": [],
            "success": False
        }
        
        try:
            # Get restaurant info
            restaurant = self.db.query(Restaurant).filter_by(id=restaurant_id).first()
            if not restaurant:
                cleanup_results["errors"].append("Restaurant not found")
                return cleanup_results
            
            restaurant_name = restaurant.name
            logger.info(f"Cleaning up restaurant: {restaurant_name} ({restaurant_id})")
            
            # 1. Clean up wine list files and their storage data
            wine_list_files = self.db.query(WineListFile).filter_by(restaurant_id=restaurant_id).all()
            cleanup_results["wine_list_files_cleaned"] = len(wine_list_files)
            
            for wine_list in wine_list_files:
                try:
                    logger.info(f"Cleaning up wine list file: {wine_list.filename} ({wine_list.id})")
                    
                    # Clean up storage data
                    storage_cleaned = await cleanup_wine_list_data(str(wine_list.id), wine_list.file_url)
                    if storage_cleaned:
                        cleanup_results["storage_files_deleted"] += 1
                    
                    # Clean up processing data
                    processing_cleaned = await delete_processing_data(str(wine_list.id))
                    if processing_cleaned:
                        cleanup_results["processing_data_cleaned"] += 1
                        
                except Exception as e:
                    error_msg = f"Error cleaning up wine list {wine_list.id}: {str(e)}"
                    logger.error(error_msg)
                    cleanup_results["errors"].append(error_msg)
            
            # 2. Clean up audit logs
            try:
                # Get all wine entries for this restaurant
                wine_entries = self.db.query(WineEntry).filter_by(restaurant_id=restaurant_id).all()
                wine_entry_ids = [str(entry.id) for entry in wine_entries]
                
                if wine_entry_ids:
                    # Delete audit logs that reference these wine entries
                    deleted_count = self.db.query(AuditLog).filter(
                        AuditLog.wine_entry_id.in_(wine_entry_ids)
                    ).delete()
                    cleanup_results["audit_logs_deleted"] += deleted_count
                
                # Get all wine list files for this restaurant
                wine_list_file_ids = [str(wine_list.id) for wine_list in wine_list_files]
                
                if wine_list_file_ids:
                    # Delete audit logs that reference these wine list files
                    deleted_count = self.db.query(AuditLog).filter(
                        AuditLog.wine_list_file_id.in_(wine_list_file_ids)
                    ).delete()
                    cleanup_results["audit_logs_deleted"] += deleted_count
                    
            except Exception as e:
                error_msg = f"Error cleaning up audit logs: {str(e)}"
                logger.error(error_msg)
                cleanup_results["errors"].append(error_msg)
            
            # 3. Clean up rules (database cascade will handle this, but we'll track it)
            try:
                ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
                if ruleset:
                    cleanup_results["rules_deleted"] = 1
                    logger.info(f"Ruleset found for restaurant {restaurant_id} (will be deleted by cascade)")
            except Exception as e:
                error_msg = f"Error checking ruleset: {str(e)}"
                logger.error(error_msg)
                cleanup_results["errors"].append(error_msg)
            
            # 4. Clean up any legacy rule cache files
            try:
                await self._cleanup_legacy_rule_cache(restaurant_id)
            except Exception as e:
                error_msg = f"Error cleaning up legacy rule cache: {str(e)}"
                logger.error(error_msg)
                cleanup_results["errors"].append(error_msg)
            
            # 5. Delete the restaurant (cascade will handle database relationships)
            self.db.delete(restaurant)
            self.db.commit()
            
            cleanup_results["success"] = True
            logger.info(f"Successfully completed cleanup for restaurant {restaurant_id}")
            
        except Exception as e:
            error_msg = f"Error during restaurant cleanup: {str(e)}"
            logger.error(error_msg)
            cleanup_results["errors"].append(error_msg)
            self.db.rollback()
        
        return cleanup_results
    
    async def _cleanup_legacy_rule_cache(self, restaurant_id: str) -> bool:
        """
        Clean up any legacy rule cache files that might be associated with a restaurant.
        
        Args:
            restaurant_id: The ID of the restaurant
            
        Returns:
            bool: True if cleanup was successful
        """
        logger.info(f"Cleaning up legacy rule cache for restaurant {restaurant_id}")
        try:
            # Since the rule cache system is deprecated and rules are now stored in the database,
            # this function primarily handles any legacy cache files that might exist
            cache_dir = "backend/rule_cache"
            if os.path.exists(cache_dir):
                # Look for any cache files that might contain restaurant-specific data
                # Since the cache system is deprecated, we'll just log that we checked
                logger.info(f"Legacy rule cache directory exists, but cache system is deprecated. Rules are stored in database.")
            
            logger.info(f"Legacy rule cache cleanup completed for restaurant {restaurant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up legacy rule cache for restaurant {restaurant_id}: {str(e)}")
            return False
    
    def get_restaurant_cleanup_summary(self, restaurant_id: str) -> Dict[str, Any]:
        """
        Get a summary of what would be cleaned up for a restaurant.
        
        Args:
            restaurant_id: The ID of the restaurant
            
        Returns:
            Dict containing summary of data that would be cleaned up
        """
        try:
            restaurant = self.db.query(Restaurant).filter_by(id=restaurant_id).first()
            if not restaurant:
                return {"error": "Restaurant not found"}
            
            wine_list_files = self.db.query(WineListFile).filter_by(restaurant_id=restaurant_id).all()
            wine_entries = self.db.query(WineEntry).filter_by(restaurant_id=restaurant_id).all()
            ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
            
            # Count audit logs
            wine_entry_ids = [str(entry.id) for entry in wine_entries]
            wine_list_file_ids = [str(wine_list.id) for wine_list in wine_list_files]
            
            audit_logs_count = 0
            if wine_entry_ids:
                audit_logs_count += self.db.query(AuditLog).filter(
                    AuditLog.wine_entry_id.in_(wine_entry_ids)
                ).count()
            
            if wine_list_file_ids:
                audit_logs_count += self.db.query(AuditLog).filter(
                    AuditLog.wine_list_file_id.in_(wine_list_file_ids)
                ).count()
            
            return {
                "restaurant_id": restaurant_id,
                "restaurant_name": restaurant.name,
                "wine_list_files_count": len(wine_list_files),
                "wine_entries_count": len(wine_entries),
                "audit_logs_count": audit_logs_count,
                "has_ruleset": ruleset is not None,
                "date_created": restaurant.date_created.isoformat() if restaurant.date_created else None
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup summary for restaurant {restaurant_id}: {str(e)}")
            return {"error": str(e)}

async def cleanup_all_restaurants() -> Dict[str, Any]:
    """
    Clean up all restaurants and their associated data.
    WARNING: This is a destructive operation!
    
    Returns:
        Dict containing cleanup results
    """
    logger.warning("Starting cleanup of ALL restaurants - this is a destructive operation!")
    
    db = next(get_db())
    cleanup_manager = RestaurantCleanupManager(db)
    
    all_restaurants = db.query(Restaurant).all()
    total_results = {
        "total_restaurants": len(all_restaurants),
        "successful_cleanups": 0,
        "failed_cleanups": 0,
        "individual_results": [],
        "errors": []
    }
    
    for restaurant in all_restaurants:
        try:
            result = await cleanup_manager.cleanup_restaurant_completely(str(restaurant.id))
            total_results["individual_results"].append(result)
            
            if result["success"]:
                total_results["successful_cleanups"] += 1
            else:
                total_results["failed_cleanups"] += 1
                total_results["errors"].extend(result["errors"])
                
        except Exception as e:
            error_msg = f"Error cleaning up restaurant {restaurant.id}: {str(e)}"
            logger.error(error_msg)
            total_results["errors"].append(error_msg)
            total_results["failed_cleanups"] += 1
    
    logger.info(f"Completed cleanup of all restaurants. Success: {total_results['successful_cleanups']}, Failed: {total_results['failed_cleanups']}")
    return total_results 