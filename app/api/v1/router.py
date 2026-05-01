"""API v1 Router - Research Formation System."""

from fastapi import APIRouter

from app.api.v1 import auth, session, chat, abstract, gate, revision, outline, ws_chat, export, account

api_router = APIRouter()

# Authentication
api_router.include_router(auth.router, tags=["Auth"])

# Session management
api_router.include_router(session.router, tags=["Session"])

# Conversational engine
api_router.include_router(chat.router, tags=["Chat"])

# Abstract generation
api_router.include_router(abstract.router, tags=["Abstract"])

# Submission gate (Phase 2)
api_router.include_router(gate.router, tags=["Gate"])

# Guided revision
api_router.include_router(revision.router, tags=["Revision"])

# Manuscript outline (Phase 3)
api_router.include_router(outline.router, tags=["Outline"])

# Export (Phase 1 Research Brief)
api_router.include_router(export.router, tags=["Export"])

# Account / quota
api_router.include_router(account.router, tags=["Account"])

# WebSocket
api_router.include_router(ws_chat.router, tags=["WebSocket"])
