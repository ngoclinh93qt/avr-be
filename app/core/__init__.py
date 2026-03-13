"""Core business logic for AVR Research Formation System.

Modules:
- supabase_client: Database operations
- conversation: State machine for conversation flow
- extractor: Attribute extraction from user input
- blueprint_builder: Research blueprint construction
- gate_engine: Tier 0-4 constraint checking and IS calculation
- journal_search: ChromaDB vector search for journals
- ws_manager: WebSocket connection management
"""

from .supabase_client import supabase_service
from .ws_manager import ws_manager

__all__ = [
    "supabase_service",
    "ws_manager",
]
