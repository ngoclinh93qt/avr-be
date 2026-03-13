"""
Supabase client for authentication and database operations.

Tables: profiles, research_sessions, conversation_turns, violations
"""

from datetime import datetime
from functools import lru_cache
from typing import Optional
import json

from supabase import create_async_client, AsyncClient

from app.config import get_settings


async def get_supabase_client() -> AsyncClient:
    """Get Supabase client with publishable key (for auth operations)."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise ValueError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env"
        )

    return await create_async_client(settings.supabase_url, settings.supabase_publishable_key)


async def get_supabase_admin() -> AsyncClient:
    """Get Supabase admin client with secret key (for backend/database operations)."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_secret_key:
        raise ValueError(
            "Supabase admin not configured. Set SUPABASE_SECRET_KEY in .env"
        )

    return await create_async_client(settings.supabase_url, settings.supabase_secret_key)


class SupabaseService:
    """Service class for Supabase operations."""

    def __init__(self):
        self._client: Optional[AsyncClient] = None
        self._admin: Optional[AsyncClient] = None

    async def get_client(self) -> AsyncClient:
        """Get regular client (uses publishable key)."""
        if self._client is None:
            self._client = await get_supabase_client()
        return self._client

    async def get_admin(self) -> AsyncClient:
        """Get admin client (uses secret key)."""
        if self._admin is None:
            self._admin = await get_supabase_admin()
        return self._admin

    # ════════════════════════════════════════════════════════
    # Auth Operations
    # ════════════════════════════════════════════════════════

    async def sign_up(self, email: str, password: str) -> dict:
        """Register a new user."""
        client = await self.get_client()
        response = await client.auth.sign_up({"email": email, "password": password})
        return {"user": response.user, "session": response.session}

    async def sign_in(self, email: str, password: str) -> dict:
        """Sign in with email/password."""
        client = await self.get_client()
        response = await client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        return {"user": response.user, "session": response.session}

    async def sign_out(self, access_token: str) -> bool:
        """Sign out user."""
        try:
            client = await self.get_client()
            await client.auth.sign_out()
            return True
        except Exception:
            return False

    async def get_user(self, access_token: str) -> Optional[dict]:
        """Get user from access token."""
        try:
            client = await self.get_client()
            response = await client.auth.get_user(access_token)
            return response.user
        except Exception:
            return None

    async def refresh_session(self, refresh_token: str) -> dict:
        """Refresh user session."""
        client = await self.get_client()
        response = await client.auth.refresh_session(refresh_token)
        return {"user": response.user, "session": response.session}

    # ════════════════════════════════════════════════════════
    # Profiles
    # ════════════════════════════════════════════════════════

    async def get_profile(self, user_id: str) -> Optional[dict]:
        """Get user profile."""
        admin = await self.get_admin()
        response = await admin.table("profiles").select("*").eq("id", user_id).single().execute()
        return response.data

    async def update_profile(self, user_id: str, updates: dict) -> dict:
        """Update user profile."""
        admin = await self.get_admin()
        response = await admin.table("profiles").update(updates).eq("id", user_id).execute()
        return response.data[0] if response.data else {}

    async def increment_runs_today(self, user_id: str) -> int:
        """Increment runs_today counter and return new value."""
        profile = await self.get_profile(user_id)
        if not profile:
            return 0
        new_count = (profile.get("runs_today") or 0) + 1
        await self.update_profile(user_id, {"runs_today": new_count})
        return new_count

    async def check_user_tier(self, user_id: str) -> tuple[str, bool]:
        """Check user tier and if they can run paid features.

        Returns:
            Tuple of (tier, can_access_paid)
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return "free", False

        tier = profile.get("tier", "free")
        paid_until = profile.get("paid_until")

        if tier == "paid" and paid_until:
            # Check if still valid
            from datetime import datetime, timezone
            if isinstance(paid_until, str):
                paid_until = datetime.fromisoformat(paid_until.replace("Z", "+00:00"))
            if paid_until > datetime.now(timezone.utc):
                return "paid", True

        return tier, tier == "paid"

    # ════════════════════════════════════════════════════════
    # Research Sessions
    # ════════════════════════════════════════════════════════

    async def create_research_session(
        self,
        user_id: str,
        phase: str = "phase1",
    ) -> dict:
        """Create a new research session."""
        data = {
            "user_id": user_id,
            "phase": phase,
            "status": "active",
            "conversation_state": "INITIAL",
            "clarifying_turns_count": 0,
            "extracted_attributes": {},
            "gate_run_count": 0,
            "score_history": [],
            "abstract_versions": [],
        }
        admin = await self.get_admin()
        response = await admin.table("research_sessions").insert(data).execute()
        return response.data[0] if response.data else {}

    async def get_research_session(self, session_id: str) -> Optional[dict]:
        """Get a research session by ID."""
        admin = await self.get_admin()
        response = await admin.table("research_sessions").select("*").eq("id", session_id).single().execute()
        return response.data

    async def update_research_session(
        self,
        session_id: str,
        updates: dict,
    ) -> dict:
        """Update a research session."""
        # Convert complex objects to JSON if needed
        for key in ["extracted_attributes", "blueprint", "violations",
                    "journal_suggestions", "score_history", "abstract_versions"]:
            if key in updates and updates[key] is not None:
                if hasattr(updates[key], "model_dump"):
                    updates[key] = updates[key].model_dump()

        admin = await self.get_admin()
        response = await admin.table("research_sessions").update(updates).eq("id", session_id).execute()
        return response.data[0] if response.data else {}

    async def get_user_sessions(
        self,
        user_id: str,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Get user's research sessions with optional filters."""
        admin = await self.get_admin()
        query = (
            admin.table("research_sessions")
            .select("id, phase, status, conversation_state, created_at, updated_at")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
        )
        if phase:
            query = query.eq("phase", phase)
        if status:
            query = query.eq("status", status)
        query = query.range(offset, offset + limit - 1)
        response = await query.execute()
        return response.data or []

    async def delete_research_session(self, session_id: str) -> bool:
        """Delete a research session (cascades to turns and violations)."""
        try:
            admin = await self.get_admin()
            await admin.table("research_sessions").delete().eq("id", session_id).execute()
            return True
        except Exception:
            return False

    async def append_score_history(
        self,
        session_id: str,
        score: float,
    ) -> dict:
        """Append a score to the session's score history."""
        session = await self.get_research_session(session_id)
        if not session:
            return {}

        history = session.get("score_history") or []
        history.append(score)

        return await self.update_research_session(
            session_id,
            {
                "score_history": history,
                "gate_run_count": len(history),
            }
        )

    async def append_abstract_version(
        self,
        session_id: str,
        abstract: str,
    ) -> dict:
        """Append an abstract version to history."""
        session = await self.get_research_session(session_id)
        if not session:
            return {}

        versions = session.get("abstract_versions") or []
        versions.append({
            "version": len(versions) + 1,
            "abstract": abstract,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return await self.update_research_session(
            session_id,
            {"abstract_versions": versions}
        )

    # ════════════════════════════════════════════════════════
    # Conversation Turns
    # ════════════════════════════════════════════════════════

    async def add_conversation_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        extracted_attributes: Optional[dict] = None,
    ) -> dict:
        """Add a conversation turn."""
        data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "extracted_attributes": extracted_attributes or {},
        }
        admin = await self.get_admin()
        response = await admin.table("conversation_turns").insert(data).execute()

        # Update session's clarifying turns count if user message
        if role == "user":
            session = await self.get_research_session(session_id)
            if session:
                await self.update_research_session(
                    session_id,
                    {"clarifying_turns_count": (session.get("clarifying_turns_count") or 0) + 1}
                )

        return response.data[0] if response.data else {}

    async def get_conversation_turns(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Get conversation turns for a session."""
        admin = await self.get_admin()
        query = (
            admin.table("conversation_turns")
            .select("*")
            .eq("session_id", session_id)
            .order("turn_number", desc=False)
        )
        if limit:
            query = query.limit(limit)
        response = await query.execute()
        return response.data or []

    async def get_last_turn(self, session_id: str) -> Optional[dict]:
        """Get the last conversation turn."""
        admin = await self.get_admin()
        response = await admin.table("conversation_turns").select("*").eq("session_id", session_id).order("turn_number", desc=True).limit(1).execute()
        return response.data[0] if response.data else None

    # ════════════════════════════════════════════════════════
    # Violations
    # ════════════════════════════════════════════════════════

    async def save_violations(
        self,
        session_id: str,
        violations: list[dict],
        gate_run_number: int,
    ) -> list[dict]:
        """Save violations for a gate run."""
        if not violations:
            return []

        data = []
        for v in violations:
            violation_data = {
                "session_id": session_id,
                "code": v.get("code"),
                "tier": v.get("tier"),
                "severity": v.get("severity"),
                "message_vi": v.get("message_vi"),
                "path_vi": v.get("path_vi"),
                "context": v.get("context", {}),
                "gate_run_number": gate_run_number,
            }
            data.append(violation_data)

        admin = await self.get_admin()
        response = await admin.table("violations").insert(data).execute()
        return response.data or []

    async def get_session_violations(
        self,
        session_id: str,
        gate_run_number: Optional[int] = None,
    ) -> list[dict]:
        """Get violations for a session, optionally filtered by gate run."""
        admin = await self.get_admin()
        query = (
            admin.table("violations")
            .select("*")
            .eq("session_id", session_id)
        )
        if gate_run_number is not None:
            query = query.eq("gate_run_number", gate_run_number)
        query = query.order("tier", desc=False)
        response = await query.execute()
        return response.data or []

    async def get_latest_violations(self, session_id: str) -> list[dict]:
        """Get violations from the latest gate run."""
        session = await self.get_research_session(session_id)
        if not session:
            return []

        gate_run_count = session.get("gate_run_count", 0)
        if gate_run_count == 0:
            return []

        return await self.get_session_violations(session_id, gate_run_count)


# Global instance
supabase_service = SupabaseService()
