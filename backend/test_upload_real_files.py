#!/usr/bin/env python3
"""
Script to upload real-world PDF files to their respective restaurants for testing.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models import Restaurant, WineListFile, WineListFileStatus, WineEntry
from app.api_v2 import process_pdf
from app.storage import save_file
from fastapi import UploadFile
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File to restaurant mapping
FILE_RESTAURANT_MAPPING = {
    "compagnie-des-vins-surnaturels-seven-dials-pages.pdf": "CVS",
    "Les-110-de-taillevent-pages-2.pdf": "110 Taillevent", 
    "the-10-cases - Test2.pdf": "Ten Cases",
    "Sager & Wilde-Test1.pdf": "Sager and Wilde"
}

async def get_restaurant_by_name(db, name: str) -> Restaurant:
    """Get restaurant by name."""
    return db.query(Restaurant).filter(Restaurant.name == name).first()

async def create_mock_upload_file(file_path: str) -> UploadFile:
    """Create a mock UploadFile object from a file path."""
    filename = os.path.basename(file_path)
    
    # Create a mock UploadFile
    class MockUploadFile:
        def __init__(self, file_path: str, filename: str):
            self.file_path = file_path
            self.filename = filename
            self.content_type = "application/pdf"
            self.size = os.path.getsize(file_path)
        
        async def read(self):
            with open(self.file_path, 'rb') as f:
                return f.read()
    
    return MockUploadFile(file_path, filename)

async def upload_file_to_restaurant(file_path: str, restaurant: Restaurant, db) -> Dict:
    """Upload a file to a specific restaurant."""
    try:
        logger.info(f"Uploading {file_path} to restaurant {restaurant.name}")
        
        # Create mock upload file
        upload_file = await create_mock_upload_file(file_path)
        
        # Save file to storage
        file_url = await save_file(upload_file, f"wine-lists/{restaurant.id}")
        if not file_url:
            raise Exception("Failed to save file")
        
        # Create wine list entry
        wine_list = WineListFile(
            restaurant_id=restaurant.id,
            filename=upload_file.filename,
            file_url=file_url,
            status=WineListFileStatus.processing,
            metadata={}
        )
        db.add(wine_list)
        db.commit()
        db.refresh(wine_list)
        
        logger.info(f"Created wine list entry: {wine_list.id}")
        
        # Process the PDF
        logger.info(f"Processing PDF for wine list {wine_list.id}")
        extracted_fields, metadata, learning_results, wine_blocks = await process_pdf(
            file_path, 
            str(restaurant.id), 
            str(wine_list.id), 
            db
        )
        
        # Update wine list with results
        wine_list.status = WineListFileStatus.parsed
        wine_list.metadata = metadata
        wine_list.learning_results = learning_results
        wine_list.learning_date = datetime.utcnow()
        wine_list.parsed_date = datetime.utcnow()
        db.commit()

        # Store extracted fields as WineEntry rows
        logger.info(f"Saving {len(extracted_fields)} wine entries to database...")
        
        def extract_value(field_data):
            """Safely extract value from field data structure"""
            if field_data is None:
                return None
            elif isinstance(field_data, dict):
                return field_data.get('value')
            else:
                return str(field_data)
        
        for i, entry in enumerate(extracted_fields):
            # Get the original block text for raw_text field
            raw_text = wine_blocks[i].get('text') if i < len(wine_blocks) else None
            
            # Ensure entry is not None
            if entry is None:
                logger.warning(f"Entry at index {i} is None, skipping")
                continue
            
            wine_entry = WineEntry(
                wine_list_file_id=wine_list.id,
                restaurant_id=restaurant.id,
                # Map extracted fields to database fields correctly with safe extraction
                producer=extract_value(entry.get('producer_name') or entry.get('producer_title')),
                cuvee=extract_value(entry.get('wine_name')),
                type=extract_value(entry.get('type')),
                vintage=extract_value(entry.get('vintage')),
                price=extract_value(entry.get('price')),
                bottle_size=extract_value(entry.get('bottle_size')),
                grape_variety=extract_value(entry.get('grape_variety')),
                country=extract_value(entry.get('country')),
                region=extract_value(entry.get('region')),
                subregion=extract_value(entry.get('sub_region')),  # Note: sub_region -> subregion
                row_confidence=extract_value(entry.get('row_confidence')) or entry.get('confidence', 0.0),
                field_confidence=entry.get('field_confidence') if entry.get('field_confidence') is not None else {},
                section_header=extract_value(entry.get('section_header')),
                subheader=extract_value(entry.get('subheader')),
                raw_text=raw_text,  # Use the original block text
                status=None,  # Set to None or default, or map if present
                designation=extract_value(entry.get('designation')),
                classification=extract_value(entry.get('classification')),
                sub_type=extract_value(entry.get('sub_type'))
            )
            db.add(wine_entry)
        
        db.commit()
        logger.info(f"Successfully saved {len(extracted_fields)} wine entries to database")
        
        return {
            "success": True,
            "wine_list_id": str(wine_list.id),
            "extracted_entries": len(extracted_fields),
            "learning_results": learning_results
        }
        
    except Exception as e:
        logger.error(f"Error uploading {file_path}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    """Main function to upload all real-world files."""
    logger.info("Starting upload of real-world PDF files...")
    
    # Get database session
    db = next(get_db())
    
    # Get real files directory
    real_files_dir = Path(__file__).parent / "tests" / "real-files"
    
    if not real_files_dir.exists():
        logger.error(f"Real files directory not found: {real_files_dir}")
        return
    
    results = []
    
    # Process each file
    for filename, restaurant_name in FILE_RESTAURANT_MAPPING.items():
        file_path = real_files_dir / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Get restaurant
        restaurant = await get_restaurant_by_name(db, restaurant_name)
        if not restaurant:
            logger.error(f"Restaurant not found: {restaurant_name}")
            continue
        
        # Upload file
        result = await upload_file_to_restaurant(str(file_path), restaurant, db)
        result["filename"] = filename
        result["restaurant"] = restaurant_name
        results.append(result)
        
        logger.info(f"Completed processing {filename}")
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("UPLOAD SUMMARY")
    logger.info("="*50)
    
    successful = 0
    total_entries = 0
    
    for result in results:
        if result["success"]:
            successful += 1
            total_entries += result["extracted_entries"]
            logger.info(f"✅ {result['filename']} -> {result['restaurant']}: {result['extracted_entries']} entries")
        else:
            logger.error(f"❌ {result['filename']} -> {result['restaurant']}: {result['error']}")
    
    logger.info(f"\nTotal files processed: {len(results)}")
    logger.info(f"Successful uploads: {successful}")
    logger.info(f"Total wine entries extracted: {total_entries}")

if __name__ == "__main__":
    asyncio.run(main()) 