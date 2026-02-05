"""
WebSocket message schemas for realtime communication.

Message Flow:
1. Client sends 'user_message' with abstract
2. Server responds with 'agent_thinking' (status updates)
3. Server sends 'clarification_needed' if abstract incomplete
4. Client sends 'user_message' with answers
5. Server sends 'analysis_progress' during analysis steps
6. Server sends 'analysis_complete' with final results
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Message Types
# ============================================================================


class MessageType(str, Enum):
    """Types of WebSocket messages."""

    # Client → Server
    USER_MESSAGE = "user_message"
    USER_ANSWER = "user_answer"

    # Server → Client
    AGENT_THINKING = "agent_thinking"
    CLARIFICATION_NEEDED = "clarification_needed"
    ANALYSIS_PROGRESS = "analysis_progress"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"
    SESSION_STARTED = "session_started"


# ============================================================================
# Client Messages (Client → Server)
# ============================================================================


class UserMessage(BaseModel):
    """User's initial message with research abstract."""

    type: str = MessageType.USER_MESSAGE
    abstract: str = Field(..., min_length=10, max_length=5000)
    language: Optional[str] = "auto"
    session_id: Optional[str] = None


class UserAnswer(BaseModel):
    """User's answer to clarification questions."""

    type: str = MessageType.USER_ANSWER
    question_id: str
    answer: str
    session_id: str


# ============================================================================
# Server Messages (Server → Client)
# ============================================================================


class SessionStarted(BaseModel):
    """Session initialization confirmation."""

    type: str = MessageType.SESSION_STARTED
    session_id: str
    timestamp: str


class AgentThinking(BaseModel):
    """Agent is processing (with status message)."""

    type: str = MessageType.AGENT_THINKING
    message: str
    step: Optional[str] = None  # "assessing", "analyzing", "generating"
    progress: Optional[int] = None  # 0-100


class ClarificationQuestion(BaseModel):
    """A single clarification question."""

    id: str
    question: str
    element: str  # "methodology", "population", "outcome", etc.
    priority: int  # 1=critical, 2=important, 3=nice-to-have


class ClarificationNeeded(BaseModel):
    """Server needs more information from user."""

    type: str = MessageType.CLARIFICATION_NEEDED
    intro_message: str
    questions: list[ClarificationQuestion]
    skip_allowed: bool = False
    skip_message: Optional[str] = None


class AnalysisProgress(BaseModel):
    """Progress update during analysis."""

    type: str = MessageType.ANALYSIS_PROGRESS
    step: str  # "novelty", "gaps", "swot", "publishability", "suggestions"
    message: str
    progress: int  # 0-100
    partial_result: Optional[dict[str, Any]] = None


class AnalysisComplete(BaseModel):
    """Final analysis results."""

    type: str = MessageType.ANALYSIS_COMPLETE
    result: dict[str, Any]  # Full TopicAnalyzeFullResponse
    processing_time_seconds: float


class ErrorMessage(BaseModel):
    """Error occurred during processing."""

    type: str = MessageType.ERROR
    error: str
    details: Optional[str] = None
    recoverable: bool = True


# ============================================================================
# Union Type for All Messages
# ============================================================================

ClientMessage = UserMessage | UserAnswer
ServerMessage = (
    SessionStarted
    | AgentThinking
    | ClarificationNeeded
    | AnalysisProgress
    | AnalysisComplete
    | ErrorMessage
)
