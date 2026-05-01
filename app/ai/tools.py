import uuid
import json
import logging
import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_number
from datetime import datetime, timezone
from google import genai
from google.genai import types
from sqlalchemy import text
from app.models.lead import LeadStatus, Priority, Currency
from app.db.session import AsyncSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# Basic fallback maps for MVP data enrichment
REGION_TO_TZ = {
    "TR": "Europe/Istanbul",
    "GB": "Europe/London",
    "AE": "Asia/Dubai",
    "US": "America/New_York",
    "DE": "Europe/Berlin"
}
REGION_TO_LANG = {"TR": "tr", "GB": "en", "AE": "ar", "US": "en", "DE": "de"}

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
    
async def sync_lead_profile(
    organization_id: str, 
    patient_phone: str,
    lead_id: str | None,  # CRITICAL: We now pass the known state!
    first_name: str, 
    last_name: str, 
    preferred_language: str = "en",
    currency: str = "USD",
    priority: str = "WARM"
) -> str:
    """
    Updates an existing lead or creates a highly enriched new lead with minimal DB latency.
    """
    logger.info(f"  AI syncing lead profile: {first_name} {last_name} | {priority} | {currency}")
    
    async with AsyncSessionLocal() as db:
        if lead_id:
            # --- SCENARIO A: UPDATE EXISTING LEAD (1 Query) ---
            update_query = text("""
                UPDATE leads SET 
                    first_name = :fname, 
                    last_name = :lname, 
                    preferred_language = :pref_lang, 
                    priority = CAST(:priority AS "Priority"), 
                    currency = CAST(:currency AS "Currency"), 
                    updated_at = now()
                WHERE id = CAST(:lead_id AS UUID) AND organization_id = :org_id
            """)
            await db.execute(update_query, {
                "fname": first_name, "lname": last_name, "pref_lang": preferred_language,
                "priority": priority, "currency": currency, 
                "lead_id": lead_id, "org_id": organization_id
            })
            await db.commit()
            return f"Successfully updated existing CRM profile for {first_name}."

        else:
            # --- SCENARIO B: CREATE ENRICHED LEAD ---
            # Parse Phone Data
            country_code = "UNKNOWN"
            try:
                parsed_phone = phonenumbers.parse(patient_phone if patient_phone.startswith('+') else f"+{patient_phone}")
                country_code = region_code_for_number(parsed_phone) or "UNKNOWN"
            except Exception:
                pass

            timezone = REGION_TO_TZ.get(country_code, "UTC")
            primary_language = REGION_TO_LANG.get(country_code, "en")
            social_links = json.dumps({"whatsapp": f"https://wa.me/{patient_phone.replace('+', '')}"})

            # 1. Fetch all defaults in ONE trip using subqueries
            defaults_query = text("""
                SELECT 
                    (SELECT om.user_id FROM organization_memberships om JOIN roles r ON om.role_id = r.id WHERE om.organization_id = :org_id AND r.slug = 'owner' AND om.status = 'ACTIVE' LIMIT 1) as owner_id,
                    (SELECT id FROM pipeline_stages WHERE organization_id = :org_id ORDER BY order_index ASC LIMIT 1) as stage_id,
                    (SELECT id FROM lead_sources WHERE organization_id = :org_id AND is_active = true ORDER BY CASE WHEN name ILIKE '%whatsapp%' THEN 0 ELSE 1 END LIMIT 1) as source_id
            """)
            defaults = (await db.execute(defaults_query, {"org_id": organization_id})).mappings().first()

            # 2. Insert Lead
            insert_query = text("""
                INSERT INTO leads (
                    id, organization_id, pipeline_stage_id, assigned_agent_id, source_id, 
                    first_name, last_name, gender, phone_number, country, timezone, 
                    primary_language, preferred_language, social_links, status, priority, currency, 
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :org_id, :stage_id, :agent_id, :source_id,
                    :fname, :lname, 'UNKNOWN', :phone, :country, :tz, 
                    :p_lang, :pref_lang, CAST(:social AS jsonb), 'NEW', CAST(:priority AS "Priority"), CAST(:currency AS "Currency"), 
                    now(), now()
                ) RETURNING id
            """)
            
            new_lead_id = (await db.execute(insert_query, {
                "org_id": organization_id, "stage_id": defaults["stage_id"], "agent_id": defaults["owner_id"], "source_id": defaults["source_id"],
                "fname": first_name, "lname": last_name, "phone": patient_phone, 
                "country": country_code, "tz": timezone, "p_lang": primary_language, "pref_lang": preferred_language,
                "social": social_links, "priority": priority, "currency": currency
            })).scalar_one()
            
            # 3. Attach to Conversation
            conv_query = text("""
                UPDATE conversations SET lead_id = :lead_id 
                WHERE external_contact_id = :phone AND organization_id = :org_id
            """)
            await db.execute(conv_query, {"lead_id": new_lead_id, "phone": patient_phone, "org_id": organization_id})
            await db.commit()

            return f"Successfully created fully enriched lead profile for {first_name} {last_name}."