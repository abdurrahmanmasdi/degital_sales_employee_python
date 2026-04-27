"""
AI Sales Agent Microservice - Main Entry Point

FastAPI application serving an enterprise-grade AI sales agent
that processes WhatsApp messages and generates contextual sales replies
using Google Generative AI (Gemini 2.5 Flash).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting AI Sales Agent microservice...")
    yield
    logger.info("Shutting down AI Sales Agent microservice...")


# Initialize FastAPI application
app = FastAPI(
    title="AI Sales Agent",
    description="Enterprise-grade AI sales agent microservice using Gemini 2.5 Flash",
    version="1.0.0",
    lifespan=lifespan,
)


# Include webhook router with prefix
app.include_router(webhook.router, prefix="/webhook")


@app.get("/", tags=["health"])
async def root_health_check() -> JSONResponse:
    """
    Root health check endpoint.
    
    Simple endpoint to verify the API is running and accessible.
    
    Returns:
        JSON response with service status and version information.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "AI Sales Agent",
            "version": "1.0.0",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )