from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- Nested WhatsApp Payload Structures ---

class WhatsAppText(BaseModel):
    body: str

class WhatsAppMessage(BaseModel):
    from_number: str = Field(alias="from") # 'from' is a Python keyword, so we use an alias
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppText] = None
    # We can add audio/image schemas here later

class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[List[Any]] = None
    messages: Optional[List[WhatsAppMessage]] = None

class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

# --- The Main Webhook Payload ---
class WhatsAppWebhookPayload(BaseModel):
    """
    The strict Pydantic model for incoming Meta WhatsApp webhooks.
    """
    object: str
    entry: List[WhatsAppEntry]