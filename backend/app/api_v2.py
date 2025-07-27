import logging
import sys
import traceback

# Configure logging first
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("[api_v2] Starting imports...")
    
    from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Query
    logger.info("[api_v2] FastAPI imports successful")
    
    from sqlalchemy.orm import Session
    logger.info("[api_v2] SQLAlchemy imports successful")
    
    from app.models import User, Restaurant, WineListFile, WineEntry, Ruleset, WineListFileStatus
    logger.info("[api_v2] Models imports successful")
    
    from app.supabase_auth import get_current_user, require_role
    logger.info("[api_v2] Supabase auth imports successful")
    
    from app.database import get_db
    logger.info("[api_v2] Database imports successful")
    
    from pydantic import BaseModel
    from typing import Optional, List, Dict, Any
    from uuid import UUID, uuid4
    logger.info("[api_v2] Standard library imports successful")
    
    import os
    import tempfile
    import requests
    from datetime import datetime
    import json
    logger.info("[api_v2] Additional standard library imports successful")

    logger.info("[api_v2] Attempting to import PDF processing modules...")
    from app.pdf_processing.extractor import PDFExtractor, ExtractionConfig, ExtractionStrategy
    logger.info("[api_v2] PDF extractor imports successful")
    
    from app.pdf_processing.preprocessor import PDFPreprocessor, PreprocessingConfig
    logger.info("[api_v2] PDF preprocessor imports successful")
    
    from app.pdf_processing.metadata import PDFMetadataExtractor
    logger.info("[api_v2] PDF metadata imports successful")
    
    from app.pdf_processing.exceptions import PDFProcessingError, PDFExtractionError, OCRProcessingError, MetadataExtractionError, PreprocessingError
    logger.info("[api_v2] PDF exceptions imports successful")
    
    from app.fieldextractor.fieldextractor import FieldExtractor
    logger.info("[api_v2] Field extractor imports successful")
    
    from app.rules.rule_manager import RuleManager
    logger.info("[api_v2] Rule manager imports successful")
    
    from app.storage import save_file, get_file_url, save_processing_data, cleanup_wine_list_data
    logger.info("[api_v2] Storage imports successful")
    
    from app.pdf_processing.categorizer import PDFBlockCategorizer
    logger.info("[api_v2] PDF categorizer imports successful")
    
    from app.rules.hybrid_extraction_pipeline import HybridExtractionPipeline
    logger.info("[api_v2] Hybrid extraction pipeline imports successful")
    
    from app.config import AI_RULE_GENERATION_ENABLED
    logger.info("[api_v2] Config imports successful")
    
    logger.info("[api_v2] All imports completed successfully")

except ImportError as e:
    logger.error(f"[api_v2] Import error: {e}")
    logger.error(f"[api_v2] Traceback: {traceback.format_exc()}")
    raise
except Exception as e:
    logger.error(f"[api_v2] Unexpected error during imports: {type(e).__name__}: {e}")
    logger.error(f"[api_v2] Traceback: {traceback.format_exc()}")
    raise

logger.setLevel(logging.INFO)
logger.info("[api_v2] Module loaded.")

# Initialize router
api_router = APIRouter(tags=["api_v2"])

# --- Pydantic Models ---
class RestaurantCreate(BaseModel):
    name: str
    wine_list_url: Optional[str] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    wine_list_url: Optional[str] = None

class WineListFileCreate(BaseModel):
    restaurant_id: UUID
    filename: str
    file_url: str
    parsed_date: Optional[str] = None
    notes: Optional[str] = None

class WineEntryUpdate(BaseModel):
    producer: Optional[str] = None
    cuvee: Optional[str] = None
    type: Optional[str] = None
    vintage: Optional[str] = None
    price: Optional[str] = None
    bottle_size: Optional[str] = None
    grape_variety: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    subregion: Optional[str] = None
    row_confidence: Optional[float] = None
    field_confidence: Optional[dict] = None
    section_header: Optional[str] = None
    subheader: Optional[str] = None
    raw_text: Optional[str] = None
    status: Optional[str] = None
    designation: Optional[str] = None
    classification: Optional[str] = None
    sub_type: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = "staff"
    restaurant_id: Optional[UUID] = None
    supabase_user_id: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    restaurant_id: Optional[UUID] = None

class RulesetUpdate(BaseModel):
    rules_json: dict

# --- Helper Functions ---
async def download_file(url: str) -> str:
    """Download a file from URL and save to temporary file."""
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to download file from storage")
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(response.content)
    temp_file.close()
    return temp_file.name

async def process_pdf(file_path: str, restaurant_id: str, wine_list_id: str, db: Session) -> tuple:
    logger.info(f"[api_v2] process_pdf called for {file_path}, restaurant_id={restaurant_id}, wine_list_id={wine_list_id}")
    try:
        # Initialize PDF processing components
        extractor = PDFExtractor(ExtractionConfig(strategy=ExtractionStrategy.HYBRID))
        preprocessor = PDFPreprocessor(PreprocessingConfig())
        categorizer = PDFBlockCategorizer()
        metadata_extractor = PDFMetadataExtractor()
        
        # Extract text and metadata
        pages, metadata = extractor.extract(file_path)
        metadata = metadata_extractor.extract(file_path)
        
        # Save extractor output
        await save_processing_data(wine_list_id, "extractor", {
            "pages": pages,
            "metadata": metadata
        })
        
        # Preprocess text blocks
        processed_pages = preprocessor.preprocess(pages)
        
        # Save preprocessor output
        await save_processing_data(wine_list_id, "preprocessor", {
            "processed_pages": processed_pages
        })
        
        # Categorize text blocks
        categorized_pages = categorizer.categorize(processed_pages)
        
        # Save categorizer output
        await save_processing_data(wine_list_id, "categorizer", {
            "categorized_pages": categorized_pages
        })
        
        # Filter for wine entries and combine into text
        wine_blocks = []
        for block in categorized_pages:
            if block['type'] == 'wine_entry':
                wine_blocks.append(block)
        
        # Initialize hybrid extraction pipeline
        if AI_RULE_GENERATION_ENABLED:
            # Use new AI Hybrid Rule Generation System
            logger.info("Using AI Hybrid Rule Generation System")
            hybrid_pipeline = HybridExtractionPipeline(restaurant_id)
            pipeline_results = hybrid_pipeline.process_wine_list(wine_blocks)
            
            # Extract results from pipeline
            extraction_results = pipeline_results.get('extraction_results', [])
            metadata.update(pipeline_results.get('metadata', {}))
            
            # Convert pipeline results to expected format
            extracted_fields = []
            for result in extraction_results:
                if result is None:
                    logger.warning("Found None result in extraction_results, skipping")
                    continue
                    
                fields = result.get('fields', {})
                if fields is None:
                    logger.warning("Found None fields in result, using empty dict")
                    fields = {}
                    
                # Convert to expected format
                converted_fields = {}
                for field_name, field_data in fields.items():
                    if field_data is None:
                        converted_fields[field_name] = {'value': None, 'confidence': 0.0}
                    elif isinstance(field_data, dict):
                        converted_fields[field_name] = field_data
                    else:
                        converted_fields[field_name] = {'value': field_data, 'confidence': 0.8}
                
                # Ensure we have at least one field to prevent empty entries
                if not converted_fields:
                    converted_fields = {
                        'producer_name': {'value': None, 'confidence': 0.0},
                        'wine_name': {'value': None, 'confidence': 0.0}
                    }
                
                extracted_fields.append(converted_fields)
            
            # Prepare learning results for backward compatibility
            learning_results = {
                'summary': pipeline_results.get('metadata', {}),
                'new_rules': {},  # Rules are now managed by the pipeline
                'hybrid_system_used': True,
                'pipeline_results': pipeline_results
            }
            
        else:
            # Use legacy system
            logger.info("Using legacy extraction system")
            
            # Initialize field extractor and rule manager
            field_extractor = FieldExtractor(restaurant_id=restaurant_id)
            rule_manager = RuleManager()
            
            # Get restaurant-specific rules
            rules = rule_manager.load_rules(restaurant_id)
            
            # Extract fields from wine blocks
            extracted_fields = field_extractor.extract_batch(wine_blocks)
            
            # Save initial field extraction output
            await save_processing_data(wine_list_id, "field_extractor", {
                "extracted_fields": extracted_fields,
                "wine_blocks": wine_blocks
            })
            
            # Initialize learning pipeline
            from app.rules.rule_learner import RuleLearner
            learner = RuleLearner(restaurant_id)
            
            # Learn from initial extraction
            learning_results = learner.analyze_entries(extracted_fields, sample_size=3)
            
            # Save learning results
            await save_processing_data(wine_list_id, "learning", {
                "learning_results": learning_results
            })
            
            # Reparse with new rules if learning was successful
            if learning_results.get('new_rules'):
                # Update field extractor with new rules
                field_extractor = FieldExtractor(restaurant_id=restaurant_id)
                # Reparse all entries
                extracted_fields = field_extractor.extract_batch(wine_blocks)
                
                # Save reparsed results
                await save_processing_data(wine_list_id, "field_extractor", {
                    "extracted_fields": extracted_fields,
                    "wine_blocks": wine_blocks
                }, version="reparsed")
        
        return extracted_fields, metadata, learning_results, wine_blocks
        
    except Exception as e:
        logger.error(f"[api_v2] Exception in process_pdf: {e}")
        raise PDFProcessingError(f"Failed to process PDF: {str(e)}")

def extract_value(field):
    """Extract value from field with robust None handling."""
    if field is None:
        return None
    
    if isinstance(field, dict):
        if 'value' in field:
            # Handle nested value structure
            if isinstance(field['value'], dict) and 'value' in field['value']:
                return field['value']['value']
            return field['value']
        # If no 'value' key, return the first non-None value
        for key, val in field.items():
            if val is not None and key != 'confidence' and key != 'provenance':
                return val
        return None
    return field

# --- API Endpoints ---
@api_router.post("/wine-lists/upload")
async def upload_wine_list(
    file: UploadFile = File(...),
    restaurant_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    logger.info("[api_v2] upload_wine_list endpoint called.")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file size (limit to 50MB)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
    
    try:
        # Save file to storage
        file_url = await save_file(file, restaurant_id)
        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to save file")
            
        # Download file for processing
        file_path = await download_file(file_url)
        if not file_path:
            raise HTTPException(status_code=500, detail="Failed to download file")
            
        try:
            # Create wine list entry first to get ID
            wine_list = WineListFile(
                restaurant_id=restaurant_id,
                filename=file.filename,
                file_url=file_url,
                status=WineListFileStatus.processing,
                metadata={}
            )
            db.add(wine_list)
            db.commit()
            db.refresh(wine_list)
            
            # Process PDF with wine list ID for data storage
            try:
                extracted_fields, metadata, learning_results, wine_blocks = await process_pdf(file_path, restaurant_id, str(wine_list.id), db)
            except Exception as processing_error:
                logger.error(f"PDF processing failed: {processing_error}")
                # Update status to error
                wine_list.status = WineListFileStatus.error
                wine_list.notes = f"Processing failed: {str(processing_error)}"
                db.commit()
                raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(processing_error)}")
            
            # Update wine list with results
            wine_list.status = WineListFileStatus.parsed
            wine_list.metadata = metadata
            wine_list.learning_results = learning_results
            wine_list.learning_date = datetime.utcnow()
            db.commit()

            # Store extracted fields as WineEntry rows
            for i, entry in enumerate(extracted_fields):
                # Get the original block text for raw_text field
                raw_text = wine_blocks[i].get('text') if i < len(wine_blocks) else None
                
                # Ensure entry is not None
                if entry is None:
                    logger.warning(f"Entry at index {i} is None, skipping")
                    continue
                
                wine_entry = WineEntry(
                    wine_list_file_id=wine_list.id,
                    restaurant_id=restaurant_id,
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
                    row_confidence=extract_value(entry.get('row_confidence')),
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

            # Clean up temporary file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            return {
                "id": wine_list.id,
                "status": wine_list.status,
                "message": "Wine list processed successfully",
                "learning_results": learning_results
            }
            
        except Exception as e:
            logger.error(f"Error processing wine list: {str(e)}")
            # Update status to error
            wine_list.status = WineListFileStatus.error
            wine_list.notes = str(e)
            db.commit()
            
            # Clean up temporary file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            raise HTTPException(status_code=500, detail=f"Error processing wine list: {str(e)}")
            
    except Exception as e:
        logger.error(f"[api_v2] Exception in upload_wine_list: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading wine list: {str(e)}")

@api_router.get("/wine-lists/{file_id}")
def get_wine_list(file_id: str, db: Session = Depends(get_db)):
    """Get a specific wine list file."""
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    return wine_list

@api_router.delete("/wine-lists/{file_id}")
async def delete_wine_list(file_id: str, db: Session = Depends(get_db)):
    """Delete a wine list file and all associated data."""
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    
    try:
        # Clean up all associated data from storage
        await cleanup_wine_list_data(str(wine_list.id), wine_list.file_url)
        
        # Delete from database (cascade will handle wine entries)
        db.delete(wine_list)
        db.commit()
        
        return {"detail": "Wine list and all associated data deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting wine list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting wine list: {str(e)}")

@api_router.get("/wine-lists/{file_id}/processing-data")
async def get_processing_data_endpoint(
    file_id: str,
    stage: Optional[str] = Query(None, description="Specific processing stage to retrieve"),
    version: Optional[str] = Query(None, description="Version of the data to retrieve"),
    db: Session = Depends(get_db)
):
    """Get processing data for a wine list."""
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    
    try:
        from app.storage import get_processing_data, list_processing_stages
        
        if stage:
            # Get specific stage data
            data = await get_processing_data(str(wine_list.id), stage, version)
            if not data:
                raise HTTPException(status_code=404, detail=f"No data found for stage: {stage}")
            return {"stage": stage, "data": data}
        else:
            # List all available stages
            stages = await list_processing_stages(str(wine_list.id))
            return {"stages": stages}
            
    except Exception as e:
        logger.error(f"Error retrieving processing data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving processing data: {str(e)}")

@api_router.get("/restaurants/{id}/wine-lists")
def list_wine_lists_for_restaurant(id: str, db: Session = Depends(get_db)):
    """List all wine lists for a restaurant."""
    return db.query(WineListFile).filter_by(restaurant_id=id).all()

@api_router.get("/wine-entries/{file_id}")
def list_wine_entries(file_id: str, db: Session = Depends(get_db)):
    """List all wine entries for a wine list."""
    return db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()

@api_router.put("/wine-entries/{wine_entry_id}")
def update_wine_entry(wine_entry_id: str, data: WineEntryUpdate, db: Session = Depends(get_db)):
    """Update a wine entry."""
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry

@api_router.put("/wine-entries/bulk")
def bulk_update_wine_entries(entries: list[dict], db: Session = Depends(get_db)):
    """Bulk update wine entries."""
    updated = []
    for entry_data in entries:
        entry = db.query(WineEntry).get(entry_data["id"])
        if entry:
            for k, v in entry_data.items():
                if k != "id":
                    setattr(entry, k, v)
            db.commit()
            db.refresh(entry)
            updated.append(entry)
    return {"updated": updated}

@api_router.post("/wine-entries/{wine_entry_id}/reject")
def reject_wine_entry(wine_entry_id: str, db: Session = Depends(get_db)):
    """Reject a wine entry."""
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    return {"status": "rejected"}

@api_router.get("/restaurants")
def list_restaurants(db: Session = Depends(get_db)):
    """List all restaurants."""
    return db.query(Restaurant).all()

@api_router.post("/restaurants")
def create_restaurant(data: RestaurantCreate, db: Session = Depends(get_db)):
    """Create a new restaurant."""
    restaurant = Restaurant(**data.dict())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@api_router.get("/restaurants/{id}")
def get_restaurant(id: str, db: Session = Depends(get_db)):
    """Get a specific restaurant."""
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@api_router.put("/restaurants/{id}")
def update_restaurant(id: str, data: RestaurantUpdate, db: Session = Depends(get_db)):
    """Update a restaurant."""
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(restaurant, k, v)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@api_router.delete("/restaurants/{id}")
def delete_restaurant(id: str, db: Session = Depends(get_db)):
    """Delete a restaurant."""
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(restaurant)
    db.commit()
    return {"detail": "Deleted"}

@api_router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all users."""
    return db.query(User).all()

@api_router.post("/users")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter_by(supabase_user_id=data.supabase_user_id).first():
        raise HTTPException(status_code=400, detail="Supabase user ID already registered")
    user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        restaurant_id=data.restaurant_id,
        supabase_user_id=data.supabase_user_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@api_router.put("/users/{id}")
def update_user(id: str, data: UserUpdate, db: Session = Depends(get_db)):
    """Update a user."""
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user

@api_router.delete("/users/{id}")
def delete_user(id: str, db: Session = Depends(get_db)):
    """Delete a user."""
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "Deleted"}

@api_router.get("/restaurants/{id}/ruleset")
def get_ruleset(id: str, db: Session = Depends(get_db)):
    """Get ruleset for a restaurant."""
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    return ruleset

@api_router.put("/restaurants/{id}/ruleset")
def update_ruleset(id: str, data: RulesetUpdate, db: Session = Depends(get_db)):
    """Update ruleset for a restaurant."""
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    ruleset.rules_json = data.rules_json
    db.commit()
    db.refresh(ruleset)
    return ruleset

@api_router.delete("/restaurants/{id}/ruleset")
def delete_ruleset(id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    """Delete ruleset for a restaurant (clear all rules)."""
    try:
        logger.info(f"Attempting to delete ruleset for restaurant {id} by user {current_user.id}")
        
        # Check if restaurant exists
        restaurant = db.query(Restaurant).filter_by(id=id).first()
        if not restaurant:
            logger.warning(f"Restaurant {id} not found")
            raise HTTPException(status_code=404, detail="Restaurant not found")
        
        # Find and delete the ruleset
        ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
        if ruleset:
            logger.info(f"Found ruleset for restaurant {id}, deleting...")
            db.delete(ruleset)
            db.commit()
            logger.info(f"Ruleset deleted successfully for restaurant {id} by user {current_user.id}")
            return {"message": "Ruleset cleared successfully"}
        else:
            logger.info(f"No ruleset found for restaurant {id}")
            # No ruleset exists, but that's okay - return success
            return {"message": "No ruleset found to clear"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ruleset for restaurant {id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clear ruleset")

@api_router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "restaurant_id": current_user.restaurant_id
    }

@api_router.post("/wine-lists/{file_id}/learn")
async def learn_from_wine_list(
    file_id: str,
    sample_size: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Learn new rules from a wine list using AI analysis."""
    try:
        # Get wine list and entries
        wine_list = db.query(WineListFile).get(file_id)
        if not wine_list:
            raise HTTPException(status_code=404, detail="Wine list not found")
            
        entries = db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()
        if not entries:
            raise HTTPException(status_code=404, detail="No wine entries found")
            
        # Convert entries to format expected by RuleLearner
        entry_dicts = []
        for entry in entries:
            entry_dict = {
                'text': entry.raw_text,
                'producer_name': entry.producer,
                'wine_name': entry.cuvee,
                'vintage': entry.vintage,
                'price': entry.price,
                'region': entry.region,
                'country': entry.country,
                'grape_variety': entry.grape_variety,
                'type': entry.type,
                'sub_type': entry.sub_type,
                'designation': entry.designation,
                'classification': entry.classification
            }
            entry_dicts.append(entry_dict)
            
        # Initialize rule learner and analyze entries
        from app.rules.rule_learner import RuleLearner
        learner = RuleLearner(wine_list.restaurant_id)
        analysis_results = learner.analyze_entries(entry_dicts, sample_size)
        
        # Reparse entries with new rules
        from app.fieldextractor.fieldextractor import FieldExtractor
        field_extractor = FieldExtractor(restaurant_id=wine_list.restaurant_id)
        
        updated_entries = []
        for entry in entries:
            extracted_fields = field_extractor.extract({'text': entry.raw_text})
            
            # Update entry with new extraction results
            for field, value in extracted_fields.items():
                if hasattr(entry, field):
                    setattr(entry, field, value['value'])
                    entry.field_confidence = value['confidence']
            
            db.add(entry)
            updated_entries.append(entry)
        
        db.commit()
        
        return {
            "message": "Learning completed successfully",
            "analysis_results": analysis_results,
            "updated_entries": len(updated_entries)
        }
        
    except Exception as e:
        logger.error(f"Error in learning pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in learning pipeline: {str(e)}") 