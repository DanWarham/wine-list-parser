"""
Unified Restaurant Service for orchestrating restaurant operations.
This service provides high-level operations that coordinate between different services.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.models import Restaurant, WineListFile, WineEntry

logger = logging.getLogger(__name__)


class UnifiedRestaurantService(BaseService):
    """
    Unified service for orchestrating restaurant operations including:
    - Restaurant overview and statistics
    - Wine list management coordination
    - Quality analysis coordination
    """
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def get_restaurant_overview(self, restaurant_id: str) -> Dict[str, Any]:
        """Get comprehensive overview of a restaurant."""
        try:
            # Get restaurant basic info
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Restaurant not found"
                )
            
            # Get wine list count
            wine_list_count = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).count()
            
            # Get wine entry count
            wine_entry_count = self.db.query(WineEntry).filter(
                WineEntry.restaurant_id == restaurant_id
            ).count()
            
            # Get latest wine list
            latest_wine_list = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).order_by(WineListFile.uploaded_at.desc()).first()
            
            return {
                'restaurant': {
                    'id': str(restaurant.id),
                    'name': restaurant.name,
                    'wine_list_url': restaurant.wine_list_url
                },
                'statistics': {
                    'wine_list_count': wine_list_count,
                    'wine_entry_count': wine_entry_count,
                    'last_upload': latest_wine_list.uploaded_at.isoformat() if latest_wine_list else None
                },
                'latest_wine_list': {
                    'id': str(latest_wine_list.id),
                    'filename': latest_wine_list.filename,
                    'status': latest_wine_list.status.value,
                    'uploaded_at': latest_wine_list.uploaded_at.isoformat()
                } if latest_wine_list else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get restaurant overview: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get restaurant overview"
            )
    
    def get_restaurant_quality_summary(self, restaurant_id: str) -> Dict[str, Any]:
        """Get quality summary for a restaurant's wine lists."""
        try:
            # Get all wine lists for the restaurant
            wine_lists = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).all()
            
            if not wine_lists:
                return {
                    'restaurant_id': restaurant_id,
                    'quality_summary': 'No wine lists found',
                    'total_lists': 0,
                    'average_confidence': 0.0
                }
            
            # Calculate quality metrics
            total_entries = 0
            total_confidence = 0.0
            high_quality_lists = 0
            
            for wine_list in wine_lists:
                entries = self.db.query(WineEntry).filter(
                    WineEntry.wine_list_file_id == wine_list.id
                ).all()
                
                total_entries += len(entries)
                
                # Calculate average confidence for this list
                list_confidence = sum(entry.row_confidence or 0.0 for entry in entries) / len(entries) if entries else 0.0
                total_confidence += list_confidence
                
                if list_confidence > 0.8:
                    high_quality_lists += 1
            
            avg_confidence = total_confidence / len(wine_lists) if wine_lists else 0.0
            
            return {
                'restaurant_id': restaurant_id,
                'total_wine_lists': len(wine_lists),
                'total_wine_entries': total_entries,
                'average_confidence': round(avg_confidence, 3),
                'high_quality_lists': high_quality_lists,
                'quality_score': round(avg_confidence * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Failed to get restaurant quality summary: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get restaurant quality summary"
            )
    
    def get_restaurant_recommendations(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """Get recommendations for improving restaurant wine list quality."""
        try:
            recommendations = []
            
            # Get wine list count
            wine_list_count = self.db.query(WineListFile).filter(
                WineListFile.restaurant_id == restaurant_id
            ).count()
            
            if wine_list_count == 0:
                recommendations.append({
                    'priority': 'high',
                    'category': 'setup',
                    'title': 'Upload First Wine List',
                    'description': 'Start by uploading your first wine list to begin analysis',
                    'action': 'Upload a wine list PDF file'
                })
            
            # Get average confidence
            wine_entries = self.db.query(WineEntry).filter(
                WineEntry.restaurant_id == restaurant_id
            ).all()
            
            if wine_entries:
                avg_confidence = sum(entry.row_confidence or 0.0 for entry in wine_entries) / len(wine_entries)
                
                if avg_confidence < 0.7:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'quality',
                        'title': 'Improve Extraction Quality',
                        'description': f'Current average confidence is {avg_confidence:.1%}',
                        'action': 'Review and refine extraction rules'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get restaurant recommendations: {e}")
            return []
