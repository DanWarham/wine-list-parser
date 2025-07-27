import os
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY
import uuid
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info("[storage] Module loaded.")

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def save_file(file: UploadFile, path: str) -> str:
    logger.info(f"[storage] save_file called for path: {path}")
    """
    Save an uploaded file to Supabase Storage.
    
    Args:
        file: The uploaded file
        path: The path where the file should be saved (e.g., 'wine-lists/restaurant_id/filename.pdf')
        
    Returns:
        str: The public URL of the saved file
        
    Raises:
        HTTPException: If the file upload fails
    """
    try:
        # Read file content
        file_content = await file.read()
        logger.info(f"Read file content, size: {len(file_content)} bytes")
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = os.path.basename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}_{unique_id}{ext}"
        
        # Create full path with unique filename and ensure forward slashes
        path = path.replace('\\', '/')  # Convert any backslashes to forward slashes
        full_path = f"{path}/{unique_filename}" if path else unique_filename
        logger.info(f"Attempting to upload file to path: {full_path}")
        
        # Upload to Supabase Storage
        try:
            storage_response = supabase.storage.from_("wine-lists").upload(
                full_path,
                file_content,
                {"content-type": file.content_type}
            )
            logger.info(f"Storage response: {storage_response}")
        except Exception as upload_error:
            logger.error(f"Supabase upload error: {str(upload_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file to storage: {str(upload_error)}")
        
        if not storage_response:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Get public URL
        try:
            public_url = supabase.storage.from_("wine-lists").get_public_url(full_path)
            logger.info(f"Generated public URL: {public_url}")
            return public_url
        except Exception as url_error:
            logger.error(f"Error getting public URL: {str(url_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to get public URL: {str(url_error)}")
        
    except Exception as e:
        logger.error(f"[storage] Exception in save_file: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

async def save_processing_data(
    wine_list_id: str,
    stage: str,
    data: Dict[str, Any],
    version: Optional[str] = None
) -> str:
    logger.info(f"[storage] save_processing_data called for wine_list_id: {wine_list_id}, stage: {stage}")
    """
    Save processing data (JSON outputs) to Supabase Storage with proper organization.
    
    Args:
        wine_list_id: The ID of the wine list file
        stage: Processing stage (extractor, preprocessor, categorizer, field_extractor, ai_refined, etc.)
        data: The data to save
        version: Optional version identifier
        
    Returns:
        str: The storage path where the data was saved
    """
    try:
        # Create organized path structure
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        version_suffix = f"_v{version}" if version else ""
        filename = f"{stage}{version_suffix}_{timestamp}.json"
        
        # Organize by wine list ID and stage
        storage_path = f"processing-data/{wine_list_id}/{stage}/{filename}"
        
        # Convert data to JSON with datetime handling
        json_data = json.dumps(data, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        # Upload to Supabase Storage
        storage_response = supabase.storage.from_("wine-lists").upload(
            storage_path,
            json_data.encode('utf-8'),
            {"content-type": "application/json"}
        )
        
        if not storage_response:
            raise HTTPException(status_code=500, detail="Failed to save processing data")
        
        logger.info(f"Saved processing data to: {storage_path}")
        return storage_path
        
    except Exception as e:
        logger.error(f"[storage] Exception in save_processing_data: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving processing data: {str(e)}")

async def get_processing_data(wine_list_id: str, stage: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    logger.info(f"[storage] get_processing_data called for wine_list_id: {wine_list_id}, stage: {stage}, version: {version}")
    """
    Retrieve processing data from Supabase Storage.
    
    Args:
        wine_list_id: The ID of the wine list file
        stage: Processing stage to retrieve
        version: Optional version identifier
        
    Returns:
        Optional[Dict[str, Any]]: The processing data if found, None otherwise
    """
    try:
        # List files in the stage directory
        stage_path = f"processing-data/{wine_list_id}/{stage}/"
        
        # Get list of files in the directory
        files = supabase.storage.from_("wine-lists").list(stage_path)
        
        if not files:
            return None
        
        # Filter out None files
        valid_files = [f for f in files if f is not None]
        if not valid_files:
            return None
        
        # Find the most recent file or specific version
        if version:
            # Look for specific version
            target_file = None
            for file_info in valid_files:
                if file_info.get('name') and f"_v{version}_" in file_info['name']:
                    target_file = file_info['name']
                    break
            if not target_file:
                return None
        else:
            # Get the most recent file
            valid_files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            target_file = valid_files[0].get('name')
            if not target_file:
                return None
        
        # Download the file
        file_path = f"{stage_path}{target_file}"
        response = supabase.storage.from_("wine-lists").download(file_path)
        
        if not response:
            return None
        
        # Parse JSON data
        data = json.loads(response.decode('utf-8'))
        return data
        
    except Exception as e:
        logger.error(f"[storage] Exception in get_processing_data: {e}")
        return None

async def list_processing_stages(wine_list_id: str) -> Dict[str, Any]:
    logger.info(f"[storage] list_processing_stages called for wine_list_id: {wine_list_id}")
    """
    List all available processing stages for a wine list.
    
    Args:
        wine_list_id: The ID of the wine list file
        
    Returns:
        Dict[str, Any]: Dictionary with stages and their metadata
    """
    try:
        base_path = f"processing-data/{wine_list_id}/"
        stages = {}
        
        # List all directories (stages) for this wine list
        items = supabase.storage.from_("wine-lists").list(base_path)
        
        if not items:
            return {}
        
        for item in items:
            if item is None:
                continue
                
            # Check if this is a directory (no mimetype in metadata)
            metadata = item.get('metadata', {})
            if metadata is None:
                metadata = {}
                
            if metadata.get('mimetype') is None:  # This is a directory
                stage_name = item.get('name', '').rstrip('/')
                if not stage_name:
                    continue
                    
                stage_path = f"{base_path}{stage_name}/"
                
                # Get files in this stage
                stage_files = supabase.storage.from_("wine-lists").list(stage_path)
                
                if stage_files:
                    stages[stage_name] = {
                        'files': [f.get('name', '') for f in stage_files if f is not None],
                        'count': len([f for f in stage_files if f is not None]),
                        'latest': stage_files[-1].get('name') if stage_files and stage_files[-1] else None,
                        'created_at': stage_files[-1].get('created_at') if stage_files and stage_files[-1] else None
                    }
        
        return stages
        
    except Exception as e:
        logger.error(f"[storage] Exception in list_processing_stages: {e}")
        return {}

async def delete_processing_data(wine_list_id: str, stage: Optional[str] = None) -> bool:
    logger.info(f"[storage] delete_processing_data called for wine_list_id: {wine_list_id}, stage: {stage}")
    """
    Delete processing data for a wine list.
    
    Args:
        wine_list_id: The ID of the wine list file
        stage: Optional specific stage to delete. If None, deletes all stages.
        
    Returns:
        bool: True if deletion was successful
    """
    try:
        if stage:
            # Delete specific stage
            stage_path = f"processing-data/{wine_list_id}/{stage}/"
            supabase.storage.from_("wine-lists").remove([stage_path])
        else:
            # Delete all processing data for this wine list
            base_path = f"processing-data/{wine_list_id}/"
            
            # List all stages
            stages = await list_processing_stages(wine_list_id)
            
            # Delete each stage
            for stage_name in stages.keys():
                stage_path = f"{base_path}{stage_name}/"
                supabase.storage.from_("wine-lists").remove([stage_path])
        
        logger.info(f"Deleted processing data for wine list {wine_list_id}")
        return True
        
    except Exception as e:
        logger.error(f"[storage] Exception in delete_processing_data: {e}")
        return False

async def get_file_url(path: str) -> Optional[str]:
    logger.info(f"[storage] get_file_url called for path: {path}")
    """
    Get the public URL for a file in Supabase Storage.
    
    Args:
        path: The path of the file in storage
        
    Returns:
        Optional[str]: The public URL if the file exists, None otherwise
    """
    try:
        return supabase.storage.from_("wine-lists").get_public_url(path)
    except Exception:
        logger.error(f"[storage] Exception in get_file_url for path: {path}")
        return None

async def delete_file(path: str) -> bool:
    logger.info(f"[storage] delete_file called for path: {path}")
    """
    Delete a file from Supabase Storage.
    
    Args:
        path: The path of the file to delete
        
    Returns:
        bool: True if the file was deleted successfully, False otherwise
    """
    try:
        supabase.storage.from_("wine-lists").remove([path])
        return True
    except Exception as e:
        logger.error(f"[storage] Exception in delete_file: {e}")
        return False

async def cleanup_wine_list_data(wine_list_id: str, file_url: str) -> bool:
    logger.info(f"[storage] cleanup_wine_list_data called for wine_list_id: {wine_list_id}, file_url: {file_url}")
    """
    Clean up all data associated with a wine list when it's deleted.
    
    Args:
        wine_list_id: The ID of the wine list file
        file_url: The URL of the original PDF file
        
    Returns:
        bool: True if cleanup was successful
    """
    try:
        # Extract file path from URL
        file_path = file_url.split('/')[-1]  # Get filename from URL
        
        # Delete original PDF file
        await delete_file(file_path)
        
        # Delete all processing data
        await delete_processing_data(wine_list_id)
        
        logger.info(f"Cleaned up all data for wine list {wine_list_id}")
        return True
        
    except Exception as e:
        logger.error(f"[storage] Exception in cleanup_wine_list_data: {e}")
        return False 