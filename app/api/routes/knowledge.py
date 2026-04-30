from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO
from pypdf import PdfReader
import logging

from app.db.session import AsyncSessionLocal
from app.models.organization import KnowledgeBase
from app.ai.tools import get_gemini_embedding # Re-using our tool!
from app.core.security import verify_internal_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Slices a massive wall of text into overlapping paragraphs.
    Overlap ensures we don't cut a sentence in half and lose context.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap # Move forward, but backtrack slightly for overlap

    return chunks

@router.post("/upload", dependencies=[Depends(verify_internal_service)])
async def upload_document(
    organization_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Receives a PDF from NestJS, extracts the text, embeds it using Gemini,
    and saves it to the organization's vector database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # 1. Read the PDF File in memory
        pdf_bytes = await file.read()
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        
        full_text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                full_text += extracted + "\n"

        if not full_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

        # 2. Chunk the text into digestible paragraphs
        text_chunks = chunk_text(full_text)
        logger.info(f"Extracted {len(text_chunks)} chunks from {file.filename}")

        # 3. Process and Save to Database
        async with AsyncSessionLocal() as db:
            for chunk in text_chunks:
                # Ask Gemini to turn the text into a 768-dimensional vector
                vector = await get_gemini_embedding(chunk)
                
                if vector:
                    # Save to our table with the file_name attached
                    new_doc = KnowledgeBase(
                        organization_id=organization_id,
                        file_name=file.filename,
                        content=chunk,
                        embedding=vector
                    )
                    db.add(new_doc)
            
            # Commit all chunks at once for speed
            await db.commit()

        return {"status": "success", "message": f"Successfully ingested {file.filename}", "chunks_saved": len(text_chunks)}

    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during PDF processing.")