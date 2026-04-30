import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization, OrganizationAiPersona
from app.models.chat import Conversation, Message, MessageType, ActiveHandler
from app.schemas.webhook import WhatsAppWebhookPayload
from app.db.session import AsyncSessionLocal
from app.services.whatsapp_client import send_whatsapp_text
from app.db.redis import redis_client

# Import our scalable Agent Class
from app.ai.agent import ClinicSalesAgent

logger = logging.getLogger(__name__)

def format_message_for_redis(msg: Message, sender_type: str):
    return {
        "id": str(msg.id),
        "content": msg.content,
        "sender": sender_type,
        "createdAt": msg.created_at.isoformat()
    }

async def process_whatsapp_message(payload: WhatsAppWebhookPayload, tenant: Organization):
    """
    The orchestrator task. It routes data between Meta, the Database, and the AI Agent.
    """
    try:
        phone_number_id = payload.entry[0].changes[0].value.metadata.phone_number_id
        msg_data = payload.entry[0].changes[0].value.messages[0]
        patient_phone = msg_data.from_number
        lead_text = msg_data.text.body if msg_data.text else ""
    except (IndexError, AttributeError):
        logger.debug("Received payload that is not a text message. Ignoring.")
        return

    if not lead_text:
        return

    async with AsyncSessionLocal() as db:
        
        # 1. Find or Create the Conversation
        conv_query = select(Conversation).where(
            Conversation.organization_id == tenant.id,
            Conversation.external_contact_id == patient_phone
        )
        result = await db.execute(conv_query)
        conversation = result.scalar_one_or_none()

        # If it doesn't exist, create it with the correct schema columns
        if not conversation:
            logger.info(f"Creating new conversation for external contact: {patient_phone}")
            conversation = Conversation(
                organization_id=tenant.id,
                name=patient_phone,                 # Can be updated later to their actual name by NestJS
                external_contact_id=patient_phone,  # CRITICAL: Links to the Meta WhatsApp ID
                handled_by=ActiveHandler.AI
            )
            db.add(conversation)
            await db.flush()

        # --- HUMAN TAKEOVER CHECK ---
        if conversation.handled_by == ActiveHandler.HUMAN:  # Updated Enum
            logger.info(f"Conversation {conversation.id} is handled by HUMAN. AI sleeping.")
            # We still save the lead's message and publish to Redis so the Human sees it!
            lead_message = Message(
                conversation_id=conversation.id, type=MessageType.LEAD_TEXT, content=lead_text # Updated Enum
            )
            db.add(lead_message)
            await db.commit()

            await redis_client.publish_chat_event(
                organization_id=tenant.id, conversation_id=conversation.id, message=format_message_for_redis(lead_message, "USER")
            )
            return # Exit early before AI generation

        # 2. Save the Lead's Message
        lead_message = Message(
            conversation_id=conversation.id,
            type=MessageType.LEAD_TEXT, # Updated Enum
            content=lead_text
        )
        db.add(lead_message)
        await db.commit()

        await redis_client.publish_chat_event(
            organization_id=tenant.id,
            conversation_id=conversation.id,
            message=format_message_for_redis(lead_message, "USER")
        )

        # 3. Fetch the AI Persona for this Tenant
        persona_query = select(OrganizationAiPersona).where(
            OrganizationAiPersona.organization_id == tenant.id
        ).limit(1)
        persona_result = await db.execute(persona_query)
        persona = persona_result.scalar_one_or_none()
        
        system_prompt = persona.system_prompt if persona else "You are a helpful assistant."

        # 4. Fetch the Conversation History (Memory)
        history_query = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(15) # Grab last 15 messages for good context
        
        history_result = await db.execute(history_query)
        recent_messages = list(history_result.scalars().all())
        recent_messages.reverse() # Reverse to chronological order
        
        chat_history_str = "\n".join([
            f"{'Patient' if m.type in [MessageType.LEAD_TEXT, MessageType.LEAD_AUDIO] else 'AI/Clinic'}: {m.content}"
            for m in recent_messages
        ])

        # ==========================================
        #   THE SCALABLE AGENT
        # ==========================================
        logger.info(f"Generating AI reply for {patient_phone} using Agent...")
        
        agent = ClinicSalesAgent(
            organization_id=str(tenant.id),
            system_prompt=system_prompt
        )

        ai_reply_text = await agent.generate_response(
            user_message=lead_text,
            chat_history_str=chat_history_str
        )

        # ==========================================
        #   SAVE & SEND
        # ==========================================
        ai_message = Message(
            conversation_id=conversation.id,
            type=MessageType.AI_TEXT, # Updated Enum
            content=ai_reply_text
        )
        db.add(ai_message)
        await db.commit()
        
        await redis_client.publish_chat_event(
            organization_id=tenant.id,
            conversation_id=conversation.id,
            message=format_message_for_redis(ai_message, "AI")
        )
        
        logger.info(f"  Successfully processed AI reply for {patient_phone}")

        await send_whatsapp_text(
            to_phone=patient_phone,
            phone_number_id=phone_number_id,
            text=ai_reply_text
        )