from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True
    
    # LLM Providers - all optional to allow flexible configuration
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Local LLM server (OpenAI-compatible)
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None

    # Default provider and model
    default_provider: str = "local"  # local, anthropic, openai, google, openrouter
    default_model: str = "glm-4.7-flash-mlx"

    # Provider-specific model overrides (optional)
    anthropic_model: Optional[str] = None
    openai_model: Optional[str] = None
    google_model: Optional[str] = None
    openrouter_model: Optional[str] = None
    
    # Supabase (new key format: Publishable + Secret)
    supabase_url: Optional[str] = None
    supabase_publishable_key: Optional[str] = None  # Publishable API key (anon)
    supabase_secret_key: Optional[str] = None  # Secret API key (for admin ops)

    # Database (legacy - use Supabase instead)
    database_url: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
