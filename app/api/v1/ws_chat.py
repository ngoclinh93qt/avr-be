"""WebSocket chat endpoint for real-time conversation."""

import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.supabase_client import supabase_service
from app.domain.extraction.extractor import extract_attributes, merge_attributes
from app.domain.blueprint.conversation import (
    evaluate_completeness,
    get_missing_element_questions,
    format_blocking_message,
)
from app.domain.blueprint.blueprint_builder import build_blueprint
from app.core.ws_manager import ws_manager
from app.models.schemas import ExtractedAttributes
from app.models.enums import ConversationState, SessionStatus
from app.llm import get_llm_client
from app.llm.prompts.clarify import get_clarification_prompt, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Default user for development (bypass auth)
DEFAULT_USER_ID = "53262502-c85d-436f-98eb-66f518383813"  # admin@avr.com
DEV_MODE = True  # Set to False in production


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.

    Protocol:
    1. Client connects
    2. Client sends: {"type": "auth", "token": "..."} (optional in dev mode)
    3. Server responds: {"type": "auth_success"} or {"type": "error", "error": "..."}
    4. Client sends: {"type": "start_session", "session_id": "..."} or {"type": "create_session"}
    5. Client sends: {"type": "chat", "message": "..."}
    6. Server streams: {"type": "stream", "content": "...", "done": false}
    7. Server sends final: {"type": "stream", "content": "", "done": true, "state": "...", "blueprint": {...}}
    """
    client = websocket.client
    logger.info("WebSocket connected: %s:%s", client.host if client else "unknown", client.port if client else "?")
    await websocket.accept()

    # In dev mode, use default user; otherwise require auth
    user_id: Optional[str] = DEFAULT_USER_ID if DEV_MODE else None
    session_id: Optional[str] = None

    # Register with ws_manager so HTTP handlers can push messages to this connection
    if DEV_MODE and user_id:
        ws_manager.register(websocket, user_id)

    # Send auto-auth success in dev mode
    if DEV_MODE and user_id:
        logger.debug("Dev mode: auto-auth user_id=%s", user_id)
        await websocket.send_json({"type": "auth_success", "user_id": user_id, "dev_mode": True})

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON from client: %s | raw=%r", e, data[:200])
                await _send_error(websocket, "Invalid JSON")
                continue

            msg_type = message.get("type")
            logger.debug("Received message type=%r session_id=%s", msg_type, session_id)

            # Handle authentication (still supported, will override default)
            if msg_type == "auth":
                token = message.get("token")
                if not token:
                    if DEV_MODE:
                        # In dev mode, auth without token is OK
                        await websocket.send_json({"type": "auth_success", "user_id": user_id, "dev_mode": True})
                        continue
                    await _send_error(websocket, "Token required")
                    continue

                # Validate token
                user = await supabase_service.get_user(token)
                if not user:
                    if DEV_MODE:
                        # In dev mode, invalid token falls back to default user
                        logger.warning("Dev mode: invalid token, falling back to default user")
                        await websocket.send_json({"type": "auth_success", "user_id": user_id, "dev_mode": True})
                        continue
                    logger.warning("Auth failed: invalid token")
                    await _send_error(websocket, "Invalid token")
                    continue

                user_id = user.id if hasattr(user, 'id') else user.get('id')
                ws_manager.register(websocket, user_id)
                logger.info("Auth success: user_id=%s", user_id)
                await websocket.send_json({"type": "auth_success", "user_id": user_id})
                continue

            # Require auth for other operations (skip in dev mode)
            if not user_id:
                await _send_error(websocket, "Not authenticated")
                continue

            # Handle session operations
            if msg_type == "create_session":
                phase = message.get("phase", "phase1")
                logger.info("Creating session: user_id=%s phase=%s", user_id, phase)
                session = await supabase_service.create_research_session(
                    user_id=user_id,
                    phase=phase,
                )
                session_id = session["id"]
                logger.info("Session created: session_id=%s", session_id)

                # Send welcome message
                welcome = (
                    "Chào bạn! Tôi là trợ lý nghiên cứu AVR. "
                    "Hãy chia sẻ ý tưởng nghiên cứu của bạn — "
                    "tôi sẽ giúp xây dựng Research Blueprint từng bước."
                )
                await supabase_service.add_conversation_turn(
                    session_id=session_id,
                    role="assistant",
                    content=welcome,
                )

                await websocket.send_json({
                    "type": "session_created",
                    "session_id": session_id,
                    "welcome_message": welcome,
                })
                continue

            if msg_type == "start_session":
                session_id = message.get("session_id")
                if not session_id:
                    await _send_error(websocket, "session_id required")
                    continue

                # Verify session ownership
                logger.info("Starting session: session_id=%s user_id=%s", session_id, user_id)
                session = await supabase_service.get_research_session(session_id)
                if not session or session.get("user_id") != user_id:
                    logger.warning("Session access denied: session_id=%s user_id=%s found=%s", session_id, user_id, bool(session))
                    await _send_error(websocket, "Session not found or access denied")
                    session_id = None
                    continue

                # Load conversation history
                turns = await supabase_service.get_conversation_turns(session_id, limit=20)

                await websocket.send_json({
                    "type": "session_started",
                    "session_id": session_id,
                    "state": session.get("conversation_state"),
                    "history": turns,
                })
                continue

            # Handle chat message
            if msg_type == "chat":
                if not session_id:
                    await _send_error(websocket, "No session active")
                    continue

                user_message = message.get("message", "").strip()
                if not user_message:
                    await _send_error(websocket, "Empty message")
                    continue

                logger.info("Processing chat: session_id=%s message_len=%d", session_id, len(user_message))
                # Process the message
                await _process_chat_message(
                    websocket=websocket,
                    session_id=session_id,
                    user_message=user_message,
                )
                continue

            logger.warning("Unknown message type: %r", msg_type)
            await _send_error(websocket, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        if user_id:
            ws_manager.disconnect(websocket, user_id)
        logger.info("WebSocket disconnected: session_id=%s user_id=%s", session_id, user_id)
    except Exception as e:
        if user_id:
            ws_manager.disconnect(websocket, user_id)
        logger.exception("Unhandled WebSocket error: session_id=%s user_id=%s", session_id, user_id)
        try:
            await _send_error(websocket, f"Internal server error: {e}")
        except Exception:
            pass  # Connection may already be closed


async def _send_error(websocket: WebSocket, error: str):
    """Send error message to client."""
    logger.error("Sending error to client: %s", error)
    await websocket.send_json({
        "type": "error",
        "error": error,
        "recoverable": True,
    })


async def _process_chat_message(
    websocket: WebSocket,
    session_id: str,
    user_message: str,
):
    """Process a chat message and stream response."""
    # Get session
    session = await supabase_service.get_research_session(session_id)
    if not session:
        await _send_error(websocket, "Session not found")
        return

    # Extract attributes
    existing_attrs = None
    if session.get("extracted_attributes"):
        try:
            existing_attrs = ExtractedAttributes(**session["extracted_attributes"])
        except Exception as e:
            logger.warning("Failed to parse existing attributes for session %s: %s", session_id, e)
            existing_attrs = ExtractedAttributes()

    logger.info("─── [CHAT] session=%s | message=%r", session_id, user_message[:300])
    logger.info("[CHAT] existing_attrs before extraction: %s",
                existing_attrs.model_dump(exclude_none=True) if existing_attrs else "None")

    new_attrs = extract_attributes(user_message, existing_attrs)
    merged_attrs = merge_attributes(existing_attrs or ExtractedAttributes(), new_attrs)

    logger.info("[CHAT] merged_attrs after extraction: %s",
                merged_attrs.model_dump(exclude_none=True))

    # Save user message
    await supabase_service.add_conversation_turn(
        session_id=session_id,
        role="user",
        content=user_message,
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
    logger.info(
        "[CHAT] Completeness: turn=%d  is_complete=%s  score=%.0f%%  "
        "missing=%s  blocking=%s  next_state=%s",
        turns_count, completeness.is_complete, completeness.completeness_score,
        completeness.missing_elements, completeness.blocking_issues,
        completeness.next_state.value,
    )

    # Generate response
    if completeness.blocking_issues:
        response_text = format_blocking_message(completeness.blocking_issues)
        next_state = ConversationState.BLOCKED
        blueprint = None
        await websocket.send_json({"type": "stream", "content": response_text, "done": False})

    elif completeness.is_complete:
        logger.info("[CHAT] Session %s COMPLETE — building blueprint (design=%s)", session_id, design_type)
        blueprint = build_blueprint(merged_attrs, design_type)
        logger.info("[CHAT] Blueprint built: %s", blueprint.model_dump(exclude_none=True))
        response_text = _format_completion_message_short(blueprint)
        next_state = ConversationState.COMPLETE
        await websocket.send_json({"type": "stream", "content": response_text, "done": False})

    else:
        next_state = ConversationState.CLARIFYING
        blueprint = None

        # Stream LLM response
        try:
            llm = get_llm_client()
            history = await supabase_service.get_conversation_turns(session_id, limit=10)

            logger.info("[CHAT] Requesting LLM clarification — missing=%s  turn=%d",
                        completeness.missing_elements, turns_count)
            prompt = get_clarification_prompt(
                missing_elements=completeness.missing_elements,
                current_attributes=merged_attrs,
                conversation_history=[
                    {"role": t["role"], "content": t["content"]}
                    for t in history
                ],
                turn_number=turns_count,
            )

            response_text = ""
            async for chunk in llm.stream(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=1500,
            ):
                response_text += chunk
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk,
                    "done": False,
                })

        except Exception as e:
            logger.exception("LLM streaming failed for session %s", session_id)
            response_text = "Cần thêm thông tin. Hãy mô tả thêm về nghiên cứu của bạn."
            await _send_error(websocket, f"LLM error: {e}")

    # Save assistant response
    await supabase_service.add_conversation_turn(
        session_id=session_id,
        role="assistant",
        content=response_text,
    )

    # Update session
    # NOTE: Do NOT set status=abstract_ready here — that only happens in abstract.py
    # after the abstract is actually generated.
    session_updates = {
        "conversation_state": next_state.value,
        "extracted_attributes": merged_attrs.model_dump(),
    }

    if blueprint:
        session_updates["blueprint"] = blueprint.model_dump()

    logger.info("[CHAT] Updating session %s: state=%s  has_blueprint=%s",
                session_id, next_state.value, bool(blueprint))
    await supabase_service.update_research_session(session_id, session_updates)

    # Send final state
    next_action = "generate_abstract" if completeness.is_complete else "continue"
    logger.info("[CHAT] ─── Done. next_action=%s  state=%s  blueprint=%s ───",
                next_action, next_state.value, bool(blueprint))
    await websocket.send_json({
        "type": "stream",
        "content": "",
        "done": True,
        "state": next_state.value,
        "blueprint": blueprint.model_dump() if blueprint else None,
        "missing_elements": completeness.missing_elements,
        "next_action": next_action,
    })


def _format_completion_message_short(blueprint) -> str:
    """Format checkpoint-1 summary message in natural Vietnamese."""
    design_display = blueprint.design_type.value.replace("_", " ").title()
    return (
        f"Được rồi, mình tổng hợp lại:\n\n"
        f"Bạn muốn nghiên cứu về **{blueprint.intervention_or_exposure}** "
        f"trên **{blueprint.population}** (n = {blueprint.sample_size}), "
        f"thiết kế **{design_display}**, "
        f"đo lường bằng **{blueprint.primary_outcome}**.\n\n"
        f"Hướng này ổn rồi — mình tạo Abstract ước tính và kiểm tra độ mới nhé? "
        f"Nếu cần chỉnh gì, nói mình biết."
    )
