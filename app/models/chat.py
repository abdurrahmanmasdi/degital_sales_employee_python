import uuid
import enum
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Uuid, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.db.base import Base

class HandledByEnum(str, enum.Enum):
    AI = "AI"
    HUMAN = "HUMAN"

class MessageTypeEnum(str, enum.Enum):
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
    
    # CRITICAL: native_enum=False for Prisma compatibility
    handled_by = Column(SQLEnum(HandledByEnum, native_enum=False), nullable=False, default=HandledByEnum.AI)
    
    # Auto-managed timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Uuid, nullable=True, index=True)
    type = Column(SQLEnum(MessageTypeEnum, native_enum=False), nullable=False)
    content = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)
    message_metadata = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")