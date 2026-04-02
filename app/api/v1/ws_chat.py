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
from app.models.enums import ConversationState, SessionStatus, DesignType
from app.llm import get_llm_client
from app.llm.prompts.clarify import get_clarification_prompt, SYSTEM_PROMPT
from app.domain.extraction.field_validator import validate_field_answer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Default user for development (bypass auth)
DEFAULT_USER_ID = "53262502-c85d-436f-98eb-66f518383813"  # admin@avr.com
DEV_MODE = True  # Set to False in production

# In-memory per-field attempt tracking: session_id -> {field_name -> attempt_count}
# Cleared when session reaches COMPLETE or BLOCKED state.
_field_attempt_counts: dict[str, dict[str, int]] = {}


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
                
                # Evaluate missing elements for form recovery
                existing_attrs = ExtractedAttributes()
                if session.get("extracted_attributes"):
                    try:
                        existing_attrs = ExtractedAttributes(**session["extracted_attributes"])
                    except Exception:
                        pass
                completeness = evaluate_completeness(existing_attrs)

                # Prepare dynamic form for initial state if needed
                dynamic_form = []
                if completeness.missing_elements:
                    # A static dictionary for better fallback UI
                    FALLBACK_LABELS = {
                        "population": "Đối tượng nghiên cứu", "sample_size": "Cỡ mẫu", "primary_endpoint": "Kết cục chính",
                        "intervention": "Can thiệp", "comparator": "Nhóm chứng", "exposure": "Phơi nhiễm",
                        "follow_up_duration": "Thời gian theo dõi", "reference_standard": "Tiêu chuẩn vàng",
                        "search_strategy": "Chiến lược tìm kiếm", "databases": "Cơ sở dữ liệu", "case_definition": "Định nghĩa ca bệnh",
                        "control_definition": "Định nghĩa nhóm chứng", "matching_criteria": "Tiêu chí ghép cặp",
                        "inclusion_criteria": "Tiêu chuẩn chọn", "exclusion_criteria": "Tiêu chuẩn loại",
                        "randomization_method": "Phương pháp ngẫu nhiên", "blinding": "Làm mù",
                    }
                    FALLBACK_DESC = {
                        "population": "Đối tượng bạn cần nghiên cứu là gì? (Ví dụ: Trẻ em từ bao nhiêu tuổi, người lớn từ bao nhiêu tuổi, có phân biệt giới tính hay mắc bệnh nền không...)",
                        "sample_size": "Cỡ mẫu dự kiến bao nhiêu bệnh nhân? (Ví dụ: Khoảng 100-200 bệnh nhân, hoặc lấy mẫu toàn bộ dự kiến được 50 ca...)",
                        "primary_endpoint": "Kết cục chính để đánh giá là gì? (Ví dụ: Tỷ lệ tử vong sau 30 ngày, mức độ giảm đau sau 1 giờ, thời gian nằm viện...)",
                        "intervention": "Can thiệp hoặc phương pháp điều trị bạn áp dụng là gì? (Ví dụ: Dùng thuốc A liều lượng B, hoặc phẫu thuật thủ thuật C...)",
                        "comparator": "Nhóm chứng để đánh giá so sánh là gì? (Ví dụ: Phác đồ chuẩn, dùng thuốc giả dược (Placebo), hay không can thiệp...)",
                        "exposure": "Nhóm yếu tố nguy cơ/phơi nhiễm bạn muốn đánh giá là gì? (Ví dụ: Tiếp xúc khói thuốc, làm việc ở hầm mỏ...)",
                        "follow_up_duration": "Bạn dự kiến thời gian theo dõi bệnh nhân là bao lâu? (Ví dụ: Theo dõi 6 tháng, 1 năm, hoặc đến khi xuất viện...)",
                        "reference_standard": "Tiêu chuẩn vàng để đem ra so sánh với Test của bạn là gì? (Ví dụ: Kết quả giải phẫu bệnh, PCR...)",
                        "search_strategy": "Chiến lược tìm kiếm tài liệu của bạn là gì? Có từ khóa (Keywords) cụ thể nào không?",
                        "databases": "Bạn dự kiến sẽ lục tìm tài liệu trên nền tảng cơ sở dữ liệu nào? (Ví dụ: PubMed, Embase, Cochrane...)",
                        "case_definition": "Định nghĩa chính xác như thế nào thì được tính là 'ca bệnh' trong đề cương của bạn?",
                        "control_definition": "Định nghĩa như thế nào thì được gọi là 'nhóm chứng' (ng khỏe/ko mắc bệnh) trong đề cương của bạn?",
                        "matching_criteria": "Nếu bạn có ý định ghép cặp, bạn tính ghép theo tiêu chí nào? (Ví dụ: Cứ 1 bệnh nhân thì ghép 1 người khỏe có cùng tuổi và giới tính...)",
                        "inclusion_criteria": "Đâu là những tiêu chuẩn chọn chính để đưa bệnh nhân vào nghiên cứu?",
                        "exclusion_criteria": "Trường hợp nào dù thỏa mãn tiêu chuẩn chọn nhưng bạn sẽ chủ động loại trừ khỏi nghiên cứu?",
                        "randomization_method": "Chiến lược phân bổ ngẫu nhiên bạn hướng đến là gì? (Ví dụ: Simple, Blocked, máy tính...)",
                        "blinding": "Dự kiến thiết kế làm mù như thế nào? (Ví dụ: Mù đơn - bệnh nhân không biết, mù đôi - cả BS lẫn BN đều không biết...)"
                    }
                    
                    dynamic_form = [{
                        "attribute_name": m, 
                        "question_label": FALLBACK_LABELS.get(m, m.replace("_", " ").title()), 
                        "description": FALLBACK_DESC.get(m, "Hãy mô tả chi tiết thông tin cho phần này."), 
                        "placeholder": ""
                    } for m in completeness.missing_elements]

                # Always append the optional notes field
                if dynamic_form is not None and isinstance(dynamic_form, list):
                    dynamic_form.append({
                        "attribute_name": "additional_notes",
                        "question_label": "Thông tin bổ sung (Không bắt buộc)",
                        "description": "Bạn có muốn bổ sung thêm context nào khác không? (Ví dụ: 'Tôi muốn làm tại Bệnh viện Bạch Mai' hoặc 'Nghiên cứu kéo dài 2 năm').",
                        "placeholder": "VD: Địa điểm nghiên cứu, giới hạn kinh phí..."
                    })

                await websocket.send_json({
                    "type": "session_started",
                    "session_id": session_id,
                    "state": session.get("conversation_state"),
                    "history": turns,
                    "missing_elements": completeness.missing_elements,
                    "dynamic_form": dynamic_form,
                })
                continue

            # Handle chat message
            if msg_type == "chat":
                if not session_id:
                    await _send_error(websocket, "No session active")
                    continue

                user_message = message.get("message", "").strip()
                form_data = message.get("form_data", None)
                
                if not user_message and not form_data:
                    await _send_error(websocket, "Empty message and no form data")
                    continue

                logger.info("Processing chat: session_id=%s message_len=%d form_data=%s", session_id, len(user_message), bool(form_data))
                # Process the message
                await _process_chat_message(
                    websocket=websocket,
                    session_id=session_id,
                    user_message=user_message,
                    form_data=form_data,
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
    form_data: dict = None,
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

    logger.info("─── [CHAT] session=%s | message=%r | form_data=%s", session_id, user_message[:300], bool(form_data))
    logger.info("[CHAT] existing_attrs before extraction: %s",
                existing_attrs.model_dump(exclude_none=True) if existing_attrs else "None")

    new_attrs = extract_attributes(user_message, existing_attrs) if user_message else ExtractedAttributes()
    
    if form_data:
        for key, value in form_data.items():
            if hasattr(new_attrs, key) and value is not None and value.strip():
                # Smart merging: if existing already has string value, append it to preserve context.
                old_val = getattr(existing_attrs or ExtractedAttributes(), key)
                if old_val and isinstance(old_val, str) and not isinstance(old_val, DesignType):
                    # Only append if value isn't already in old_val
                    if value.lower() not in old_val.lower():
                        setattr(new_attrs, key, f"{old_val}, {value}")
                else:
                    setattr(new_attrs, key, value)
                
    merged_attrs = merge_attributes(existing_attrs or ExtractedAttributes(), new_attrs)

    # --- Per-field answer validation ---
    # Categorise each submitted form field: confirmed (clear) vs uncertain (vague).
    # Uncertain fields on their 1st attempt are cleared from merged_attrs so
    # evaluate_completeness still marks them as missing and re-asks.
    # On the 2nd+ attempt the field is force-accepted regardless of quality.
    newly_confirmed: list[str] = []
    newly_uncertain: list[tuple[str, str, str]] = []  # (field, raw_value, reason)

    if form_data:
        submitted = {
            k: v.strip()
            for k, v in form_data.items()
            if k != "additional_notes" and v and v.strip()
        }
        session_counts = _field_attempt_counts.setdefault(session_id, {})
        for field, value in submitted.items():
            session_counts[field] = session_counts.get(field, 0) + 1
            confidence, reason = validate_field_answer(field, value)
            if confidence == "confirmed" or session_counts[field] >= 2:
                newly_confirmed.append(field)
            else:
                newly_uncertain.append((field, value, reason or "Câu trả lời chưa rõ ràng."))
                # Clear from merged_attrs so completeness flags it as still missing
                if hasattr(merged_attrs, field):
                    try:
                        setattr(merged_attrs, field, None)
                    except Exception:
                        pass

    logger.info("[CHAT] merged_attrs after extraction: %s",
                merged_attrs.model_dump(exclude_none=True))
    if newly_confirmed:
        logger.info("[CHAT] newly_confirmed fields: %s", newly_confirmed)
    if newly_uncertain:
        logger.info("[CHAT] newly_uncertain fields: %s", [(f, v) for f, v, _ in newly_uncertain])

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
    dynamic_form: list[dict] = []  # always defined so done message can reference it

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

        if completeness.missing_elements:
            # Build accepted/uncertain context dicts for the LLM prompt
            accepted_fields_ctx = {
                f: str(getattr(merged_attrs, f, "") or "")
                for f in newly_confirmed
                if getattr(merged_attrs, f, None)
            }
            try:
                llm = get_llm_client()
                history_turns = await supabase_service.get_conversation_turns(session_id, limit=6)

                prompt = get_clarification_prompt(
                    missing_elements=completeness.missing_elements,
                    current_attributes=merged_attrs,
                    conversation_history=[{"role": t["role"], "content": t["content"]} for t in history_turns],
                    turn_number=turns_count,
                    accepted_fields=accepted_fields_ctx or None,
                    uncertain_fields=newly_uncertain or None,
                )

                response = await llm.complete(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=1500,
                )

                content = response.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()

                import json
                data = json.loads(content)
                response_text = data.get("message", "Vui lòng hoàn thiện các thông tin sau:")
                dynamic_form = data.get("form_fields", [])
            except Exception as e:
                logger.exception("LLM dynamic form generation failed")
                response_text = "Để hoàn thiện thiết kế nghiên cứu, bạn vui lòng điền các thông tin còn thiếu vào form bên dưới nhé:"

                FALLBACK_LABELS = {
                    "population": "Đối tượng nghiên cứu", "sample_size": "Cỡ mẫu", "primary_endpoint": "Kết cục chính",
                    "intervention": "Can thiệp", "comparator": "Nhóm chứng", "exposure": "Phơi nhiễm",
                    "follow_up_duration": "Thời gian theo dõi", "reference_standard": "Tiêu chuẩn vàng",
                    "search_strategy": "Chiến lược tìm kiếm", "databases": "Cơ sở dữ liệu", "case_definition": "Định nghĩa ca bệnh"
                }
                FALLBACK_DESC = {
                    "population": "Đối tượng bạn cần nghiên cứu là gì? (Ví dụ: Trẻ em từ bao nhiêu tuổi, người lớn từ bao nhiêu tuổi, có phân biệt giới tính hay mắc bệnh nền không...)",
                    "sample_size": "Cỡ mẫu dự kiến bao nhiêu bệnh nhân? (Ví dụ: Khoảng 100-200 bệnh nhân, hoặc lấy mẫu toàn bộ dự kiến được 50 ca...)",
                    "primary_endpoint": "Kết cục chính để đánh giá là gì? (Ví dụ: Tỷ lệ tử vong sau 30 ngày, mức độ giảm đau sau 1 giờ, thời gian nằm viện...)",
                    "intervention": "Can thiệp hoặc phương pháp điều trị bạn áp dụng là gì? (Ví dụ: Dùng thuốc A liều lượng B, hoặc phẫu thuật thủ thuật C...)",
                    "comparator": "Nhóm chứng để đánh giá so sánh là gì? (Ví dụ: Phác đồ chuẩn, dùng thuốc giả dược (Placebo), hay không can thiệp...)",
                    "exposure": "Nhóm yếu tố nguy cơ/phơi nhiễm bạn muốn đánh giá là gì? (Ví dụ: Tiếp xúc khói thuốc, làm việc ở hầm mỏ...)",
                }
                dynamic_form = [{
                    "attribute_name": m,
                    "question_label": FALLBACK_LABELS.get(m, m.replace("_", " ").title()),
                    "description": FALLBACK_DESC.get(m, "Hãy mô tả chi tiết thông tin phần này."),
                    "placeholder": ""
                } for m in completeness.missing_elements]

            # Augment retry fields with previous-answer metadata so the frontend
            # can highlight them differently from genuinely new fields.
            if newly_uncertain:
                uncertain_map = {f: (v, r) for f, v, r in newly_uncertain}
                for field_def in dynamic_form:
                    fname = field_def.get("attribute_name")
                    if fname in uncertain_map:
                        prev_val, reason = uncertain_map[fname]
                        field_def["is_retry"] = True
                        field_def["previous_value"] = prev_val
                        field_def["rejection_reason"] = reason

        # Always append the optional notes field if we are returning a form
        if dynamic_form:
            dynamic_form.append({
                "attribute_name": "additional_notes",
                "question_label": "Thông tin bổ sung (Không bắt buộc)",
                "description": "Bạn có muốn bổ sung thêm context nào khác không? (Ví dụ: 'Tôi muốn làm tại Bệnh viện Bạch Mai' hoặc 'Nghiên cứu kéo dài 2 năm').",
                "placeholder": "VD: Địa điểm nghiên cứu, định hướng riêng..."
            })
        else:
            response_text = "Cần thêm thông tin. Hãy mô tả thêm về nghiên cứu của bạn."

        await websocket.send_json({
            "type": "stream",
            "content": response_text,
            "done": False,
        })

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

    # Cleanup in-memory attempt tracking when session is no longer clarifying
    if next_state in (ConversationState.COMPLETE, ConversationState.BLOCKED):
        _field_attempt_counts.pop(session_id, None)

    # Build accepted/uncertain payloads for the frontend
    accepted_payload = (
        {f: str(getattr(merged_attrs, f, "") or "") for f in newly_confirmed if getattr(merged_attrs, f, None)}
        if newly_confirmed else None
    )
    uncertain_payload = (
        {f: {"value": v, "reason": r} for f, v, r in newly_uncertain}
        if newly_uncertain else None
    )

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
        "dynamic_form": dynamic_form,        # always send ([] when complete/blocked)
        "accepted_fields": accepted_payload,
        "uncertain_fields": uncertain_payload,
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
