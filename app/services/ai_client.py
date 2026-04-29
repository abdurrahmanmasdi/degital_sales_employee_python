import json
from google import genai
from google.genai import types
from app.core.config import settings

# Initialize the client with our secure settings
client = genai.Client(api_key=settings.GOOGLE_API_KEY)


# ============================================================================
# TOOL: Procedure Pricing Lookup
# ============================================================================

PROCEDURE_PRICING = {
    "dental implant": "$1,500",
    "teeth whitening": "$200",
    "root canal": "$800",
    "crown": "$1,200",
    "bridge": "$1,800",
    "extraction": "$300",
    "cleaning": "$150",
    "filling": "$200",
    "veneer": "$1,000",
    "orthodontics": "$5,000",
}


def get_procedure_pricing(procedure_name: str) -> str:
    """
    Lookup pricing information for a dental procedure.
    
    Args:
        procedure_name: The name of the dental procedure.
    
    Returns:
        A formatted string with the price or a not-found message.
    """
    # Normalize the procedure name (lowercase, strip whitespace)
    normalized = procedure_name.lower().strip()
    
    if normalized in PROCEDURE_PRICING:
        price = PROCEDURE_PRICING[normalized]
        return f"The cost of {procedure_name} is {price}."
    
    # Check for partial matches
    for proc_key, price in PROCEDURE_PRICING.items():
        if normalized in proc_key or proc_key in normalized:
            return f"The cost of {proc_key} is {price}."
    
    return f"I don't have pricing information for '{procedure_name}' in my system. Please contact us for a custom quote."


async def generate_sales_reply(
    chat_history: str, 
    user_message: str, 
    system_prompt: str
) -> str:
    """
    Sends the conversation history and the new message to Gemini 2.5 Flash.
    
    Supports tool use: Gemini can call get_procedure_pricing to fetch pricing
    information dynamically and incorporate it into its response.
    
    Args:
        chat_history: Conversation history for context.
        user_message: The user's current message.
        system_prompt: System instruction for AI behavior.
    
    Returns:
        The AI's text response.
    """
    # Construct the full prompt context
    full_context = f"{chat_history}\n\nPatient: {user_message}"
    
    # Define the tool schema for Gemini
    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="get_procedure_pricing",
                    description="Lookup the pricing for a dental procedure. Use this when the patient asks about costs.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "procedure_name": types.Schema(
                                type="STRING",
                                description="The name of the dental procedure (e.g., 'dental implant', 'teeth whitening')",
                            )
                        },
                        required=["procedure_name"],
                    ),
                )
            ]
        )
    ]
    
    try:
        # Make the initial request with tools enabled
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_context,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
            )
        )
        
        # Check if Gemini wants to call a tool
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    # Gemini is calling a tool
                    tool_name = part.function_call.name
                    tool_args = part.function_call.args
                    
                    # Execute the requested tool
                    if tool_name == "get_procedure_pricing":
                        procedure_name = tool_args.get("procedure_name", "")
                        tool_result = get_procedure_pricing(procedure_name)
                        
                        # Send the tool result back to Gemini for final response
                        messages = [
                            types.Content(
                                role="user",
                                parts=[types.Part(text=full_context)]
                            ),
                            response.candidates[0].content,
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name="get_procedure_pricing",
                                            response={"result": tool_result}
                                        )
                                    )
                                ]
                            )
                        ]
                        
                        # Get the final response from Gemini
                        final_response = await client.aio.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=messages,
                            config=types.GenerateContentConfig(
                                system_instruction=system_prompt,
                                tools=tools,
                            )
                        )
                        
                        return final_response.text or "I found the pricing information but had trouble formulating a response."
        
        # Return the text if no tool was called or if tool call was successful
        return response.text or "I have trouble responding right now. Please try again."
        
    except Exception as e:
        print(f"🔴 AI Generation Error: {e}")
        return "I apologize, but I am having trouble connecting to my system right now. Could you please hold on?"