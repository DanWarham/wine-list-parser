from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.models import User, Restaurant, WineListFile, WineEntry, Ruleset
from app.auth import hash_password, verify_password, create_access_token, get_current_user, require_role, create_tokens, decode_refresh_token
from app.database import get_db  # You should have a get_db dependency for DB sessions
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.s3_utils import upload_to_minio

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    restaurant_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

# --- Pydantic Schemas ---
class RestaurantCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None
    notes: Optional[str] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None

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

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: Optional[str] = "staff"
    restaurant_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    restaurant_id: Optional[UUID] = None

class RulesetUpdate(BaseModel):
    rules_json: dict

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        restaurant_id=data.restaurant_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role.value}}

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token, refresh_token = create_tokens({"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    }

@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id = payload.get("sub")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token, new_refresh_token = create_tokens({"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token
    }

@router.get("/protected-test")
def protected_test(current_user=Depends(get_current_user)):
    return {"msg": "You are authenticated!", "user": current_user}

@router.get("/admin-only")
def admin_only_route(current_user=Depends(require_role("admin"))):
    return {"msg": "Only admins can see this"}

# --- Restaurant CRUD ---
@router.get("/restaurants", dependencies=[Depends(require_role("admin"))])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()

@router.post("/restaurants", dependencies=[Depends(require_role("admin"))])
def create_restaurant(data: RestaurantCreate, db: Session = Depends(get_db)):
    restaurant = Restaurant(**data.dict())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@router.get("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def get_restaurant(id: str, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@router.put("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def update_restaurant(id: str, data: RestaurantUpdate, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(restaurant, k, v)
    db.commit()
    db.refresh(restaurant)
    return restaurant

@router.delete("/restaurants/{id}", dependencies=[Depends(require_role("admin"))])
def delete_restaurant(id: str, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(restaurant)
    db.commit()
    return {"detail": "Deleted"}

# --- Wine List File CRUD ---
@router.post("/wine-lists/upload", dependencies=[Depends(require_role("admin"))])
def upload_wine_list(
    file: UploadFile = File(...),
    restaurant_id: str = Form(...),
    parsed_date: str = Form(None),
    db: Session = Depends(get_db)
):
    # 1. Upload file to MinIO
    file_url = upload_to_minio(file, file.filename)
    # 2. Create WineListFile DB record
    wine_list = WineListFile(
        restaurant_id=restaurant_id,
        filename=file.filename,
        file_url=file_url,
        status="uploaded",
        parsed_date=parsed_date
    )
    db.add(wine_list)
    db.commit()
    db.refresh(wine_list)
    # 3. Return response
    return {"file_id": str(wine_list.id), "status": wine_list.status.value if hasattr(wine_list.status, 'value') else wine_list.status, "upload_url": file_url}

@router.get("/wine-lists/{file_id}", dependencies=[Depends(require_role("admin"))])
def get_wine_list(file_id: str, db: Session = Depends(get_db)):
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    return wine_list

@router.delete("/wine-lists/{file_id}", dependencies=[Depends(require_role("admin"))])
def delete_wine_list(file_id: str, db: Session = Depends(get_db)):
    wine_list = db.query(WineListFile).get(file_id)
    if not wine_list:
        raise HTTPException(status_code=404, detail="Wine list file not found")
    db.delete(wine_list)
    db.commit()
    return {"detail": "Deleted"}

@router.get("/restaurants/{id}/wine-lists", dependencies=[Depends(require_role("admin"))])
def list_wine_lists_for_restaurant(id: str, db: Session = Depends(get_db)):
    return db.query(WineListFile).filter_by(restaurant_id=id).all()

# --- Wine Entry CRUD ---
@router.get("/wine-entries/{file_id}", dependencies=[Depends(require_role("admin"))])
def list_wine_entries(file_id: str, db: Session = Depends(get_db)):
    return db.query(WineEntry).filter_by(wine_list_file_id=file_id).all()

@router.put("/wine-entries/{wine_entry_id}", dependencies=[Depends(require_role("admin"))])
def update_wine_entry(wine_entry_id: str, data: WineEntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return entry

@router.put("/wine-entries/bulk", dependencies=[Depends(require_role("admin"))])
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

@router.post("/wine-entries/{wine_entry_id}/reject", dependencies=[Depends(require_role("admin"))])
def reject_wine_entry(wine_entry_id: str, db: Session = Depends(get_db)):
    entry = db.query(WineEntry).get(wine_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Wine entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    return {"status": "rejected"}

# --- User CRUD ---
@router.get("/users", dependencies=[Depends(require_role("admin"))])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/users", dependencies=[Depends(require_role("admin"))])
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role=data.role,
        restaurant_id=data.restaurant_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{id}", dependencies=[Depends(require_role("admin"))])
def update_user(id: str, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{id}", dependencies=[Depends(require_role("admin"))])
def delete_user(id: str, db: Session = Depends(get_db)):
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "Deleted"}

# --- Ruleset CRUD ---
@router.get("/restaurants/{id}/ruleset", dependencies=[Depends(require_role("admin"))])
def get_ruleset(id: str, db: Session = Depends(get_db)):
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    return ruleset

@router.put("/restaurants/{id}/ruleset", dependencies=[Depends(require_role("admin"))])
def update_ruleset(id: str, data: RulesetUpdate, db: Session = Depends(get_db)):
    ruleset = db.query(Ruleset).filter_by(restaurant_id=id).first()
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    ruleset.rules_json = data.rules_json
    db.commit()
    db.refresh(ruleset)
    return ruleset

@router.post("/restaurants/{id}/ruleset/train", dependencies=[Depends(require_role("admin"))])
def train_ruleset(id: str, db: Session = Depends(get_db)):
    # Training logic to be implemented
    return {"detail": "Not implemented"}
