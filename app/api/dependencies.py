from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.webhook import WhatsAppWebhookPayload
from app.core.exceptions import TenantNotFoundError

# 1. Re-export the database dependency for easy importing
db_dependency = Depends(get_db)

# 2. The Multi-Tenant Extractor
async def get_current_tenant(
    payload: WhatsAppWebhookPayload, 
    db: AsyncSession = db_dependency
) -> Organization:
    """
    Intercepts the incoming Meta payload, finds the target phone number,
    and returns the corresponding Organization (Tenant).
    """
    try:
        # Navigate the nested Meta JSON to find the clinic's phone ID
        phone_number_id = payload.entry[0].changes[0].value.metadata.phone_number_id
    except (IndexError, AttributeError):
        # If the payload is a status update (read receipt, etc.) and not a message,
        # it might not have these fields. We can handle that gracefully later.
        raise TenantNotFoundError(phone_number="UNKNOWN_PAYLOAD_STRUCTURE")

    # TODO: In your Prisma schema, you will need to ensure the Organization table 
    # has a column linking it to the Meta 'phone_number_id'. 
    # For now, we simulate the lookup:
    
    # query = select(Organization).where(Organization.meta_phone_id == phone_number_id)
    # result = await db.execute(query)
    # tenant = result.scalar_one_or_none()
    
    # if not tenant:
    #     raise TenantNotFoundError(phone_number=phone_number_id)
    
    # return tenant

    # TEMPORARY MOCK: Just return the first organization in the database so we can test
    query = select(Organization).limit(1)
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()
    tenant.id = "a72d844f-4d8d-45fa-ba10-9a15c8cef002"  # <-- MOCK ID for testing purposes only. In production, this would come from the DB.
    
    if not tenant:
        raise TenantNotFoundError(phone_number="NO_ORGS_IN_DATABASE")
        
    return tenant