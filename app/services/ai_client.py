from google import genai
from google.genai import types
from app.core.config import settings

# Initialize the client with our secure settings
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

async def generate_sales_reply(
    chat_history: str, 
    user_message: str, 
    system_prompt: str
) -> str:
    """
    Sends the conversation history and the new message to Gemini 2.5 Flash.
    """
    # Construct the full prompt context
    full_context = f"{chat_history}\n\nPatient: {user_message}"
    
    try:
        # Using the async client (.aio) so we don't block the server
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash', # You can swap back to 2.0-flash if traffic is high
            contents=full_context,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        return response.text
    except Exception as e:
        print(f"🔴 AI Generation Error: {e}")
        return "I apologize, but I am having trouble connecting to my system right now. Could you please hold on?"