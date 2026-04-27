"""
AI engine service for generating sales replies using Google Generative AI.

Uses the google-genai package (Gemini 2.5 Flash model) to generate
contextual, system-prompt-guided responses for the sales agent.
"""

import logging
from typing import Optional

import google.genai as genai
from google.genai import types

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the Generative AI client with the API key from configuration
genai.configure(api_key=settings.google_api_key)


async def generate_sales_reply(
    user_message: str,
    system_prompt: str,
) -> str:
    """
    Generate an AI sales reply using Gemini 2.5 Flash.
    
    Sends the user's message to the generative AI model with the provided
    system prompt to guide the AI's behavior and response style.
    
    Args:
        user_message: The user's input message requiring a sales reply.
        system_prompt: The system prompt defining AI behavior and context
                      (e.g., sales technique, tone, constraints).
    
    Returns:
        The generated sales reply as a string.
    
    Raises:
        ValueError: If user_message or system_prompt is empty.
        google.genai.APIError: If the API request fails.
        Exception: For unexpected errors during generation.
    
    Example:
        >>> system_prompt = "You are a friendly B2B SaaS sales representative..."
        >>> user_msg = "How much does your product cost?"
        >>> reply = await generate_sales_reply(user_msg, system_prompt)
        >>> print(reply)
    """
    
    # Validate inputs
    if not user_message or not user_message.strip():
        raise ValueError("user_message cannot be empty.")
    
    if not system_prompt or not system_prompt.strip():
        raise ValueError("system_prompt cannot be empty.")
    
    try:
        logger.debug(
            "Calling Gemini 2.5 Flash with user message length: %d",
            len(user_message),
        )
        
        # Create the request with system instruction
        response = genai.Client().models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        
        # Extract generated text from response
        if response and response.text:
            logger.debug(
                "Successfully generated reply (length: %d)",
                len(response.text),
            )
            return response.text.strip()
        
        logger.warning("Empty response received from Gemini API")
        return ""
    
    except ValueError as e:
        logger.error("Validation error in generate_sales_reply: %s", str(e))
        raise
    
    except Exception as e:
        logger.error(
            "Error calling Gemini API: %s (type: %s)",
            str(e),
            type(e).__name__,
        )
        raise


async def generate_sales_reply_with_context(
    user_message: str,
    system_prompt: str,
    conversation_history: Optional[list[dict]] = None,
) -> str:
    """
    Generate an AI sales reply with optional conversation history context.
    
    For multi-turn conversations, pass the conversation history to provide
    context for more coherent, contextually-aware responses.
    
    Args:
        user_message: The current user message.
        system_prompt: The system prompt for AI behavior.
        conversation_history: Optional list of previous messages in format:
                             [{"role": "user", "content": "..."}, ...]
    
    Returns:
        The generated sales reply.
    
    Raises:
        ValueError: If inputs are invalid.
        Exception: If the API request fails.
    
    Example:
        >>> history = [
        ...     {"role": "user", "content": "What's your pricing?"},
        ...     {"role": "assistant", "content": "We offer flexible plans..."}
        ... ]
        >>> reply = await generate_sales_reply_with_context(
        ...     "Can you provide more details?",
        ...     system_prompt,
        ...     history
        ... )
    """
    
    if not user_message or not user_message.strip():
        raise ValueError("user_message cannot be empty.")
    
    if not system_prompt or not system_prompt.strip():
        raise ValueError("system_prompt cannot be empty.")
    
    try:
        logger.debug(
            "Calling Gemini 2.5 Flash with history context "
            "(history length: %d)",
            len(conversation_history) if conversation_history else 0,
        )
        
        # Build contents: history + current message
        contents = []
        
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                contents.append({"role": role, "parts": [{"text": content}]})
        
        # Add current user message
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}],
        })
        
        response = genai.Client().models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        
        if response and response.text:
            logger.debug(
                "Successfully generated contextual reply (length: %d)",
                len(response.text),
            )
            return response.text.strip()
        
        logger.warning("Empty response received from Gemini API")
        return ""
    
    except ValueError as e:
        logger.error("Validation error in generate_sales_reply_with_context: %s", str(e))
        raise
    
    except Exception as e:
        logger.error(
            "Error calling Gemini API with history: %s (type: %s)",
            str(e),
            type(e).__name__,
        )
        raise
