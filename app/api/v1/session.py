"""Session management endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.models.schemas import (
    SessionStartRequest, SessionStartResponse,
    SessionDetailResponse, SessionListItem
)
from app.models.enums import Phase, SessionStatus, ConversationState
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/session", tags=["session"])


WELCOME_MESSAGES = {
    Phase.PHASE1: (
        "Chào bạn! Tôi là trợ lý nghiên cứu AVR. "
        "Hãy mô tả ý tưởng nghiên cứu của bạn — tôi sẽ giúp xây dựng Research Blueprint. "
        "Bạn có thể mô tả bằng tiếng Việt, tiếng Anh, hoặc kết hợp cả hai."
    ),
    Phase.PHASE2: (
        "Chào bạn! Đây là Phase 2 — Cửa ải kiểm duyệt. "
        "Hãy dán abstract hoàn chỉnh (có data thật) để tôi đánh giá theo tiêu chuẩn tạp chí quốc tế."
    ),
}


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Start a new research session."""
    # Check user tier for Phase 2/3
    if request.phase in [Phase.PHASE2, Phase.PHASE3]:
        tier, can_access = await supabase_service.check_user_tier(user_id)
        if not can_access:
            raise HTTPException(
                status_code=403,
                detail=f"Phase {request.phase.value} requires paid subscription"
            )

    # Create session
    session = await supabase_service.create_research_session(
        user_id=user_id,
        phase=request.phase.value,
    )

    if not session:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # Add welcome message
    welcome = WELCOME_MESSAGES.get(request.phase, WELCOME_MESSAGES[Phase.PHASE1])
    await supabase_service.add_conversation_turn(
        session_id=session["id"],
        role="assistant",
        content=welcome,
    )

    return SessionStartResponse(
        session_id=session["id"],
        phase=request.phase,
        status=SessionStatus.ACTIVE,
        conversation_state=ConversationState.INITIAL,
        welcome_message=welcome,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get session details."""
    session = await supabase_service.get_research_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify ownership
    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _session_to_response(session)


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: Optional[int] = None,
    user_id: str = Depends(get_current_user_id),
):
    """Get conversation history for a session."""
    session = await supabase_service.get_research_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    turns = await supabase_service.get_conversation_turns(session_id, limit=limit)

    return {
        "session_id": session_id,
        "turns": turns,
        "total_turns": len(turns),
    }


@router.get("/", response_model=list[SessionListItem])
async def list_sessions(
    phase: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """List user's sessions."""
    sessions = await supabase_service.get_user_sessions(
        user_id=user_id,
        phase=phase,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        SessionListItem(
            id=s["id"],
            phase=Phase(s["phase"]),
            status=SessionStatus(s["status"]),
            conversation_state=ConversationState(s["conversation_state"]),
            created_at=s["created_at"],
            updated_at=s["updated_at"],
        )
        for s in sessions
    ]


@router.post("/{session_id}/advance-phase", response_model=SessionDetailResponse)
async def advance_session_phase(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance a completed Phase 1 session to Phase 2."""
    session = await supabase_service.get_research_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if session.get("phase") != Phase.PHASE1.value:
        raise HTTPException(status_code=400, detail="Session must be in phase1 to advance")

    if session.get("status") != SessionStatus.ABSTRACT_READY.value:
        raise HTTPException(
            status_code=400,
            detail="Abstract must be generated before advancing to phase2. Complete Phase 1 first."
        )

    # Check user tier for Phase 2 (disabled for dev)
    # tier, can_access = await supabase_service.check_user_tier(user_id)
    # if not can_access:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Phase 2 requires a paid subscription"
    #     )

    await supabase_service.update_research_session(
        session_id,
        {"phase": Phase.PHASE2.value}
    )

    updated = await supabase_service.get_research_session(session_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to fetch updated session")

    return _session_to_response(updated)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a session."""
    session = await supabase_service.get_research_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await supabase_service.delete_research_session(session_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")

    return {"status": "deleted", "session_id": session_id}


def _session_to_response(session: dict) -> SessionDetailResponse:
    """Convert database session to response model."""
    from app.models.schemas import ExtractedAttributes, ResearchBlueprint, Violation

    # Parse extracted attributes
    extracted_attrs = None
    if session.get("extracted_attributes"):
        try:
            extracted_attrs = ExtractedAttributes(**session["extracted_attributes"])
        except Exception:
            pass

    # Parse blueprint
    blueprint = None
    novelty_check = None
    roadmap = None
    
    if session.get("blueprint"):
        try:
            blueprint = ResearchBlueprint(**session["blueprint"])
            # The backend saved these inside the blueprint JSONB, extract them!
            novelty_check = session["blueprint"].get("novelty_check")
            roadmap = session["blueprint"].get("roadmap")
        except Exception:
            pass

    # Parse violations
    violations = []
    if session.get("violations"):
        for v in session["violations"]:
            try:
                violations.append(Violation(**v))
            except Exception:
                pass

    return SessionDetailResponse(
        id=session["id"],
        user_id=session["user_id"],
        phase=Phase(session["phase"]),
        status=SessionStatus(session["status"]),
        conversation_state=ConversationState(session["conversation_state"]),
        clarifying_turns_count=session.get("clarifying_turns_count", 0),
        extracted_attributes=extracted_attrs,
        blueprint=blueprint,
        estimated_abstract=session.get("estimated_abstract"),
        journal_suggestions=session.get("journal_suggestions", []),
        gate_result=session.get("gate_result"),
        integrity_score=session.get("integrity_score"),
        violations=violations,
        reviewer_simulation=session.get("reviewer_simulation"),
        manuscript_outline=session.get("manuscript_outline"),
        gate_run_count=session.get("gate_run_count", 0),
        novelty_check=novelty_check,
        roadmap=roadmap,
        created_at=session["created_at"],
        updated_at=session["updated_at"],
    )
