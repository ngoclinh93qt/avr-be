"""
Supabase client for authentication and database operations.
"""

from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client with publishable key (for auth operations)."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise ValueError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env"
        )

    return create_client(settings.supabase_url, settings.supabase_publishable_key)


@lru_cache()
def get_supabase_admin() -> Client:
    """Get Supabase admin client with secret key (for backend/database operations)."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise ValueError(
            "Supabase admin not configured. Set SUPABASE_SECRET_KEY in .env"
        )

    return create_client(settings.supabase_url, settings.supabase_secret_key)


class SupabaseService:
    """Service class for Supabase operations."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._admin: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Get regular client (uses anon key)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def admin(self) -> Client:
        """Get admin client (uses service key)."""
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    # ════════════════════════════════════════════════════════
    # Auth Operations
    # ════════════════════════════════════════════════════════

    async def sign_up(self, email: str, password: str) -> dict:
        """Register a new user."""
        response = self.client.auth.sign_up({"email": email, "password": password})
        return {"user": response.user, "session": response.session}

    async def sign_in(self, email: str, password: str) -> dict:
        """Sign in with email/password."""
        response = self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        return {"user": response.user, "session": response.session}

    async def sign_out(self, access_token: str) -> bool:
        """Sign out user."""
        try:
            self.client.auth.sign_out()
            return True
        except Exception:
            return False

    async def get_user(self, access_token: str) -> Optional[dict]:
        """Get user from access token."""
        try:
            response = self.client.auth.get_user(access_token)
            return response.user
        except Exception:
            return None

    async def refresh_session(self, refresh_token: str) -> dict:
        """Refresh user session."""
        response = self.client.auth.refresh_session(refresh_token)
        return {"user": response.user, "session": response.session}

    # ════════════════════════════════════════════════════════
    # Research Sessions (Database)
    # ════════════════════════════════════════════════════════

    async def create_research_session(
        self,
        user_id: str,
        abstract: str,
        language: str = "auto",
    ) -> dict:
        """Create a new research session."""
        data = {
            "user_id": user_id,
            "abstract": abstract,
            "language": language,
            "status": "pending",
        }
        response = self.admin.table("research_sessions").insert(data).execute()
        return response.data[0] if response.data else {}

    async def update_research_session(
        self,
        session_id: str,
        updates: dict,
    ) -> dict:
        """Update a research session."""
        response = (
            self.admin.table("research_sessions")
            .update(updates)
            .eq("id", session_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    async def get_research_session(self, session_id: str) -> Optional[dict]:
        """Get a research session by ID."""
        response = (
            self.admin.table("research_sessions")
            .select("*")
            .eq("id", session_id)
            .single()
            .execute()
        )
        return response.data

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Get user's research sessions."""
        response = (
            self.admin.table("research_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    # ════════════════════════════════════════════════════════
    # Research Papers (Database)
    # ════════════════════════════════════════════════════════

    async def save_research_papers(
        self,
        session_id: str,
        papers: list[dict],
    ) -> list[dict]:
        """Save research papers for a session."""
        data = [
            {
                "session_id": session_id,
                "pmid": p.get("pmid"),
                "title": p.get("title"),
                "authors": p.get("authors", []),
                "abstract": p.get("abstract"),
                "year": p.get("year"),
                "journal": p.get("journal"),
                "doi": p.get("doi"),
                "similarity": p.get("similarity", 0.0),
                "source": p.get("source", "pubmed"),
            }
            for p in papers
        ]
        response = self.admin.table("research_papers").insert(data).execute()
        return response.data or []

    async def get_session_papers(self, session_id: str) -> list[dict]:
        """Get papers for a research session."""
        response = (
            self.admin.table("research_papers")
            .select("*")
            .eq("session_id", session_id)
            .order("similarity", desc=True)
            .execute()
        )
        return response.data or []


# Global instance
supabase_service = SupabaseService()
