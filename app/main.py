"""AVR Research Formation System - Main Application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings

settings = get_settings()

# Configure logging — ensure INFO level for our app modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Set DEBUG for extraction/design modules during debugging
for _mod in ("app.core.extractor", "app.rules.design_rules", "app.api.v1.ws_chat", "app.api.v1.abstract", "app.llm.client"):
    logging.getLogger(_mod).setLevel(logging.DEBUG)

app = FastAPI(
    title="AVR Research Formation System",
    description=(
        "AI-powered Vietnamese Research Assistant\n\n"
        "## Phases\n"
        "- **Phase 1** (Free): Conversational Idea Engine -> Blueprint -> Estimated Abstract\n"
        "- **Phase 2** (Paid): Submission Gate (Tier 0-4) -> Integrity Score -> Reviewer Simulation\n"
        "- **Phase 3** (Paid): Full Manuscript Outline (journal-specific)\n"
    ),
    version="2.2.0",
    debug=settings.debug,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://avr-app-9c203.web.app",
        "https://avr-app-9c203.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.2.0"}


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration."""
    return {
        "app_env": settings.app_env,
        "default_provider": settings.default_provider,
        "openrouter_configured": settings.openrouter_api_key is not None,
        "anthropic_configured": settings.anthropic_api_key is not None,
        "openai_configured": settings.openai_api_key is not None,
        "supabase_configured": settings.supabase_url is not None,
        "chroma_db_path": settings.chroma_db_path,
        "embedding_model": settings.embedding_model,
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AVR Research Formation System",
        "version": "2.2.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "session": "/api/v1/session",
            "chat": "/api/v1/chat",
            "abstract": "/api/v1/abstract",
            "gate": "/api/v1/gate",
            "revision": "/api/v1/revision",
            "outline": "/api/v1/outline",
            "ws_chat": "/api/v1/ws/chat",
        }
    }
