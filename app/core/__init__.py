"""Core infrastructure for AVR Research Formation System.

Modules:
- supabase_client: Database client and session operations
- auth: Authentication and JWT token management
- ws_manager: WebSocket connection management
- session_manager: In-memory session state

Business logic lives in app/domain/:
- domain/extraction: Attribute extraction and Vietnamese text processing
- domain/blueprint: Blueprint builder and conversation state machine
- domain/gate: Tier 0-4 constraint checking and IS calculation
- domain/search: Journal search, PubMed, and roadmap generation
"""

from .supabase_client import supabase_service
from .ws_manager import ws_manager

__all__ = [
    "supabase_service",
    "ws_manager",
]
