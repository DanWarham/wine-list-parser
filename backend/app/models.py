import uuid
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("[models] Starting models module initialization...")
    
    from sqlalchemy import (
        Column, String, DateTime, ForeignKey, Boolean, Enum, Float, Text, JSON, UniqueConstraint, DECIMAL
    )
    logger.info("[models] SQLAlchemy core imports successful")
    
    from sqlalchemy.dialects.postgresql import UUID
    logger.info("[models] PostgreSQL dialect imports successful")
    
    from sqlalchemy.orm import declarative_base, relationship
    logger.info("[models] SQLAlchemy ORM imports successful")
    
    import enum
    from typing import Optional
    from pydantic import BaseModel
    logger.info("[models] Standard library imports successful")

    logger.info("[models] All imports completed successfully")
    
    Base = declarative_base()
    logger.info("[models] SQLAlchemy Base created")

    # Enum definitions
    class WineListFileStatus(str, enum.Enum):
        pending = "pending"
        processing = "processing"
        parsed = "parsed"
        error = "error"
        learning = "learning"
        learned = "learned"

    class WineEntryStatus(enum.Enum):
        auto = "auto"
        user_edited = "user_edited"
        confirmed = "confirmed"
        rejected = "rejected"

    class UserRole(enum.Enum):
        admin = "admin"
        restaurant_admin = "restaurant_admin"
        staff = "staff"

    logger.info("[models] Enum definitions created")

    # Restaurant table
    class Restaurant(Base):
        __tablename__ = "restaurant"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name = Column(String, unique=True, nullable=False)
        date_created = Column(DateTime, default=datetime.utcnow)
        wine_list_url = Column(String, nullable=True)

        ruleset = relationship("Ruleset", back_populates="restaurant", uselist=False, cascade="all, delete-orphan")
        wine_list_files = relationship("WineListFile", back_populates="restaurant", cascade="all, delete-orphan")
        users = relationship("User", back_populates="restaurant", cascade="all, delete-orphan")

    # WineListFile table
    class WineListFile(Base):
        __tablename__ = "wine_list_file"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id"), nullable=False)
        filename = Column(String, nullable=False)
        file_url = Column(String, nullable=False)
        uploaded_at = Column(DateTime, default=datetime.utcnow)
        parsed_date = Column(DateTime, default=datetime.utcnow)
        status = Column(Enum(WineListFileStatus), default=WineListFileStatus.pending)
        notes = Column(Text)
        file_metadata = Column(JSON)
        learning_results = Column(JSON)  # Store learning results
        learning_date = Column(DateTime)  # When learning was last performed
        rules_version = Column(String)    # Version of rules used
        steps_status = Column(JSON, nullable=True)  # Track processing step status

        restaurant = relationship("Restaurant", back_populates="wine_list_files")
        wine_entries = relationship("WineEntry", back_populates="wine_list_file", cascade="all, delete-orphan")

    # WineEntry table
    class WineEntry(Base):
        __tablename__ = "wine_entry"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        wine_list_file_id = Column(UUID(as_uuid=True), ForeignKey("wine_list_file.id"), nullable=False)
        restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id"), nullable=False)
        producer = Column(String)
        cuvee = Column(String)
        type = Column(String)
        vintage = Column(String)
        price = Column(String)  # Store as string for original format
        bottle_size = Column(String)
        grape_variety = Column(String)
        country = Column(String)
        region = Column(String)
        subregion = Column(String)
        row_confidence = Column(Float)
        field_confidence = Column(JSON)
        section_header = Column(String)
        subheader = Column(String)
        raw_text = Column(Text)
        status = Column(Enum(WineEntryStatus), default=WineEntryStatus.auto)
        last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        designation = Column(String, nullable=True)  # e.g. Grand Cru, Premier Cru
        classification = Column(String, nullable=True)  # e.g. AOC, DOCG
        sub_type = Column(String, nullable=True)  # e.g. Brut, Sec, Demi-Sec
        extra_data = Column(JSON, nullable=True)

        wine_list_file = relationship("WineListFile", back_populates="wine_entries")

    # Ruleset table
    class Ruleset(Base):
        __tablename__ = "ruleset"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False, unique=True)
        rules_json = Column(JSON, nullable=False)
        date_created = Column(DateTime, default=datetime.utcnow)
        last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        active = Column(Boolean, default=True)

        restaurant = relationship("Restaurant", back_populates="ruleset")

    # User table
    class User(Base):
        __tablename__ = "user"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        email = Column(String, unique=True, nullable=False)
        supabase_user_id = Column(String, unique=True, nullable=False)  # New field for Supabase user id
        name = Column(String)
        role = Column(Enum(UserRole), default=UserRole.staff)
        restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id"), nullable=True)
        date_joined = Column(DateTime, default=datetime.utcnow)

        restaurant = relationship("Restaurant", back_populates="users")

    # AuditLog table (optional but recommended)
    class AuditLog(Base):
        __tablename__ = "audit_log"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
        wine_entry_id = Column(UUID(as_uuid=True), ForeignKey("wine_entry.id"), nullable=True)
        wine_list_file_id = Column(UUID(as_uuid=True), ForeignKey("wine_list_file.id"), nullable=True)
        action = Column(String, nullable=False)
        old_value = Column(JSON)
        new_value = Column(JSON)
        timestamp = Column(DateTime, default=datetime.utcnow)

        # Relationships (not strictly needed for all, but can be added as needed)
        # user = relationship("User")
        # wine_entry = relationship("WineEntry")
        # wine_list_file = relationship("WineListFile")

    class UserCreate(BaseModel):
        email: str
        supabase_user_id: str
        name: Optional[str] = None
        role: Optional[str] = "staff"
        restaurant_id: Optional[uuid.UUID] = None

    logger.info("[models] All model classes defined successfully")
    logger.info("[models] Models module initialization completed successfully")

except ImportError as e:
    logger.error(f"[models] Import error: {e}")
    logger.error(f"[models] Traceback: {traceback.format_exc()}")
    raise
except Exception as e:
    logger.error(f"[models] Model definition error: {type(e).__name__}: {e}")
    logger.error(f"[models] Traceback: {traceback.format_exc()}")
    raise
