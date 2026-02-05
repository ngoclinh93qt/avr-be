from fastapi import APIRouter

from app.api.v1 import auth, history, journal, manuscript, topic, ws_topic

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router)

# Research history
api_router.include_router(history.router)

# Feature routes
api_router.include_router(topic.router, prefix="/topic", tags=["Topic Analyzer"])
api_router.include_router(
    journal.router, prefix="/journal", tags=["Journal Matcher"]
)
api_router.include_router(
    manuscript.router, prefix="/manuscript", tags=["Manuscript Strategist"]
)

# WebSocket routes
api_router.include_router(ws_topic.router, tags=["WebSocket - Topic Analyzer"])
