"""
Configuration module for AI Sales Agent microservice.

Loads environment variables and provides validated configuration
using Pydantic Settings for type-safe access across the application.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        google_api_key: API key for Google Generative AI (Gemini).
        database_url: PostgreSQL async connection string.
    """
    
    google_api_key: str = Field(
        ...,
        description="Google API key for Generative AI access (required)",
        validation_alias="GOOGLE_API_KEY",
    )
    
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/ai_sales_agent",
        description="PostgreSQL async connection URL",
        validation_alias="DATABASE_URL",
    )
    
    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @field_validator("google_api_key", mode="before")
    @classmethod
    def validate_google_api_key(cls, v: str | None) -> str:
        """
        Validate that GOOGLE_API_KEY is provided and non-empty.
        
        Args:
            v: The API key value from environment.
            
        Returns:
            The validated API key.
            
        Raises:
            ValueError: If GOOGLE_API_KEY is missing or empty.
        """
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required. "
                "Please set it in your .env file or system environment."
            )
        return v.strip()
    
    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate and normalize the database URL.
        
        Args:
            v: The database URL value.
            
        Returns:
            The validated database URL.
            
        Raises:
            ValueError: If the database URL is invalid.
        """
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError("DATABASE_URL must not be empty.")
        
        url = v.strip()
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL async URL "
                "(e.g., postgresql+asyncpg://user:password@localhost:5432/dbname)"
            )
        
        return url


# Instantiate settings on module load.
# This ensures configuration validation happens at startup.
settings = Settings()
