"""
SQLAlchemy ORM models for the AI Sales Agent.

These models map to existing Prisma-managed tables.
The database schema is managed by Prisma migrations;
Python uses these models for read/write operations only.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class HandledByEnum(str, Enum):
    """Enum for who handled a conversation."""
    AI = "AI"
    HUMAN = "HUMAN"


class MessageTypeEnum(str, Enum):
    """Enum for message types."""
    USER_TEXT = "USER_TEXT"
    AI_TEXT = "AI_TEXT"
    SYSTEM_PROMPT = "SYSTEM_PROMPT"


class Organization(Base):
    """
    Represents an organization using the AI Sales Agent.
    
    Attributes:
        id: Unique identifier (UUID primary key).
        name: Organization name.
        ai_personas: Relationship to associated AI personas.
        conversations: Relationship to conversations within this organization.
    """
    __tablename__ = "organizations"
    
    id = Column(Uuid, primary_key=True, default=UUID)
    name = Column(String(255), nullable=False, index=True)
    
    # Relationships
    ai_personas = relationship(
        "OrganizationAiPersona",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationAiPersona(Base):
    """
    Represents an AI persona configuration for an organization.
    
    Attributes:
        id: Unique identifier (UUID primary key).
        organization_id: Foreign key to organizations table.
        system_prompt: The system prompt that defines AI behavior.
        organization: Relationship to parent Organization.
    """
    __tablename__ = "organization_ai_personas"
    
    id = Column(Uuid, primary_key=True, default=UUID)
    organization_id = Column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    system_prompt = Column(Text, nullable=False)
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="ai_personas",
    )
    
    def __repr__(self) -> str:
        return f"<OrganizationAiPersona(id={self.id}, organization_id={self.organization_id})>"


class Conversation(Base):
    """
    Represents a conversation thread within an organization.
    
    Attributes:
        id: Unique identifier (UUID primary key).
        organization_id: Foreign key to organizations table.
        handled_by: Enum indicating handler (AI or HUMAN).
        organization: Relationship to parent Organization.
        messages: Relationship to messages in this conversation.
    """
    __tablename__ = "conversations"
    
    id = Column(Uuid, primary_key=True, default=UUID)
    organization_id = Column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handled_by = Column(
        SQLEnum(HandledByEnum),
        nullable=False,
        default=HandledByEnum.AI,
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="conversations",
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, handled_by={self.handled_by})>"


class Message(Base):
    """
    Represents a message within a conversation.
    
    Attributes:
        id: Unique identifier (UUID primary key).
        conversation_id: Foreign key to conversations table.
        sender_id: UUID of the message sender (nullable for system messages).
        type: Enum indicating message type (USER_TEXT, AI_TEXT, SYSTEM_PROMPT).
        content: The message content.
        created_at: Timestamp of message creation (UTC).
        conversation: Relationship to parent Conversation.
    """
    __tablename__ = "messages"
    
    id = Column(Uuid, primary_key=True, default=UUID)
    conversation_id = Column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = Column(Uuid, nullable=True, index=True)
    type = Column(
        SQLEnum(MessageTypeEnum),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
    )
    
    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
    
    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, type={self.type}, "
            f"created_at={self.created_at})>"
        )
