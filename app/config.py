"""Configuration for AVR Research Formation System."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True

    # LLM Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None  # Primary provider

    # Local LLM server (OpenAI-compatible)
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None

    # Default provider and model
    default_provider: str = "openrouter"  # openrouter, anthropic, openai, google, local
    default_model: str = "anthropic/claude-3.5-sonnet"

    # Provider-specific model overrides
    anthropic_model: Optional[str] = "claude-3-5-sonnet-20241022"
    openai_model: Optional[str] = "gpt-4o"
    google_model: Optional[str] = "gemini-1.5-pro"
    openrouter_model: Optional[str] = "anthropic/claude-3.5-sonnet"

    # Supabase
    supabase_url: Optional[str] = None
    supabase_publishable_key: Optional[str] = None  # Publishable API key (anon)
    supabase_secret_key: Optional[str] = None       # Secret API key (for admin ops)

    # ChromaDB for journal search
    chroma_db_path: Optional[str] = "./app/data/chroma_journals"

    # Embedding model for ChromaDB
    embedding_model: str = "all-MiniLM-L6-v2"

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:5173"

    # Rate limiting
    free_tier_daily_limit: int = 3  # Abstracts per day for free users

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
