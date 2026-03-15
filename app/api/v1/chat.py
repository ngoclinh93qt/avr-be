"""Chat endpoint for conversational engine."""

from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.domain.extraction.extractor import extract_attributes, merge_attributes
from app.domain.blueprint.conversation import (
    evaluate_completeness,
    get_missing_element_questions,
    get_clarification_intro,
    format_blocking_message,
    should_ask_clarification,
)
from app.domain.blueprint.blueprint_builder import build_blueprint
from app.models.schemas import (
    ChatMessageRequest, ChatMessageResponse,
    ExtractedAttributes
)
from app.models.enums import ConversationState, SessionStatus
from app.llm import get_llm_client
from app.llm.prompts.clarify import get_clarification_prompt, SYSTEM_PROMPT
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Send a message in the conversation."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if session.get("status") != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.get('status')}, cannot send messages"
        )

    # Extract attributes from user message
    existing_attrs = None
    if session.get("extracted_attributes"):
        try:
            existing_attrs = ExtractedAttributes(**session["extracted_attributes"])
        except Exception:
            existing_attrs = ExtractedAttributes()

    new_attrs = extract_attributes(request.message, existing_attrs)
    merged_attrs = merge_attributes(existing_attrs or ExtractedAttributes(), new_attrs)

    # Save user message
    await supabase_service.add_conversation_turn(
        session_id=request.session_id,
        role="user",
        content=request.message,
        extracted_attributes=new_attrs.model_dump(),
    )

    # Evaluate completeness
    design_type = merged_attrs.design_type
    turns_count = session.get("clarifying_turns_count", 0) + 1

    completeness = evaluate_completeness(
        attributes=merged_attrs,
        design_type=design_type,
        clarifying_turns=turns_count,
    )

    # Determine next state and generate response
    if completeness.blocking_issues:
        # BLOCKED state
        response_message = format_blocking_message(completeness.blocking_issues)
        next_state = ConversationState.BLOCKED
        next_action = "blocked"
        blueprint = None

    elif completeness.is_complete:
        # COMPLETE state - build blueprint
        blueprint = build_blueprint(merged_attrs, design_type)
        response_message = _format_completion_message(blueprint)
        next_state = ConversationState.COMPLETE
        next_action = "generate_abstract"

    else:
        # CLARIFYING state - ask more questions
        next_state = ConversationState.CLARIFYING

        # Get questions for missing elements
        questions = get_missing_element_questions(
            completeness.missing_elements,
            design_type
        )

        # Use LLM to generate natural questions
        try:
            llm = get_llm_client()
            history = await supabase_service.get_conversation_turns(
                request.session_id, limit=10
            )

            prompt = get_clarification_prompt(
                missing_elements=completeness.missing_elements,
                current_attributes=merged_attrs,
                conversation_history=[
                    {"role": t["role"], "content": t["content"]}
                    for t in history
                ],
                turn_number=turns_count,
            )

            llm_response = await llm.complete(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=500,
            )
            response_message = llm_response.content

        except Exception as e:
            # Fallback to rule-based questions
            intro = get_clarification_intro(
                len(completeness.missing_elements),
                turns_count
            )
            question_texts = [q["question"] for q in questions[:3]]
            response_message = intro + "\n\n" + "\n".join(
                f"{i+1}. {q}" for i, q in enumerate(question_texts)
            )

        next_action = "continue"
        blueprint = None

    # Save assistant response
    await supabase_service.add_conversation_turn(
        session_id=request.session_id,
        role="assistant",
        content=response_message,
    )

    # Update session
    session_updates = {
        "conversation_state": next_state.value,
        "extracted_attributes": merged_attrs.model_dump(),
    }

    if blueprint:
        session_updates["blueprint"] = blueprint.model_dump()

    if next_state == ConversationState.COMPLETE:
        session_updates["status"] = SessionStatus.ABSTRACT_READY.value

    await supabase_service.update_research_session(
        request.session_id,
        session_updates,
    )

    return ChatMessageResponse(
        session_id=request.session_id,
        assistant_message=response_message,
        conversation_state=next_state,
        extracted_attributes=merged_attrs,
        blueprint=blueprint,
        next_action=next_action,
        missing_elements=completeness.missing_elements,
    )


def _format_completion_message(blueprint) -> str:
    """Format completion message with blueprint summary."""
    from app.rules.design_rules import get_design_display_name

    design_name = get_design_display_name(blueprint.design_type)

    message = f"""Tuyet voi! Toi da thu thap du thong tin de xay dung Research Blueprint.

**RESEARCH BLUEPRINT**

**PICO(T):**
- Population (P): {blueprint.population}
- Intervention/Exposure (I): {blueprint.intervention_or_exposure}
- Comparator (C): {blueprint.comparator or 'N/A'}
- Outcome (O): {blueprint.primary_outcome}
- Timeframe (T): {blueprint.timeframe or 'N/A'}

**Thiet ke:** {design_name}
**Co mau:** n = {blueprint.sample_size}

"""

    if blueprint.warnings:
        message += "**Luu y:**\n"
        for w in blueprint.warnings[:3]:
            message += f"- {w}\n"
        message += "\n"

    message += "Ban co the tien hanh tao Estimated Abstract bang cach su dung endpoint `/abstract/generate`."

    return message
