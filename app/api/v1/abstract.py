"""Abstract generation endpoint."""

from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.core.journal_search import search_journals
from app.models.schemas import (
    AbstractGenerateRequest, AbstractGenerateResponse,
    JournalSuggestion, ResearchBlueprint
)
from app.models.enums import SessionStatus, ConversationState
from app.llm import get_llm_client
from app.llm.prompts.abstract_gen import (
    get_abstract_generation_prompt,
    validate_generated_abstract,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/abstract", tags=["abstract"])


@router.post("/generate", response_model=AbstractGenerateResponse)
async def generate_abstract(
    request: AbstractGenerateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate estimated abstract from blueprint."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check session state
    if session.get("conversation_state") != ConversationState.COMPLETE.value:
        raise HTTPException(
            status_code=400,
            detail="Conversation must be COMPLETE before generating abstract"
        )

    # Get blueprint
    blueprint_data = session.get("blueprint")
    if not blueprint_data:
        raise HTTPException(
            status_code=400,
            detail="No blueprint found. Complete the conversation first."
        )

    try:
        blueprint = ResearchBlueprint(**blueprint_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blueprint data: {str(e)}"
        )

    # Check rate limiting (free tier)
    tier, can_access_paid = await supabase_service.check_user_tier(user_id)
    if tier == "free":
        runs_today = await supabase_service.increment_runs_today(user_id)
        if runs_today > 3:  # Free tier limit
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached for free tier (3 abstracts/day)"
            )

    # Generate abstract using LLM
    try:
        llm = get_llm_client()
        prompt = get_abstract_generation_prompt(blueprint)

        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=1500,
        )

        estimated_abstract = response.content.strip()

        # Validate the generated abstract
        is_valid, issues = validate_generated_abstract(estimated_abstract)
        if not is_valid:
            # Add warnings to the abstract
            warning_text = "\n\n[Canh bao tu dong: " + "; ".join(issues) + "]"
            estimated_abstract += warning_text

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate abstract: {str(e)}"
        )

    # Search for matching journals
    journal_suggestions = []
    try:
        # Create search query from blueprint
        search_query = f"{blueprint.population} {blueprint.primary_outcome} {blueprint.intervention_or_exposure}"

        journals = search_journals(
            query=search_query,
            specialty=blueprint.specialty,
            top_k=5,
        )

        journal_suggestions = [
            JournalSuggestion(
                journal_id=j["journal_id"],
                name=j["name"],
                issn=j.get("issn"),
                impact_factor=j.get("impact_factor"),
                specialty=j.get("specialty"),
                similarity_score=j["similarity_score"],
            )
            for j in journals
        ]
    except Exception as e:
        # Journal search failure is not critical
        print(f"Journal search failed: {e}")

    # Update session
    await supabase_service.update_research_session(
        request.session_id,
        {
            "estimated_abstract": estimated_abstract,
            "journal_suggestions": [j.model_dump() for j in journal_suggestions],
            "status": SessionStatus.ABSTRACT_READY.value,
        }
    )

    # Save abstract version
    await supabase_service.append_abstract_version(
        request.session_id,
        estimated_abstract
    )

    # Add assistant message
    await supabase_service.add_conversation_turn(
        session_id=request.session_id,
        role="assistant",
        content=f"Da tao Estimated Abstract. {len(journal_suggestions)} tap chi phu hop duoc goi y.",
    )

    return AbstractGenerateResponse(
        session_id=request.session_id,
        estimated_abstract=estimated_abstract,
        journal_suggestions=journal_suggestions,
        blueprint=blueprint,
        status=SessionStatus.ABSTRACT_READY,
    )
