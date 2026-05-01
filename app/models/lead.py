import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Uuid, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    QUALIFYING = "QUALIFYING"
    READY_TO_PAY = "READY_TO_PAY"
    HANDED_OFF = "HANDED_OFF"
    WON = "WON"
    LOST = "LOST"
    UNQUALIFIED = "UNQUALIFIED"

class Priority(str, enum.Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"

class Currency(str, enum.Enum):
    USD = "USD"
    TRY = "TRY"
    EUR = "EUR"
    GBP = "GBP"

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    pipeline_stage_id = Column(Uuid, nullable=True, index=True)
    assigned_agent_id = Column(Uuid, nullable=True, index=True) 
    source_id = Column(Uuid, nullable=True, index=True)
    
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    native_name = Column(String, nullable=True)
    
    gender = Column(SQLEnum(Gender, name="Gender", create_type=False), nullable=False, default=Gender.UNKNOWN)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    country = Column(String, nullable=False)
    timezone = Column(String, nullable=False)
    primary_language = Column(String, nullable=False)
    preferred_language = Column(String, nullable=True)
    
    social_links = Column(JSONB, nullable=True)
    status = Column(SQLEnum(LeadStatus, name="LeadStatus", create_type=False), nullable=False, default=LeadStatus.NEW)
    priority = Column(SQLEnum(Priority, name="Priority", create_type=False), nullable=False, default=Priority.WARM)
    estimated_value = Column(Numeric(65, 30), nullable=True)
    currency = Column(SQLEnum(Currency, name="Currency", create_type=False), nullable=False, default=Currency.USD)
    
    expected_service_date = Column(DateTime(timezone=True), nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)