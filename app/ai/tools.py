# app/ai/tools.py
import logging
from google import genai
from google.genai import types
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

async def get_gemini_embedding(text_chunk: str) -> list[float]:
    """Converts a string of text into a 768-dimensional vector using Gemini."""
    try:
        response = await client.aio.models.embed_content(
            model='gemini-embedding-001',
            contents=text_chunk,
            # This config tells Google to compress the 3072 vector down to 768
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return []

async def search_clinic_knowledge(organization_id: str, search_query: str, limit: int = 3) -> str:
    """
    Executes the vector similarity search in PostgreSQL.
    """
    logger.info(f"🔍 AI is using the Knowledge Search tool for: '{search_query}'")
    
    question_vector = await get_gemini_embedding(search_query)
    if not question_vector:
        return "Internal Error: Could not search knowledge base."

    async with AsyncSessionLocal() as db:
        query = text("""
            SELECT content 
            FROM organization_knowledge 
            WHERE organization_id = :org_id 
            ORDER BY embedding <=> CAST(:q_vector AS vector) 
            LIMIT :limit
        """)
        
        result = await db.execute(query, {
            "org_id": str(organization_id),
            # We convert the Python list to a string format PostgreSQL understands: "[0.1, 0.2, ...]"
            "q_vector": str(question_vector),
            "limit": limit
        })
        
        found_chunks = result.scalars().all()
        
        if not found_chunks:
            return "No relevant information found in the clinic's knowledge base."
            
        return "\n---\n".join(found_chunks)