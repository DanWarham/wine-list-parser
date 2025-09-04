"""
Wine List Service for handling wine list file operations.
"""

import logging
import tempfile
import os
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from .base_service import BaseService
from .processing_service import ProcessingService
from app.models import WineListFile, Restaurant, WineEntry, WineListFileStatus
from app.storage import save_file, get_file_url, save_processing_data, cleanup_wine_list_data
# Integrate with contracts
from app.contracts import ProcessingPipeline, ProcessingStatus, ProcessingStage

logger = logging.getLogger(__name__)


class WineListService(BaseService, ProcessingPipeline):
    """Service for handling wine list file operations."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.processing_service = ProcessingService(db)
        # Initialize pipeline stages
        self._stages = [
            ProcessingStage.UPLOAD,
            ProcessingStage.PROCESSING,
            ProcessingStage.EXTRACTION,
            ProcessingStage.STORAGE
        ]
    
    # Implement ProcessingPipeline contract methods
    async def process(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process wine list data (implements ProcessingPipeline contract)."""
        if isinstance(data, UploadFile):
            restaurant_id = context.get('restaurant_id') if context else None
            user_id = context.get('user_id') if context else None
            if not restaurant_id or not user_id:
                raise ValueError("restaurant_id and user_id required in context for wine list upload")
            return await self.upload_wine_list(data, restaurant_id, user_id)
        else:
            raise ValueError("Data must be UploadFile for wine list processing")
    
    async def get_pipeline_stages(self) -> List[ProcessingStage]:
        """Get pipeline stages (implements ProcessingPipeline contract)."""
        return self._stages.copy()
    
    async def get_stage_status(self, stage: ProcessingStage) -> ProcessingStatus:
        """Get status of a specific stage (implements ProcessingPipeline contract)."""
        # This would typically track status per wine list file
        # For now, return a default status
        return ProcessingStatus.COMPLETED
    
    async def update_stage_status(self, stage: ProcessingStage, status: ProcessingStatus) -> None:
        """Update status of a specific stage (implements ProcessingPipeline contract)."""
        logger.info(f"Stage {stage.value} status updated to {status.value}")
    
    async def upload_wine_list(self, file: UploadFile, restaurant_id: str, user_id: str) -> WineListFile:
        """Upload and process a wine list file."""
        try:
            # Validate restaurant exists
            restaurant = self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            self.validate_entity_exists(restaurant, restaurant_id, "Restaurant")
            
            # Save file to storage
            file_url = await save_file(file, f"wine_lists/{restaurant_id}")
            
            # Create wine list file record
            wine_list_file = WineListFile(
                restaurant_id=restaurant_id,
                filename=file.filename,
                file_url=file_url,
                status=WineListFileStatus.pending
            )
            
            self.db.add(wine_list_file)
            self.db.commit()
            
            # Start background processing
            await self._process_wine_list_background(
                str(wine_list_file.id), 
                restaurant_id, 
                file_url
            )
            
            self.log_operation("uploaded", "wine list", str(wine_list_file.id), user_id)
            return wine_list_file
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upload wine list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload wine list"
            )
    
    async def _process_wine_list_background(self, wine_list_id: str, restaurant_id: str, file_url: str) -> None:
        """Process wine list in background."""
        try:
            # Update status to processing
            wine_list = self.db.query(WineListFile).filter(WineListFile.id == wine_list_id).first()
            if wine_list:
                wine_list.status = WineListFileStatus.processing
                self.db.commit()
            
            # Download file and process using ProcessingService
            file_path = await self._download_file(file_url)
            
            try:
                # Adapt processing to accept local file path: wrap it as UploadFile-like not needed, we call internal method
                # Use internal _process_pdf to avoid reupload overhead
                wine_entries, processing_data = await self.processing_service._process_pdf(  # type: ignore[attr-defined]
                    file_path, restaurant_id
                )
                
                # Save wine entries to database
                for entry_data in wine_entries:
                    wine_entry = WineEntry(
                        wine_list_file_id=wine_list_id,
                        restaurant_id=restaurant_id,
                        **entry_data
                    )
                    self.db.add(wine_entry)
                
                # Update wine list status and save processing data
                wine_list = self.db.query(WineListFile).filter(WineListFile.id == wine_list_id).first()
                if wine_list:
                    wine_list.status = WineListFileStatus.parsed
                    wine_list.file_metadata = processing_data.get('metadata', {})
                    wine_list.steps_status = processing_data.get('steps_status', {})
                
                self.db.commit()
                
                # Save processing data to storage
                await save_processing_data(wine_list_id, processing_data)
                
                logger.info(f"Successfully processed wine list {wine_list_id}")
                
            finally:
                # Cleanup temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                
        except Exception as e:
            logger.error(f"Failed to process wine list {wine_list_id}: {e}")
            # Update status to error
            wine_list = self.db.query(WineListFile).filter(WineListFile.id == wine_list_id).first()
            if wine_list:
                wine_list.status = WineListFileStatus.error
                self.db.commit()
    
    async def _download_file(self, url: str) -> str:
        """Download file from URL to temporary location."""
        import requests
        import tempfile
        
        response = requests.get(url)
        response.raise_for_status()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(response.content)
        temp_file.close()
        
        return temp_file.name
    
    def get_wine_list(self, file_id: str) -> WineListFile:
        """Get wine list by ID."""
        wine_list = self.db.query(WineListFile).filter(WineListFile.id == file_id).first()
        self.validate_entity_exists(wine_list, file_id, "Wine list")
        return wine_list
    
    def delete_wine_list(self, file_id: str, user_id: str) -> bool:
        """Delete wine list and cleanup associated data."""
        try:
            wine_list = self.db.query(WineListFile).filter(WineListFile.id == file_id).first()
            self.validate_entity_exists(wine_list, file_id, "wine list")
            
            # Cleanup storage
            cleanup_wine_list_data(file_id)
            
            # Delete from database (cascade will handle wine entries)
            self.db.delete(wine_list)
            self.db.commit()
            
            self.log_operation("deleted", "wine list", file_id, user_id)
            return True
            
        except Exception as e:
            self.db.rollback()
            self.handle_database_error(e, "deleting", "wine list")
    
    def get_processing_data(self, file_id: str, stage: Optional[str] = None, 
                           version: Optional[str] = None) -> Dict[str, Any]:
        """Get processing data for wine list."""
        wine_list = self.get_wine_list(file_id)
        
        return {
            'file_id': file_id,
            'status': wine_list.status,
            'metadata': wine_list.file_metadata,
            'steps_status': wine_list.steps_status,
            'learning_results': wine_list.learning_results
        }
    
    def get_processing_steps(self, file_id: str) -> Dict[str, Any]:
        """Get processing steps status for wine list."""
        wine_list = self.get_wine_list(file_id)
        return wine_list.steps_status or {}
    
    def list_wine_lists_for_restaurant(self, restaurant_id: str) -> List[WineListFile]:
        """List all wine lists for a restaurant."""
        return self.db.query(WineListFile).filter(
            WineListFile.restaurant_id == restaurant_id
        ).order_by(WineListFile.uploaded_at.desc()).all()
    
    def get_wine_list_statistics(self, file_id: str) -> Dict[str, Any]:
        """Get statistics for a wine list file."""
        wine_list = self.get_wine_list(file_id)
        
        # Count wine entries
        wine_entry_count = self.db.query(WineEntry).filter(
            WineEntry.wine_list_file_id == file_id
        ).count()
        
        return {
            'file_id': file_id,
            'filename': wine_list.filename,
            'status': wine_list.status.value,
            'uploaded_at': wine_list.uploaded_at.isoformat(),
            'wine_entry_count': wine_entry_count,
            'metadata': wine_list.file_metadata or {}
        }
