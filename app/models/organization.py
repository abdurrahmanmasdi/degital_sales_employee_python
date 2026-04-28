import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    
    # Relationships
    ai_personas = relationship("OrganizationAiPersona", back_populates="organization", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="organization", cascade="all, delete-orphan")


class OrganizationAiPersona(Base):
    __tablename__ = "organization_ai_personas"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    system_prompt = Column(Text, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="ai_personas")