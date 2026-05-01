import logging
from google import genai
from google.genai import types
from app.ai.tools import search_clinic_knowledge, sync_lead_profile
from app.core.config import settings

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

class ClinicSalesAgent:
    def __init__(self, organization_id: str, system_prompt: str, patient_phone: str, lead_id: str | None):
        self.organization_id = organization_id
        self.system_prompt = system_prompt
        self.patient_phone = patient_phone
        self.lead_id = lead_id

        # 1. Define the Tool Schema explicitly (No automatic black boxes!)
        self.knowledge_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="retrieve_clinic_info",
                    description="Searches the clinic's PDF database for prices, procedures, or rules.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "search_query": types.Schema(
                                type="STRING",
                                description="The search terms. e.g. 'Zirkonyum Kron fiyat' or 'Amalgam Dolgu'"
                            )
                        },
                        required=["search_query"]
                    )
                )
            ]
        )
        
        self.sync_lead_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="sync_lead_profile",
                    description="Creates or updates the lead's profile in the CRM. Use this immediately when you learn their name, OR later in the chat if you deduce their priority level has increased or they request a specific currency.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "first_name": types.Schema(type="STRING", description="Patient's first name."),
                            "last_name": types.Schema(type="STRING", description="Patient's last name."),
                            "preferred_language": types.Schema(type="STRING", description="The 2-letter language code (e.g., 'en', 'tr', 'ar', 'de')."),
                            "currency": types.Schema(type="STRING", description="Currency deduced from chat.", enum=["USD", "EUR", "TRY", "GBP"]),
                            "priority": types.Schema(type="STRING", description="Lead intent priority.", enum=["HOT", "WARM", "COLD"])
                        },
                        required=["first_name", "last_name", "preferred_language", "currency", "priority"]
                    )
                )
            ]
        )



    async def generate_response(self, user_message: str, chat_history_str: str) -> str:
        """
        The main Agent execution loop. 
        It provides the history, the new message, and the tools to Gemini.
        """
        logger.info(f"🤖 Agent thinking for org {self.organization_id}...")

        # Inject chat history into the system prompt context so the AI remembers the conversation
        full_context = f"{self.system_prompt}\n\nRecent Conversation History:\n{chat_history_str}"
        # return f"full_context: {full_context}" # DEBUGGING: Check the full context being sent to Gemini
        config = types.GenerateContentConfig(
            system_instruction=full_context,
            temperature=0.2, # Keep it low so it focuses on facts
            tools=[self.knowledge_tool],
            # automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
        )
        # return "this is a placeholder response while we set up the agent..." # DEBUGGING: Temporary return to avoid errors while setting up the agent
        try:
            chat = client.aio.chats.create(
                model="gemini-2.5-flash",
                config=config
            )
            
            # 1. Send the user's message to the AI
            # response = await chat.send_message(user_message)
            response = await chat.send_message(user_message)
            
            # 2. Did the AI decide it needs to search the database?
            if response.function_calls:
                for function_call in response.function_calls:
                    # Tool 1: Knowledge Search
                    if function_call.name == "retrieve_clinic_info":
                        query = function_call.args.get("search_query", "")
                        logger.info(f"🛠️ AI requested tool: retrieve_clinic_info with query: '{query}'")
                        
                        # 3. WE execute the async database search safely!
                        tool_result = await search_clinic_knowledge(self.organization_id, query)
                        
                        # 4. Send the found PDF text back to the AI so it can answer the user
                        logger.info("🧠 Sending database results back to AI...")
                        response = await chat.send_message(
                            types.Part.from_function_response(
                                name="retrieve_clinic_info",
                                response={"result": tool_result}
                            )
                        )
                    
                    # Tool 2: Lead Creation
                    elif function_call.name == "sync_lead_profile":
                        tool_result = await sync_lead_profile(
                            organization_id=self.organization_id, 
                            patient_phone=self.patient_phone,
                            lead_id=self.lead_id, # We pass the state to the DB!
                            first_name=function_call.args.get("first_name", "Unknown"), 
                            last_name=function_call.args.get("last_name", "Unknown"),
                            preferred_language=function_call.args.get("preferred_language", "en"),
                            currency=function_call.args.get("currency", "USD"),
                            priority=function_call.args.get("priority", "WARM")
                        )
                        
                        response = await chat.send_message(
                            types.Part.from_function_response(
                                name="sync_lead_profile",
                                response={"result": tool_result}
                            )
                        )


            
            # 5. Return the final, intelligent response
            return response.text
            
        except Exception as e:
            logger.error(f"Agent failed to generate response: {e}")
            return "I apologize, but I am experiencing a technical issue. Please give me a moment."