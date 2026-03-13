"""Guided revision endpoint."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.core.supabase_client import supabase_service
from app.models.schemas import (
    RevisionExplainRequest, RevisionExplainResponse,
    Violation
)
from app.llm import get_llm_client
from app.llm.prompts.guided_revision import (
    get_guided_revision_prompt,
    get_quick_guidance,
    format_revision_response,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/revision", tags=["revision"])


@router.post("/explain/{code}", response_model=RevisionExplainResponse)
async def explain_violation(
    code: str,
    request: RevisionExplainRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed explanation and guidance for a specific violation."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the violation
    violations = session.get("violations", [])
    target_violation = None

    for v in violations:
        if v.get("code") == code:
            try:
                target_violation = Violation(**v)
            except Exception:
                pass
            break

    if not target_violation:
        raise HTTPException(
            status_code=404,
            detail=f"Violation {code} not found in session"
        )

    # Try to get detailed explanation from LLM
    try:
        llm = get_llm_client()
        prompt = get_guided_revision_prompt(
            violation=target_violation,
            section_text=request.section_text,
        )

        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=800,
        )

        return RevisionExplainResponse(
            code=code,
            violation=target_violation,
            explanation=response.content.strip(),
            example=None,
            suggested_rewrite=None,
        )

    except Exception as e:
        # Fallback to quick guidance
        guidance = get_quick_guidance(target_violation)

        return RevisionExplainResponse(
            code=code,
            violation=target_violation,
            explanation=guidance["explanation"],
            example=guidance.get("example"),
            suggested_rewrite=guidance.get("suggested_rewrite"),
        )


@router.get("/all/{session_id}")
async def get_all_revision_guidance(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get quick guidance for all violations in a session."""
    # Get session
    session = await supabase_service.get_research_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    violations = session.get("violations", [])

    if not violations:
        return {
            "session_id": session_id,
            "guidance": [],
            "total": 0,
        }

    # Get quick guidance for each violation
    guidance_list = []
    for v in violations:
        try:
            violation = Violation(**v)
            guidance = get_quick_guidance(violation)
            guidance_list.append({
                "code": violation.code,
                "tier": violation.tier,
                "severity": violation.severity.value,
                "message": violation.message_vi,
                "explanation": guidance["explanation"],
                "path": violation.path_vi,
            })
        except Exception:
            pass

    # Sort by severity and tier
    severity_order = {"BLOCK": 0, "MAJOR": 1, "WARN": 2}
    guidance_list.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["tier"]))

    return {
        "session_id": session_id,
        "guidance": guidance_list,
        "total": len(guidance_list),
    }
