import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.organization import Organization, OrganizationAiPersona
from app.models.chat import Conversation, Message, MessageTypeEnum, HandledByEnum
from app.schemas.webhook import WhatsAppWebhookPayload
from app.db.session import AsyncSessionLocal
from app.services.ai_client import generate_sales_reply
from app.services.whatsapp_client import send_whatsapp_text

from app.db.redis import redis_client

# Set up a logger for the service
logger = logging.getLogger(__name__)

# --- Helper Function for Formatting ---
def format_message_for_redis(msg: Message, sender_type: str):
    return {
        "id": str(msg.id),
        "content": msg.content,
        "sender": sender_type, # e.g., "USER" or "AI"
        "createdAt": msg.created_at.isoformat()
    }

async def process_whatsapp_message(payload: WhatsAppWebhookPayload, tenant: Organization):
    """
    The main background task that handles the conversational memory and AI response.
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
            Conversation.name == patient_phone
        )
        result = await db.execute(conv_query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            logger.info(f"Creating new conversation for {patient_phone}")
            conversation = Conversation(
                organization_id=tenant.id,
                name=patient_phone,
                handled_by=HandledByEnum.AI
            )
            db.add(conversation)
            await db.flush() 

        # 2. Save the Lead's Message
        lead_message = Message(
            conversation_id=conversation.id,
            type=MessageTypeEnum.LEAD_TEXT,
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
        
        # Determine the system prompt
        if persona and persona.system_prompt:
            system_prompt = persona.system_prompt
        else:
            logger.warning(f"No AI Persona found for tenant {tenant.name}. Using default fallback.")
            system_prompt = "You are a helpful and professional representative for this organization. Please assist the user."

        # 4. Fetch the Conversation History (Memory)
        history_query = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(10)
        history_result = await db.execute(history_query)
        recent_messages = list(history_result.scalars().all())
        
        # Reverse to chronological order
        recent_messages.reverse()
        
        chat_history_str = "\n".join([
            f"{'Patient' if m.type == MessageTypeEnum.LEAD_TEXT else 'AI'}: {m.content}"
            for m in recent_messages
        ])

        # 5. Generate the AI Reply
        logger.info(f"Generating AI reply for {patient_phone} using tenant persona...")
        ai_reply_text = await generate_sales_reply(
            chat_history=chat_history_str,
            user_message=lead_text,
            system_prompt=system_prompt
        )
        

        # 6. Save the AI's Reply
        ai_message = Message(
            conversation_id=conversation.id,
            type=MessageTypeEnum.AI_TEXT,
            content=ai_reply_text
        )
        db.add(ai_message)
        await db.commit()

        await redis_client.publish_chat_event(
            organization_id=tenant.id,
            conversation_id=conversation.id,
            message=format_message_for_redis(ai_message, "AI")
        )
        
        logger.info(f"✅ Successfully processed and saved AI reply for {patient_phone}")

        # 7. SEND IT TO WHATSAPP!
        await send_whatsapp_text(
            to_phone=patient_phone,
            phone_number_id=phone_number_id,
            text=ai_reply_text
        )