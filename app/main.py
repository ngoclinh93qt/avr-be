from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AVR API",
    description="AI-powered Vietnamese Research Assistant",
    version="0.1.0",
    debug=settings.debug,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/config")
async def debug_config():
    from app.core.llm_router import llm_router
    return {
        "default_provider": settings.default_provider,
        "openrouter_model": settings.openrouter_model,
        "openrouter_key_prefix": settings.openrouter_api_key[:20] + "..." if settings.openrouter_api_key else None,
        "available_providers": llm_router.available_providers,
        "resolved_provider": llm_router.get_default_provider(),
    }

