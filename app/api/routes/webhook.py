from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from app.schemas.webhook import WhatsAppWebhookPayload
from app.core.security import verify_meta_signature
from app.api.dependencies import get_current_tenant
from app.models.organization import Organization
from app.core.config import settings

# Create the router. 
# The dependency ensures NO request gets past this point without a valid Meta signature.
router = APIRouter(
    prefix="/webhook",
    tags=["WhatsApp Meta Webhook"],
    # dependencies=[Depends(verify_meta_signature)]
)

from app.services.chat_service import process_whatsapp_message 

@router.post("/whatsapp", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_meta_signature)])
async def handle_whatsapp_webhook(
    request: Request,
    payload: WhatsAppWebhookPayload,
    background_tasks: BackgroundTasks,
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Receives incoming WhatsApp messages from Meta.
    """
    # 1. Immediately acknowledge receipt to Meta to prevent timeout retries
    response = {"status": "received"}

    # 2. Safety check: Verify this is an actual message and not just a status update
    try:
        messages = payload.entry[0].changes[0].value.messages
        if not messages:
            return response
    except (IndexError, AttributeError):
        return response

    # 3. Offload the heavy AI thinking to the background so we don't block the response
    background_tasks.add_task(process_whatsapp_message, payload, tenant)

    return response

@router.get("/whatsapp")
async def verify_webhook(
    request: Request
):
    """
    Meta uses this GET endpoint once during initial setup to verify ownership of the webhook URL.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Check if the token matches our environment variable
    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        print("✅ Webhook verified successfully by Meta!")
        # Meta REQUIRES the challenge to be returned as a plain integer/string, NOT JSON.
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=challenge)
    
    return {"status": "error", "message": "Verification failed"}