import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Enum, Float, Text, JSON, UniqueConstraint, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

# Enum definitions
class WineListFileStatus(enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    parsed = "parsed"
    refined = "refined"
    finalized = "finalized"

class WineEntryStatus(enum.Enum):
    auto = "auto"
    user_edited = "user_edited"
    confirmed = "confirmed"
    rejected = "rejected"

class UserRole(enum.Enum):
    admin = "admin"
    restaurant_admin = "restaurant_admin"
    staff = "staff"

# Restaurant table
class Restaurant(Base):
    __tablename__ = "restaurant"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    contact_email = Column(String)
    notes = Column(Text)

    ruleset = relationship("Ruleset", back_populates="restaurant", uselist=False)
    wine_list_files = relationship("WineListFile", back_populates="restaurant")
    users = relationship("User", back_populates="restaurant")

# WineListFile table
class WineListFile(Base):
    __tablename__ = "wine_list_file"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    parsed_date = Column(DateTime)
    status = Column(Enum(WineListFileStatus), default=WineListFileStatus.uploaded)
    notes = Column(Text)

    restaurant = relationship("Restaurant", back_populates="wine_list_files")
    wine_entries = relationship("WineEntry", back_populates="wine_list_file")

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

    wine_list_file = relationship("WineListFile", back_populates="wine_entries")

# Ruleset table
class Ruleset(Base):
    __tablename__ = "ruleset"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurant.id"), nullable=False, unique=True)
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
    password_hash = Column(String, nullable=False)
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
