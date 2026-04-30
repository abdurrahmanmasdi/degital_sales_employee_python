import uuid
import enum
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class ActiveHandler(str, enum.Enum):
    AI = "AI"
    HUMAN = "HUMAN"

class MessageType(str, enum.Enum):
    LEAD_TEXT = "LEAD_TEXT"
    LEAD_AUDIO = "LEAD_AUDIO"
    USER_TEXT = "USER_TEXT"
    USER_AUDIO = "USER_AUDIO"
    AI_TEXT = "AI_TEXT"
    AI_AUDIO = "AI_AUDIO"
    SYSTEM_PROMPT = "SYSTEM_PROMPT"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    is_group = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    
    # CRITICAL: Mapped to Prisma's native Postgres enum
    handled_by = Column(SQLEnum(ActiveHandler, name="ActiveHandler", create_type=False), nullable=False, default=ActiveHandler.AI)
    
    lead_id = Column(Uuid, nullable=True, unique=True, index=True)
    assigned_agent_id = Column(Uuid, nullable=True, index=True)
    external_contact_id = Column(String, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    organization = relationship("Organization", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Uuid, nullable=True, index=True)
    
    # CRITICAL: Mapped to Prisma's native Postgres enum
    type = Column(SQLEnum(MessageType, name="MessageType", create_type=False), nullable=False)
    
    content = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)
    
    message_metadata = Column("metadata", JSONB, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    conversation = relationship("Conversation", back_populates="messages")