from fastapi import FastAPI
from app.api.routes import webhook
from app.core.config import settings

def create_app() -> FastAPI:
    """
    App Factory pattern. This creates the FastAPI application instance
    and configures all routes and middleware.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Enterprise AI Sales Agent Engine backing the NestJS CRM.",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Mount our v1 API routes
    app.include_router(webhook.router, prefix="/api/v1")

    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": "production ready",
            "tenant_mode": "active"
        }

    return app

# The instance that Uvicorn actually runs
app = create_app()

if __name__ == "__main__":
    import uvicorn
    # Make sure we use app='main:app' as a string so the reload flag works correctly
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)