from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.webhook import WhatsAppWebhookPayload
from app.core.exceptions import TenantNotFoundError

db_dependency = Depends(get_db)

import logging
logger = logging.getLogger(__name__)

async def get_current_tenant(
    payload: WhatsAppWebhookPayload, 
    db: AsyncSession = db_dependency
) -> Organization:
    """
    Intercepts the incoming Meta payload, finds the target phone number,
    and dynamically routes the request to the correct SaaS Tenant.
    """
    try:
        # Extract the exact clinic's Meta Phone ID from the webhook
        phone_number_id = payload.entry[0].changes[0].value.metadata.phone_number_id
        logger.debug(f"Processing message for phone number ID: {phone_number_id}")
    except (IndexError, AttributeError):
        # Ignore non-message webhooks (like read receipts) gracefully
        raise TenantNotFoundError(phone_number="UNKNOWN_PAYLOAD_STRUCTURE")

    # The actual Multi-Tenant Lookup
    query = select(Organization).where(Organization.whatsapp_phone_number_id == phone_number_id)
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()

    if not tenant:
        # If a number is messaged but not registered in our DB, we drop it.
        raise TenantNotFoundError(phone_number=phone_number_id)

    return tenant