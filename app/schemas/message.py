from pydantic import BaseModel
from typing import Optional

class ExtractedMessage(BaseModel):
    """
    A clean, flattened schema representing exactly what we care about 
    from the massive Meta payload.
    """
    tenant_phone_id: str      # The clinic's phone number ID (used to find the Organization)
    patient_phone: str        # The user's phone number
    message_type: str         # "text", "audio", etc.
    text_content: Optional[str] = None