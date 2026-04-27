"""
WhatsApp webhook router for receiving and processing incoming messages.

Handles incoming messages from WhatsApp, generates AI sales replies,
and returns responses via the FastAPI webhook endpoint.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.ai_engine import generate_sales_reply

# Configure logging
logger = logging.getLogger(__name__)

# Create router for webhook endpoints
router = APIRouter(prefix="/api", tags=["webhook"])


class WhatsAppMessageRequest(BaseModel):
    """
    Schema for incoming WhatsApp messages.
    
    Attributes:
        message: The user's message text.
        sender_id: Optional identifier for the message sender.
        conversation_id: Optional conversation thread identifier.
    """
    message: str = Field(
        ...,
        description="The user's message text",
        min_length=1,
        max_length=4096,
    )
    sender_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the message sender",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Identifier for the conversation thread",
    )


class AIReplyResponse(BaseModel):
    """
    Schema for AI-generated reply response.
    
    Attributes:
        reply: The AI-generated sales reply.
        sender_id: The sender ID from the request.
        conversation_id: The conversation ID from the request.
    """
    reply: str = Field(description="The AI-generated response")
    sender_id: Optional[str] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)


@router.post("/whatsapp", response_model=AIReplyResponse, status_code=status.HTTP_200_OK)
async def handle_whatsapp_message(
    request: WhatsAppMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> AIReplyResponse:
    """
    Handle incoming WhatsApp messages and generate AI sales replies.
    
    Receives a user message, generates a contextual AI reply using Gemini,
    and returns the response for delivery back to WhatsApp.
    
    Args:
        request: The incoming WhatsApp message payload.
        db: Async database session (injected by FastAPI dependency).
    
    Returns:
        AIReplyResponse containing the generated AI reply.
    
    Raises:
        HTTPException: If message processing fails.
    
    Example request:
        POST /api/whatsapp
        {
            "message": "What's your product pricing?",
            "sender_id": "user-123",
            "conversation_id": "conv-456"
        }
    
    Example response:
        {
            "reply": "We offer flexible pricing plans starting at...",
            "sender_id": "user-123",
            "conversation_id": "conv-456"
        }
    """
    
    try:
        logger.info(
            "Processing WhatsApp message from sender: %s, conv: %s",
            request.sender_id,
            request.conversation_id,
        )
        
        # Hardcoded system prompt for initial implementation
        system_prompt = "You are a helpful assistant."
        
        # Generate AI reply using the message and system prompt
        ai_reply = await generate_sales_reply(
            user_message=request.message,
            system_prompt=system_prompt,
        )
        
        logger.info(
            "Successfully generated reply for sender: %s (reply length: %d)",
            request.sender_id,
            len(ai_reply),
        )
        
        return AIReplyResponse(
            reply=ai_reply,
            sender_id=request.sender_id,
            conversation_id=request.conversation_id,
        )
    
    except ValueError as e:
        logger.error("Validation error processing message: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message format: {str(e)}",
        )
    
    except Exception as e:
        logger.error(
            "Error processing WhatsApp message: %s (type: %s)",
            str(e),
            type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI reply. Please try again later.",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Health check endpoint for monitoring service availability.
    
    Returns:
        Dictionary with service status.
    """
    return {"status": "healthy", "service": "ai-sales-agent"}
