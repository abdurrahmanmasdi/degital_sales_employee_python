import httpx
from app.core.config import settings

async def send_whatsapp_text(to_phone: str, phone_number_id: str, text: str):
    """
    Sends an outbound text message via the Meta Graph API.
    """
    # Meta uses the phone_number_id in the URL to know which clinic is sending the message
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text}
    }
    
    # We use httpx to make an async HTTP POST request to Meta
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status() # This will throw an error if Meta rejects it
            print(f"📤 Successfully sent message to {to_phone}")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"🔴 Failed to send message: {e.response.text}")
            return None