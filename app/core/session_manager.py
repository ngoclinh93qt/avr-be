"""
Session Manager for WebSocket conversations.

Manages conversation state including:
- User's abstract and language
- Clarification questions and answers
- Analysis progress
- Enriched abstract after clarification
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ConversationSession:
    """Represents a single conversation session."""

    session_id: str
    created_at: datetime
    abstract: str
    language: str = "auto"

    # Clarification phase
    assessment: Optional[dict] = None
    clarification_questions: Optional[dict] = None
    user_answers: dict[str, str] = field(default_factory=dict)
    enriched_abstract: Optional[str] = None

    # Analysis phase
    analysis_results: dict = field(default_factory=dict)
    current_step: Optional[str] = None
    is_complete: bool = False

    # Metadata
    last_activity: datetime = field(default_factory=datetime.now)


class SessionManager:
    """
    In-memory session manager for WebSocket conversations.

    For production, consider using Redis or a database for persistence.
    """

    def __init__(self):
        self._sessions: dict[str, ConversationSession] = {}

    def create_session(self, abstract: str, language: str = "auto") -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        session = ConversationSession(
            session_id=session_id,
            created_at=datetime.now(),
            abstract=abstract,
            language=language,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session."""
        session = self._sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session

    def update_session(self, session_id: str, **kwargs) -> Optional[ConversationSession]:
        """Update session fields."""
        session = self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
        return session

    def add_user_answer(self, session_id: str, question_id: str, answer: str) -> Optional[ConversationSession]:
        """Add a user's answer to a clarification question."""
        session = self.get_session(session_id)
        if session:
            session.user_answers[question_id] = answer
        return session

    def store_analysis_result(
        self, session_id: str, step: str, result: dict
    ) -> Optional[ConversationSession]:
        """Store partial analysis result."""
        session = self.get_session(session_id)
        if session:
            session.analysis_results[step] = result
            session.current_step = step
        return session

    def mark_complete(self, session_id: str, final_result: dict) -> Optional[ConversationSession]:
        """Mark session as complete with final results."""
        session = self.get_session(session_id)
        if session:
            session.analysis_results["final"] = final_result
            session.is_complete = True
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        now = datetime.now()
        to_delete = []
        for session_id, session in self._sessions.items():
            age = (now - session.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)

        for session_id in to_delete:
            del self._sessions[session_id]

        return len(to_delete)

    @property
    def active_sessions(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global instance
session_manager = SessionManager()
