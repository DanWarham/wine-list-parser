from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.models import User, Restaurant, WineListFile, WineEntry, Ruleset
from app.supabase_auth import get_current_user, require_role  # updated import
from app.database import get_db, SessionLocal  # You should have a get_db dependency for DB sessions
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.config import supabase
from app.pdf_extraction import extract_pdf_text_with_ocr, save_extraction_to_json, extract_date_from_pdf_metadata, extract_date_from_filename
import os
import tempfile
import re
from app.preprocessing import preprocess_extraction, detect_sections
from app.wine_segmentation import segment_wine_entries
from app.parsing import extract_fields_for_entries, parse_wine_list, GLOBAL_RULES
import pandas as pd
import numpy as np
from datetime import datetime, date
import logging
from app.ai_parsing import parse_wine_entries
from app.lwin import match_lwin_batch, enrich_wine_entry as lwin_enrich_wine_entry
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Split routers
api_router = APIRouter(tags=["api"])

# --- Pydantic Schemas ---
class RestaurantCreate(BaseModel):
    name: str
    wine_list_url: Optional[str] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    wine_list_url: Optional[str] = None

class WineListFileCreate(BaseModel):
    restaurant_id: uuid.UUID
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
    restaurant_id: Optional[uuid.UUID] = None
    supabase_user_id: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    restaurant_id: Optional[uuid.UUID] = None

class RulesetUpdate(BaseModel):
    rules_json: dict

class SyncUserRequest(BaseModel):
    supabase_user_id: str
    email: str

# --- API Endpoints (resources) ---
@api_router.get("/restaurants", dependencies=[Depends(require_role("admin"))])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()

@api_router.post("/restaurants", dependencies=[Depends(require_role("admin"))])
def create_restaurant(data: RestaurantCreate, db: Session = Depends(get_db)):
    restaurant = Restaurant(**data.dict())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@api_router.get("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def get_restaurant(id: str, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@api_router.put("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def update_restaurant(id: str, data: RestaurantUpdate, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(restaurant, k, v)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@api_router.delete("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def delete_restaurant(id: str, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(restaurant)
    db.commit()
    return {"detail": "Deleted"}

@api_router.post("/wine-lists/upload", dependencies=[Depends(require_role("admin"))])
def upload_wine_list(
    file: UploadFile = File(...),
    restaurant_id: str = Form(...),
    parsed_date: str = Form(None),
    db: Session = Depends(get_db)
):
    file_bytes = file.file.read()  # Read file content once

    # --- Date extraction logic ---
    _parsed_date = None
    if parsed_date:
        try:
            _parsed_date = datetime.strptime(parsed_date, "%Y-%m-%d").date()
        except Exception:
            _parsed_date = None
    if not _parsed_date:
        _parsed_date = extract_date_from_filename(file.filename)
    if not _parsed_date:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        _parsed_date = extract_date_from_pdf_metadata(tmp_path)
        os.remove(tmp_path)
    if not _parsed_date:
        _parsed_date = date.today()
    # --- End date extraction logic ---

    # Upload to Supabase Storage
    bucket_name = "wine-lists"
    supabase.storage.from_(bucket_name).upload(file.filename, file_bytes, {"content-type": file.content_type or "application/pdf"})
    file_url = supabase.storage.from_(bucket_name).get_public_url(file.filename)

    # Create wine list record with initial status
    wine_list = WineListFile(
        restaurant_id=restaurant_id,
        filename=file.filename,
        file_url=file_url,
        status="uploaded",
        parsed_date=_parsed_date,
    )
    db.add(wine_list)
    db.commit()
    db.refresh(wine_list)

    # Start async processing
    import threading
    from app.database import SessionLocal  # Import SessionLocal for new session

    def make_json_serializable(obj):
        import math
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(v) for v in obj]
        elif isinstance(obj, (pd.Timestamp, np.datetime64)):
            return str(obj)
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif hasattr(obj, 'isna') and obj.isna():  # pandas NA
            return None
        elif isinstance(obj, (np.floating, np.integer)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj.item()
        elif obj is None:
            return None
        else:
            return obj

    def process_file(wine_list_id: str):
        # Create new database session for this thread
        thread_db = SessionLocal()
        try:
            # Get fresh wine_list object in this session
            wine_list = thread_db.query(WineListFile).get(wine_list_id)
            if not wine_list:
                logger.error(f"[ERROR] Wine list {wine_list_id} not found in thread")
                return

            # Save a local temp copy for extraction
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            # Update status to processing
            wine_list.status = "processing"
            logger.info(f"Setting wine_list {wine_list.id} status to 'processing'")
            thread_db.commit()
            thread_db.flush()
            logger.info(f"wine_list {wine_list.id} status after commit: {wine_list.status}")

            logger.info(f"Starting PDF extraction for wine_list {wine_list.id}")
            pages = extract_pdf_text_with_ocr(tmp_path)
            logger.info(f"Finished PDF extraction for wine_list {wine_list.id}")

            logger.info(f"Starting preprocessing for wine_list {wine_list.id}")
            cleaned_pages = preprocess_extraction(pages)
            logger.info(f"Finished preprocessing for wine_list {wine_list.id}")

            logger.info(f"Starting section detection for wine_list {wine_list.id}")
            lines_with_sections = detect_sections(cleaned_pages)
            logger.info(f"Finished section detection for wine_list {wine_list.id}")

            logger.info(f"Starting segmentation for wine_list {wine_list.id}")
            wine_entries = segment_wine_entries(lines_with_sections)
            logger.info(f"Finished segmentation for wine_list {wine_list.id}")

            logger.info(f"Starting multi-stage parsing pipeline for wine_list {wine_list.id}")
            ruleset_obj = thread_db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
            ruleset = ruleset_obj.rules_json if ruleset_obj else None
            final_entries, refinement_data = parse_wine_list(wine_entries, ruleset)
            logger.info(f"Finished multi-stage parsing for wine_list {wine_list.id}")

            logger.info(f"Starting DB entry creation for wine_list {wine_list.id}")
            # Get valid WineEntry fields dynamically
            valid_fields = set(c.name for c in WineEntry.__table__.columns)
            for entry in final_entries:
                db_entry = {k: v for k, v in entry.items() if k in valid_fields and k != 'extra_data'}
                # Store all extra fields in extra_data
                extra_data = {k: v for k, v in entry.items() if k not in valid_fields or k == 'provenance' or k == 'lwin_match_info' or k == 'lwin_suggestions'}
                extra_data = make_json_serializable(extra_data)
                wine_entry = WineEntry(
                    wine_list_file_id=wine_list.id,
                    restaurant_id=restaurant_id,
                    **db_entry,
                    extra_data=extra_data if extra_data else None
                )
                thread_db.add(wine_entry)
            logger.info(f"Finished DB entry creation for wine_list {wine_list.id}")

            # Save extraction and refinement data to JSON for debugging
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            specs_dir = os.path.join(project_root, "specs")
            os.makedirs(specs_dir, exist_ok=True)
            safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
            json_filename = f"extracted_{safe_filename}.json"
            json_path = os.path.join(specs_dir, json_filename)
            save_extraction_to_json(wine_entries, json_path)
            # Save refinement data
            refinement_filename = f"refinement_{safe_filename}.json"
            refinement_path = os.path.join(specs_dir, refinement_filename)
            import json as _json
            # Make refinement_data JSON serializable before saving
            serializable_refinement_data = make_json_serializable(refinement_data)
            with open(refinement_path, "w", encoding="utf-8") as f:
                _json.dump(serializable_refinement_data, f, ensure_ascii=False, indent=2)

            # Update wine list status and notes
            wine_list.status = "parsed"
            wine_list.notes = f"extraction_json: specs/{json_filename}; refinement_json: specs/{refinement_filename}"
            logger.info(f"Setting wine_list {wine_list.id} status to 'parsed'")
            thread_db.commit()
            thread_db.flush()
            logger.info(f"wine_list {wine_list.id} status after commit: {wine_list.status}")

            # Clean up temp file
            os.remove(tmp_path)

        except Exception as e:
            # Log error and update status
            logger.error(f"Error processing file: {str(e)}")
            if 'wine_list' in locals():
                wine_list.status = "error"
                wine_list.notes = f"Error: {str(e)}"
                logger.error(f"[DEBUG] Setting wine_list {wine_list.id} status to 'error'")
                thread_db.commit()
                thread_db.flush()
                logger.error(f"wine_list {wine_list.id} status after commit: {wine_list.status}")
        finally:
            # Always close the thread's database session
            thread_db.close()

    # Start processing in background thread
    thread = threading.Thread(target=process_file, args=(str(wine_list.id),))
    thread.start()

    return {
        "file_id": str(wine_list.id),
        "status": wine_list.status.value if hasattr(wine_list.status, 'value') else wine_list.status,
        "upload_url": file_url
    }

@api_router.get("/wine-lists/{file_id}", dependencies=[Depends(require_role("admin"))])
def get_wine_list(file_id: str, db: Session = Depends(get_db)):
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    return wine_list

@api_router.delete("/wine-lists/{file_id}", dependencies=[Depends(require_role("admin"))])
def delete_wine_list(file_id: str, db: Session = Depends(get_db)):
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    db.delete(wine_list)
    db.commit()
    return {"detail": "Deleted"}

@api_router.get("/restaurants/{id}/wine-lists", dependencies=[Depends(require_role("admin"))])
def list_wine_lists_for_restaurant(id: str, db: Session = Depends(get_db)):
    return db.query(WineListFile).filter_by(restaurant_id=id).all()

@api_router.get("/wine-entries/{file_id}", dependencies=[Depends(require_role("admin"))])
def list_wine_entries(file_id: str, db: Session = Depends(get_db)):
    return db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()

@api_router.put("/wine-entries/{wine_entry_id}", dependencies=[Depends(require_role("admin"))])
def update_wine_entry(wine_entry_id: str, data: WineEntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry

@api_router.put("/wine-entries/bulk", dependencies=[Depends(require_role("admin"))])
def bulk_update_wine_entries(entries: list[dict], db: Session = Depends(get_db)):
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

@api_router.post("/wine-entries/{wine_entry_id}/reject", dependencies=[Depends(require_role("admin"))])
def reject_wine_entry(wine_entry_id: str, db: Session = Depends(get_db)):
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    return {"status": "rejected"}

@api_router.get("/users", dependencies=[Depends(require_role("admin"))])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@api_router.post("/users")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
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

@api_router.put("/users/{id}", dependencies=[Depends(require_role("admin"))])
def update_user(id: str, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user

@api_router.delete("/users/{id}", dependencies=[Depends(require_role("admin"))])
def delete_user(id: str, db: Session = Depends(get_db)):
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "Deleted"}

@api_router.get("/restaurants/{id}/ruleset", dependencies=[Depends(require_role("admin"))])
def get_ruleset(id: str, db: Session = Depends(get_db)):
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    return ruleset

@api_router.put("/restaurants/{id}/ruleset", dependencies=[Depends(require_role("admin"))])
def update_ruleset(id: str, data: RulesetUpdate, db: Session = Depends(get_db)):
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    ruleset.rules_json = data.rules_json
    db.commit()
    db.refresh(ruleset)
    return ruleset

@api_router.post("/restaurants/{id}/ruleset/train", dependencies=[Depends(require_role("admin"))])
def train_ruleset(id: str, db: Session = Depends(get_db)):
    # Training logic to be implemented
    return {"detail": "Not implemented"}

@api_router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "restaurant_id": current_user.restaurant_id
    }

@api_router.get("/wine-lists/{file_id}/entries", dependencies=[Depends(require_role("admin"))])
def list_wine_list_entries(file_id: str, db: Session = Depends(get_db)):
    entries = db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()
    # Convert to dict and merge extra_data fields
    result = []
    for entry in entries:
        entry_dict = {
            "id": str(entry.id),
            "producer": entry.producer,
            "cuvee": entry.cuvee,
            "type": entry.type,
            "vintage": entry.vintage,
            "price": entry.price,
            "bottle_size": entry.bottle_size,
            "grape_variety": entry.grape_variety,
            "country": entry.country,
            "region": entry.region,
            "subregion": entry.subregion,
            "row_confidence": entry.row_confidence,
            "field_confidence": entry.field_confidence or {},
            "section_header": entry.section_header,
            "subheader": entry.subheader,
            "raw_text": entry.raw_text,
            "designation": entry.designation,
            "classification": entry.classification,
            "sub_type": entry.sub_type,
            "status": entry.status.value if entry.status else None,
            "last_modified": entry.last_modified.isoformat() if entry.last_modified else None
        }
        # Merge extra_data fields if they exist
        if entry.extra_data:
            entry_dict.update(entry.extra_data)
        result.append(entry_dict)
    return result

@api_router.post("/wine-lists/{file_id}/refinement/random", dependencies=[Depends(require_role("admin"))])
def get_random_wine_for_refinement(file_id: str, db: Session = Depends(get_db)):
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    entries = db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()
    if not entries:
        raise HTTPException(status_code=404, detail="No wine entries found for this file")
    import random
    entry = random.choice(entries)
    # Check if key fields are missing
    key_fields = ["producer", "cuvee", "vintage", "price", "type"]
    needs_parse = any(getattr(entry, f, None) in (None, "") for f in key_fields)
    if needs_parse:
        # Parse with global rules (stateless, do not save)
        entry_dict = {c.name: getattr(entry, c.name) for c in WineEntry.__table__.columns}
        entry_dict['raw_text'] = entry.raw_text
        parsed, _ = extract_fields_for_entries([entry_dict], ruleset=None, global_rules=GLOBAL_RULES)
        enriched = entry_dict.copy()
        enriched.update(parsed[0])
        enriched['id'] = str(entry.id)
        return enriched
    else:
        # Return as dict (with id as str)
        entry_dict = {c.name: getattr(entry, c.name) for c in WineEntry.__table__.columns}
        entry_dict['id'] = str(entry.id)
        return entry_dict

class WineRefinementUpdate(BaseModel):
    entry_id: str
    fields: dict

@api_router.post("/wine-lists/{file_id}/refinement/update", dependencies=[Depends(require_role("admin"))])
def update_wine_refinement_and_generate_rule(file_id: str, data: WineRefinementUpdate, db: Session = Depends(get_db)):
    # Update the wine entry with user corrections
    entry = db.query(WineEntry).get(data.entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    for k, v in data.fields.items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    # Generate/update ruleset for the restaurant
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    # For now, just log the correction; rule generation logic can be expanded
    # Re-parse the file with the new rule (pseudo-code, to be implemented)
    # parse_wine_list_again(wine_list, new_rule_from_correction)
    # Select next random wine for refinement
    entries = db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()
    import random
    entry = random.choice(entries)
    return entry

@api_router.get("/wine-lists/{file_id}/refinement-data", dependencies=[Depends(require_role("admin"))])
def get_wine_list_refinement_data(file_id: str, db: Session = Depends(get_db)):
    """
    Return the refinement data (JSON) for a given wine list file.
    Looks up the specs/refinement_{filename}.json referenced in wine_list.notes.
    """
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    # Parse the refinement_json path from notes
    import re, os, json
    notes = wine_list.notes or ""
    match = re.search(r"refinement_json: ([^;\n]+)", notes)
    if not match:
        raise HTTPException(status_code=404, detail="No refinement data found for this wine list")
    refinement_path = match.group(1)
    # Compute absolute path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_path = os.path.join(project_root, refinement_path) if not os.path.isabs(refinement_path) else refinement_path
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Refinement data file not found")
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading refinement data: {str(e)}")

@api_router.post("/wine-entries/{wine_entry_id}/refine/ai", dependencies=[Depends(require_role("admin"))])
def refine_wine_entry_ai(wine_entry_id: str, db: Session = Depends(get_db)):
    """
    Refine a wine entry using AI (does not save, just returns the enriched entry).
    """
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    # Prepare entry dict for AI
    entry_dict = {c.name: getattr(entry, c.name) for c in WineEntry.__table__.columns}
    entry_dict['raw_text'] = entry.raw_text
    # Run AI parser
    enriched = parse_wine_entries([entry_dict])[0]
    # Merge with original fields
    for k, v in enriched.items():
        if v is not None:
            entry_dict[k] = v
    return entry_dict

@api_router.post("/wine-entries/{wine_entry_id}/refine/lwin", dependencies=[Depends(require_role("admin"))])
def refine_wine_entry_lwin(wine_entry_id: str, db: Session = Depends(get_db)):
    """
    Refine a wine entry using LWIN (does not save, just returns the enriched entry).
    """
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    # Prepare entry dict for LWIN
    entry_dict = {c.name: getattr(entry, c.name) for c in WineEntry.__table__.columns}
    entry_dict['raw_text'] = entry.raw_text
    # Run LWIN matcher
    lwin_matches = match_lwin_batch([entry_dict])
    lwin_match = lwin_matches[0] if lwin_matches else None
    if lwin_match:
        enriched = lwin_enrich_wine_entry(entry_dict, lwin_match)
        enriched['lwin_match_info'] = lwin_match
        return enriched
    else:
        return entry_dict

@api_router.post("/sync-user")
def sync_user(data: SyncUserRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(supabase_user_id=data.supabase_user_id).first()
    if not user:
        user = User(
            supabase_user_id=data.supabase_user_id,
            email=data.email,
            role="staff"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.email != data.email:
            user.email = data.email
            db.commit()
    return {"id": user.id, "role": user.role}
