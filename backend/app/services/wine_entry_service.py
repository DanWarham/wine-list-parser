"""
Wine Entry Service for handling wine entry operations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .base_service import BaseService
from app.models import WineEntry, WineEntryStatus

logger = logging.getLogger(__name__)


class WineEntryService(BaseService):
    """Service for handling wine entry operations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def list_wine_entries(self, file_id: str) -> List[WineEntry]:
        """List all wine entries for a wine list file."""
        return self.db.query(WineEntry).filter(
            WineEntry.wine_list_file_id == file_id
        ).order_by(WineEntry.id).all()
    
    def get_wine_entry(self, wine_entry_id: str) -> WineEntry:
        """Get wine entry by ID."""
        wine_entry = self.db.query(WineEntry).filter(WineEntry.id == wine_entry_id).first()
        self.validate_entity_exists(wine_entry, wine_entry_id, "Wine entry")
        return wine_entry
    
    def update_wine_entry(self, wine_entry_id: str, data: Dict[str, Any], user_id: str) -> WineEntry:
        """Update a wine entry."""
        try:
            wine_entry = self.get_wine_entry(wine_entry_id)
            
            # Store old values for audit log
            old_values = {
                'producer': wine_entry.producer,
                'cuvee': wine_entry.cuvee,
                'type': wine_entry.type,
                'vintage': wine_entry.vintage,
                'price': wine_entry.price,
                'bottle_size': wine_entry.bottle_size,
                'grape_variety': wine_entry.grape_variety,
                'country': wine_entry.country,
                'region': wine_entry.region,
                'subregion': wine_entry.subregion,
                'designation': wine_entry.designation,
                'classification': wine_entry.classification,
                'sub_type': wine_entry.sub_type,
                'extra_data': wine_entry.extra_data
            }
            
            # Update fields
            for field, value in data.items():
                if hasattr(wine_entry, field) and value is not None:
                    setattr(wine_entry, field, value)
            
            # Update status to user_edited
            wine_entry.status = WineEntryStatus.user_edited
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action="update_wine_entry",
                entity_type="wine_entry",
                entity_id=wine_entry_id,
                old_value=old_values,
                new_value=data
            )
            
            self.log_operation("updated", "wine entry", wine_entry_id, user_id)
            return wine_entry
            
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "updating", "wine entry")
    
    def bulk_update_wine_entries(self, entries: List[Dict[str, Any]], user_id: str) -> List[WineEntry]:
        """Bulk update multiple wine entries."""
        try:
            updated_entries = []
            
            for entry_data in entries:
                wine_entry_id = entry_data.get('id')
                if not wine_entry_id:
                    continue
                
                # Remove id from data to update
                update_data = {k: v for k, v in entry_data.items() if k != 'id'}
                if update_data:
                    updated_entry = self.update_wine_entry(wine_entry_id, update_data, user_id)
                    updated_entries.append(updated_entry)
            
            self.log_operation("bulk updated", f"{len(updated_entries)} wine entries", "bulk", user_id)
            return updated_entries
            
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "bulk updating", "wine entries")
    
    def reject_wine_entry(self, wine_entry_id: str, user_id: str) -> WineEntry:
        """Reject a wine entry."""
        try:
            wine_entry = self.get_wine_entry(wine_entry_id)
            
            # Store old status for audit log
            old_status = wine_entry.status
            
            # Update status to rejected
            wine_entry.status = WineEntryStatus.rejected
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action="reject_wine_entry",
                entity_type="wine_entry",
                entity_id=wine_entry_id,
                old_value={"status": old_status},
                new_value={"status": WineEntryStatus.rejected}
            )
            
            self.log_operation("rejected", "wine entry", wine_entry_id, user_id)
            return wine_entry
            
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "rejecting", "wine entry")
    
    def confirm_wine_entry(self, wine_entry_id: str, user_id: str) -> WineEntry:
        """Confirm a wine entry."""
        try:
            wine_entry = self.get_wine_entry(wine_entry_id)
            
            # Store old status for audit log
            old_status = wine_entry.status
            
            # Update status to confirmed
            wine_entry.status = WineEntryStatus.confirmed
            
            self.db.commit()
            
            # Create audit log
            self.create_audit_log(
                user_id=user_id,
                action="confirm_wine_entry",
                entity_type="wine_entry",
                entity_id=wine_entry_id,
                old_value={"status": old_status},
                new_value={"status": WineEntryStatus.confirmed}
            )
            
            self.log_operation("confirmed", "wine entry", wine_entry_id, user_id)
            return wine_entry
            
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "confirming", "wine entry")
    
    def get_wine_entries_by_status(self, file_id: str, status: WineEntryStatus) -> List[WineEntry]:
        """Get wine entries by status for a wine list file."""
        return self.db.query(WineEntry).filter(
            WineEntry.wine_list_file_id == file_id,
            WineEntry.status == status
        ).all()
    
    def get_wine_entries_by_confidence(self, file_id: str, min_confidence: float = 0.0, 
                                      max_confidence: float = 1.0) -> List[WineEntry]:
        """Get wine entries by confidence range for a wine list file."""
        return self.db.query(WineEntry).filter(
            WineEntry.wine_list_file_id == file_id,
            WineEntry.row_confidence >= min_confidence,
            WineEntry.row_confidence <= max_confidence
        ).all()
    
    def search_wine_entries(self, file_id: str, search_term: str) -> List[WineEntry]:
        """Search wine entries by text in various fields."""
        search_filter = (
            WineEntry.wine_list_file_id == file_id,
            (
                WineEntry.producer.ilike(f"%{search_term}%") |
                WineEntry.cuvee.ilike(f"%{search_term}%") |
                WineEntry.type.ilike(f"%{search_term}%") |
                WineEntry.grape_variety.ilike(f"%{search_term}%") |
                WineEntry.country.ilike(f"%{search_term}%") |
                WineEntry.region.ilike(f"%{search_term}%") |
                WineEntry.raw_text.ilike(f"%{search_term}%")
            )
        )
        
        return self.db.query(WineEntry).filter(*search_filter).all()
    
    def get_wine_entry_statistics(self, file_id: str) -> Dict[str, Any]:
        """Get statistics for wine entries in a file."""
        entries = self.list_wine_entries(file_id)
        
        if not entries:
            return {
                'total_entries': 0,
                'status_counts': {},
                'confidence_stats': {},
                'field_completion_stats': {}
            }
        
        # Status counts
        status_counts = {}
        for entry in entries:
            status = entry.status.value if entry.status else 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Confidence statistics
        confidences = [e.row_confidence for e in entries if e.row_confidence is not None]
        confidence_stats = {
            'min': min(confidences) if confidences else 0,
            'max': max(confidences) if confidences else 0,
            'avg': sum(confidences) / len(confidences) if confidences else 0,
            'count_with_confidence': len(confidences)
        }
        
        # Field completion statistics
        fields = ['producer', 'cuvee', 'type', 'vintage', 'price', 'grape_variety', 
                 'country', 'region', 'subregion']
        field_completion = {}
        
        for field in fields:
            completed = sum(1 for e in entries if getattr(e, field) and getattr(e, field).strip())
            field_completion[field] = {
                'completed': completed,
                'total': len(entries),
                'completion_rate': completed / len(entries) if entries else 0
            }
        
        return {
            'total_entries': len(entries),
            'status_counts': status_counts,
            'confidence_stats': confidence_stats,
            'field_completion_stats': field_completion
        }
