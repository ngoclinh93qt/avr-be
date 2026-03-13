"""Submission gate endpoint (Phase 2)."""

from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.core.gate_engine import (
    run_gate,
    format_violations_for_display,
    get_gate_result_message,
    can_proceed_to_outline,
)
from app.models.schemas import (
    GateRunRequest, GateRunResponse,
    Violation, ResearchBlueprint, ExtractedAttributes
)
from app.models.enums import SessionStatus, GateResult
from app.llm import get_llm_client
from app.llm.prompts.reviewer_sim import (
    get_reviewer_simulation_prompt,
    format_reviewer_response,
    get_quick_feedback,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/gate", tags=["gate"])


@router.post("/run", response_model=GateRunResponse)
async def run_gate_check(
    request: GateRunRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Run submission gate check on abstract."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check user tier - Phase 2 is paid
    tier, can_access = await supabase_service.check_user_tier(user_id)
    if not can_access:
        raise HTTPException(
            status_code=403,
            detail="Gate check requires paid subscription"
        )

    # Get blueprint and attributes if available
    blueprint = None
    attributes = None

    if session.get("blueprint"):
        try:
            blueprint = ResearchBlueprint(**session["blueprint"])
        except Exception:
            pass

    if session.get("extracted_attributes"):
        try:
            attributes = ExtractedAttributes(**session["extracted_attributes"])
        except Exception:
            pass

    # Check for rare disease confirmation (R-10)
    rare_disease_confirmed = False
    if attributes and attributes.rare_disease_confirmed:
        rare_disease_confirmed = True

    # Run gate check (R-11: Re-run full check each submission)
    gate_result = run_gate(
        abstract=request.abstract,
        blueprint=blueprint,
        attributes=attributes,
        rare_disease_confirmed=rare_disease_confirmed,
    )

    # Convert violations to schema
    violations = [
        Violation(
            code=v.code,
            tier=v.tier,
            severity=v.severity,
            message_vi=v.message_vi,
            path_vi=v.path_vi,
            context=v.context,
        )
        for v in gate_result.violations
    ]

    # Save violations to database
    gate_run_count = session.get("gate_run_count", 0) + 1
    await supabase_service.save_violations(
        session_id=request.session_id,
        violations=[v.model_dump() for v in violations],
        gate_run_number=gate_run_count,
    )

    # Generate reviewer simulation
    reviewer_sim = None
    try:
        llm = get_llm_client()
        prompt = get_reviewer_simulation_prompt(
            violations=violations,
            gate_result=gate_result.gate_result,
            integrity_score=gate_result.integrity_score,
            gate_run_count=gate_run_count,
        )

        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=1000,
        )
        reviewer_sim = response.content.strip()

    except Exception as e:
        # Fallback to quick feedback
        reviewer_sim = get_quick_feedback(violations, gate_result.gate_result)

    # Update session
    await supabase_service.update_research_session(
        request.session_id,
        {
            "submitted_abstract": request.abstract,
            "violations": [v.model_dump() for v in violations],
            "integrity_score": gate_result.integrity_score,
            "gate_result": gate_result.gate_result.value,
            "reviewer_simulation": reviewer_sim,
            "gate_run_count": gate_run_count,
            "status": SessionStatus.GATE_RUN.value,
        }
    )

    # Append to score history
    await supabase_service.append_score_history(
        request.session_id,
        gate_result.integrity_score,
    )

    # Append abstract version
    await supabase_service.append_abstract_version(
        request.session_id,
        request.abstract,
    )

    # Get updated score history
    updated_session = await supabase_service.get_research_session(request.session_id)
    score_history = updated_session.get("score_history", [])

    return GateRunResponse(
        session_id=request.session_id,
        gate_result=gate_result.gate_result,
        integrity_score=gate_result.integrity_score,
        violations=violations,
        reviewer_simulation=reviewer_sim,
        gate_run_count=gate_run_count,
        score_history=score_history,
        can_proceed_to_phase3=can_proceed_to_outline(gate_result.gate_result),
    )
