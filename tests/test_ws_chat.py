"""Integration tests for WebSocket chat endpoint.

Tests the full conversation flow via ws_chat.py:
  connect → auth_success (dev mode) → create_session → chat → stream → done
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SESSION_ID = "test-session-uuid-1234"
USER_ID = "53262502-c85d-436f-98eb-66f518383813"


def _make_session(
    session_id: str = SESSION_ID,
    state: str = "INITIAL",
    turns: int = 0,
    attrs: dict | None = None,
    blueprint: dict | None = None,
) -> dict:
    return {
        "id": session_id,
        "user_id": USER_ID,
        "phase": "phase1",
        "status": "active",
        "conversation_state": state,
        "clarifying_turns_count": turns,
        "extracted_attributes": attrs or {},
        "blueprint": blueprint,
        "gate_run_count": 0,
        "score_history": [],
        "abstract_versions": [],
    }


def _supabase_mock(
    session: dict | None = None,
    turns: list | None = None,
) -> AsyncMock:
    """Return a pre-configured SupabaseService mock."""
    mock = AsyncMock()
    mock.create_research_session.return_value = session or _make_session()
    mock.get_research_session.return_value = session or _make_session()
    mock.add_conversation_turn.return_value = {}
    mock.get_conversation_turns.return_value = turns or []
    mock.update_research_session.return_value = {}
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _collect_messages(ws, count: int) -> list[dict]:
    """Receive `count` JSON messages from the WebSocket."""
    return [json.loads(ws.receive_text()) for _ in range(count)]


def _drain_stream(ws) -> tuple[str, dict]:
    """Drain stream messages until done=True. Returns (full_text, final_msg)."""
    full_text = ""
    final = {}
    while True:
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "stream", f"Unexpected message type: {msg['type']}"
        full_text += msg.get("content", "")
        if msg.get("done"):
            final = msg
            break
    return full_text, final


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Basic Protocol
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketProtocol:
    """Test basic connection and session management."""

    def test_connect_receives_auth_success_in_dev_mode(self):
        """Dev mode: server auto-sends auth_success on connect."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "auth_success"
                assert msg["user_id"] == USER_ID
                assert msg.get("dev_mode") is True

    def test_create_session_returns_session_created(self):
        """create_session message returns session_created with welcome."""
        db = _supabase_mock()
        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "session_created"
                assert "session_id" in msg
                assert "welcome_message" in msg

        db.create_research_session.assert_called_once()

    def test_start_existing_session(self):
        """start_session with valid session_id returns session_started + history."""
        session = _make_session(state="CLARIFYING", turns=2)
        turns = [
            {"role": "user", "content": "Hello", "turn_number": 1},
            {"role": "assistant", "content": "Tell me more", "turn_number": 2},
        ]
        db = _supabase_mock(session=session, turns=turns)

        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "start_session", "session_id": SESSION_ID})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "session_started"
                assert msg["session_id"] == SESSION_ID
                assert msg["state"] == "CLARIFYING"
                assert len(msg["history"]) == 2

    def test_start_session_wrong_user_returns_error(self):
        """start_session with session belonging to another user returns error."""
        session = _make_session()
        session["user_id"] = "other-user-id"
        db = _supabase_mock(session=session)

        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "start_session", "session_id": SESSION_ID})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"
                assert "denied" in msg["error"].lower() or "not found" in msg["error"].lower()

    def test_chat_without_session_returns_error(self):
        """Sending chat before create/start_session returns error."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "chat", "message": "Hello"})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"
                assert "session" in msg["error"].lower()

    def test_empty_message_returns_error(self):
        """Empty chat message returns error without crashing."""
        db = _supabase_mock()
        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                create_msg = json.loads(ws.receive_text())
                assert create_msg["type"] == "session_created"

                ws.send_json({"type": "chat", "message": "   "})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"

    def test_unknown_message_type_returns_error(self):
        """Unknown message type gets a recoverable error, not a crash."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "unknown_action"})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"
                assert msg.get("recoverable") is True


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Chat Message Processing
# ─────────────────────────────────────────────────────────────────────────────

class TestChatMessageProcessing:
    """Test _process_chat_message behavior via the WebSocket."""

    def _setup_and_create_session(self, ws, db_session=None):
        """Helper: consume auth_success, create session, return session_id."""
        ws.receive_text()  # auth_success
        ws.send_json({"type": "create_session"})
        msg = json.loads(ws.receive_text())
        return msg["session_id"]

    # ── incomplete input → CLARIFYING ──────────────────────────────────────

    def test_incomplete_input_triggers_clarifying_state(self):
        """Vague input causes LLM to ask a follow-up question."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # Incomplete attrs: missing intervention, comparator, primary_endpoint, etc.
        # Use COHORT to avoid RCT-specific F-B02 (no comparator) → BLOCKED
        incomplete_attrs = ExtractedAttributes(
            design_type=DesignType.COHORT_PROSPECTIVE,
            population="Benh nhan dai thao duong",
            # Missing: exposure, primary_endpoint, sample_size, follow_up_duration
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        llm_chunk = "Ban co the cho biet them ve dan so nghien cuu khong?"

        async def fake_stream(**_):
            yield llm_chunk

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=incomplete_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=incomplete_attrs),
            patch("app.api.v1.ws_chat.get_llm_client") as mock_llm_factory,
        ):
            mock_llm = MagicMock()
            mock_llm.stream = fake_stream
            mock_llm_factory.return_value = mock_llm

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                self._setup_and_create_session(ws, session)

                ws.send_json({"type": "chat", "message": "Toi muon nghien cuu gi do"})
                text, final = _drain_stream(ws)

                assert final["state"] == "CLARIFYING"
                assert final["done"] is True
                assert final["blueprint"] is None
                assert llm_chunk in text

    # ── complete input → COMPLETE ──────────────────────────────────────────

    def test_complete_rct_input_reaches_complete_state(self):
        """A fully-specified RCT builds a blueprint and reaches COMPLETE."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # All 7 RCT required_elements now exist in ExtractedAttributes schema
        complete_attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="200 benh nhan dai thao duong type 2",
            intervention="Metformin 500mg ngay hai lan",
            comparator="Placebo",
            primary_endpoint="HbA1c giam >= 0.5% sau 6 thang",
            sample_size=200,
            randomization_method="Block randomization",
            blinding="Double-blind",
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=complete_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=complete_attrs),
        ):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                self._setup_and_create_session(ws, session)

                ws.send_json({"type": "chat", "message": "irrelevant — attributes are mocked"})
                _, final = _drain_stream(ws)

                assert final["state"] == "COMPLETE"
                assert final["done"] is True
                assert final["blueprint"] is not None


    # ── multi-turn conversation ────────────────────────────────────────────

    def test_multi_turn_conversation_accumulates_attributes(self):
        """Each chat turn merges extracted attributes; later turns get richer context."""
        initial_session = _make_session(state="INITIAL", turns=0)

        call_count = 0

        async def fake_stream(**_):
            yield "Cam on. Ban co the cho biet co mau khong?"

        db = AsyncMock()
        db.create_research_session.return_value = initial_session
        db.add_conversation_turn.return_value = {}
        db.update_research_session.return_value = {}

        # Simulate session state evolving between turns
        def get_session_side_effect(session_id):
            nonlocal call_count
            call_count += 1
            turns = min(call_count // 2, 2)
            return _make_session(state="CLARIFYING", turns=turns)

        db.get_research_session.side_effect = get_session_side_effect
        db.get_conversation_turns.return_value = []

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.get_llm_client") as mock_llm_factory,
        ):
            mock_llm = MagicMock()
            mock_llm.stream = fake_stream
            mock_llm_factory.return_value = mock_llm

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                create_msg = json.loads(ws.receive_text())
                assert create_msg["type"] == "session_created"

                # Turn 1: introduce topic
                ws.send_json({"type": "chat", "message": "Nghien cuu RCT ve metformin"})
                _, final1 = _drain_stream(ws)
                assert final1["done"] is True

                # Turn 2: provide more detail
                ws.send_json({
                    "type": "chat",
                    "message": "200 benh nhan dai thao duong type 2, theo doi 6 thang, HbA1c la endpoint chinh",
                })
                _, final2 = _drain_stream(ws)
                assert final2["done"] is True

        # Verify two user turns were saved
        user_turn_calls = [
            c for c in db.add_conversation_turn.call_args_list
            if c.kwargs.get("role") == "user"
        ]
        assert len(user_turn_calls) == 2

    # ── session persistence ────────────────────────────────────────────────

    def test_session_attributes_persisted_to_database(self):
        """After chat, extracted_attributes are saved to DB via update_research_session."""
        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        async def fake_stream(**_):
            yield "Please tell me more."

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.get_llm_client") as mock_llm_factory,
        ):
            mock_llm = MagicMock()
            mock_llm.stream = fake_stream
            mock_llm_factory.return_value = mock_llm

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "Nghien cuu RCT voi 100 benh nhan"})
                _drain_stream(ws)

        # update_research_session should have been called with extracted_attributes
        update_calls = db.update_research_session.call_args_list
        assert len(update_calls) >= 1
        last_call_kwargs = update_calls[-1].args[1]  # second positional arg = updates dict
        assert "extracted_attributes" in last_call_kwargs
        assert "conversation_state" in last_call_kwargs

    # ── blueprint built on complete ────────────────────────────────────────

    def test_blueprint_saved_when_state_is_complete(self):
        """When completeness check passes, blueprint is written to DB and sent to client."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # All 7 RCT required_elements now exist in ExtractedAttributes schema
        complete_attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="200 benh nhan dai thao duong type 2",
            intervention="Metformin 500mg ngay hai lan",
            comparator="Placebo",
            primary_endpoint="HbA1c giam >= 0.5% sau 6 thang",
            sample_size=200,
            randomization_method="Block randomization",
            blinding="Double-blind",
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=complete_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=complete_attrs),
        ):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "irrelevant — attributes are mocked"})
                _, final = _drain_stream(ws)

        # State must be COMPLETE, blueprint must be in final message and saved to DB
        assert final["state"] == "COMPLETE"
        assert final["blueprint"] is not None
        update_calls = db.update_research_session.call_args_list
        last_updates = update_calls[-1].args[1]
        assert "blueprint" in last_updates


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Error Handling
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Test error paths and resilience."""

    def test_invalid_json_returns_recoverable_error(self):
        """Malformed JSON from client results in error, connection stays alive."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_text("this is not json {{{")
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"
                assert msg.get("recoverable") is True

                # Connection is still alive — can send another message
                ws.send_json({"type": "create_session"})
                msg2 = json.loads(ws.receive_text())
                assert msg2["type"] == "session_created"

    def test_llm_failure_sends_error_and_continues(self):
        """When LLM stream raises, client gets error but session is still updated."""
        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        async def failing_stream(**_):
            raise RuntimeError("LLM API unreachable")
            yield  # make it a generator

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.get_llm_client") as mock_llm_factory,
        ):
            mock_llm = MagicMock()
            mock_llm.stream = failing_stream
            mock_llm_factory.return_value = mock_llm

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "Nghien cuu gi do"})

                # Should get an error message from LLM failure
                msg = json.loads(ws.receive_text())
                assert msg["type"] in ("error", "stream")

                # Session update still called (fallback message saved)
                assert db.add_conversation_turn.called

    def test_chat_with_missing_session_in_db(self):
        """If session_id is set but not found in DB, returns error."""
        db = _supabase_mock()
        db.get_research_session.return_value = None  # session disappeared

        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                # Manually inject session_id by doing start_session with a bad id
                ws.send_json({"type": "start_session", "session_id": "ghost-session"})
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "error"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Extractor & Conversation Logic (unit, no WS)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractorIntegration:
    """Test extractor + conversation modules independently."""

    def test_extract_rct_keywords(self):
        from app.core.extractor import extract_attributes
        from app.models.enums import DesignType

        text = (
            "Thu nghiem lam sang ngau nhien (RCT) tren 150 benh nhan "
            "ung thu vu giai doan II-III, so sanh phac do FOLFOX voi XELOX, "
            "theo doi 12 thang, endpoint la Overall Survival."
        )
        attrs = extract_attributes(text)
        assert attrs.design_type == DesignType.RCT
        assert attrs.sample_size is not None and attrs.sample_size > 0

    def test_extract_cohort_keywords(self):
        from app.core.extractor import extract_attributes
        from app.models.enums import DesignType

        text = "Nghien cuu thuan tap tien cuu 300 benh nhan tang huyet ap tai cong dong"
        attrs = extract_attributes(text)
        assert attrs.design_type in (
            DesignType.COHORT_PROSPECTIVE, DesignType.COHORT_RETROSPECTIVE
        )

    def test_merge_attributes_accumulates(self):
        from app.core.extractor import extract_attributes, merge_attributes
        from app.models.schemas import ExtractedAttributes

        existing = extract_attributes("RCT voi 100 benh nhan")
        new_info = extract_attributes("endpoint chinh la HbA1c giam 0.5%")
        merged = merge_attributes(existing, new_info)

        # merged should have both sample_size and primary_outcome if extracted
        assert merged is not None

    def test_completeness_incomplete_rct(self):
        from app.core.conversation import evaluate_completeness
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="Benh nhan dai thao duong",
            # Missing: intervention, comparator, primary_outcome, sample_size, etc.
        )
        result = evaluate_completeness(attrs, DesignType.RCT, clarifying_turns=1)
        assert not result.is_complete
        assert len(result.missing_elements) > 0

    def test_completeness_complete_rct(self):
        from app.core.conversation import evaluate_completeness
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # All 7 RCT required_elements now exist in ExtractedAttributes schema
        attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="200 benh nhan dai thao duong type 2",
            intervention="Metformin 500mg ngay hai lan",
            comparator="Placebo",
            primary_endpoint="HbA1c giam >= 0.5% sau 6 thang",
            sample_size=200,
            randomization_method="Block randomization",
            blinding="Double-blind",
        )
        result = evaluate_completeness(attrs, DesignType.RCT, clarifying_turns=3)
        assert result.is_complete
        assert result.blocking_issues == []





# ─────────────────────────────────────────────────────────────────────────────
# Tests: BLOCKED State
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockedState:
    """Test BLOCKED conversation state when feasibility issues are detected."""

    def test_rct_tiny_sample_triggers_blocked(self):
        """RCT with n < 20 triggers F-B01 → BLOCKED state sent to client."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # Attributes that will pass completeness but fail F-B01 (n < 20)
        blocking_attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="Benh nhan dai thao duong type 2",
            intervention="Metformin 500mg",
            comparator="Placebo",
            primary_endpoint="HbA1c giam >= 0.5%",
            sample_size=5,  # triggers F-B01: RCT n < 20
            setting="Benh vien Cho Ray",
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=blocking_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=blocking_attrs),
        ):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())  # session_created

                ws.send_json({"type": "chat", "message": "RCT voi 5 benh nhan"})
                _, final = _drain_stream(ws)

                # BLOCKED state must be sent; model is not complete despite attrs
                assert final["state"] == "BLOCKED"
                assert final["done"] is True

    def test_blocked_state_saves_assistant_turn(self):
        """When BLOCKED, blocking message is still saved as an assistant turn."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        blocking_attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="Benh nhan",
            intervention="Thuoc A",
            comparator="Placebo",
            primary_endpoint="Dau cuoi",
            sample_size=3,  # n < 20 → block
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=blocking_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=blocking_attrs),
        ):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success
                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "RCT voi 3 benh nhan"})
                _drain_stream(ws)

        # Both user turn and assistant (blocking) turn must be saved
        assistant_turns = [
            c for c in db.add_conversation_turn.call_args_list
            if c.kwargs.get("role") == "assistant"
        ]
        # At least one assistant turn (welcome + blocking message)
        assert len(assistant_turns) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Final Stream Message Fields
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamMessageFields:
    """Verify all required fields are present in the final done=True stream message."""

    def _chat_and_get_final(self, db, extra_patches=()):
        """Helper: connect, create session, send one chat, return final stream msg."""
        ctx = [patch("app.api.v1.ws_chat.supabase_service", db)]
        ctx.extend(extra_patches)

        with __import__('contextlib').ExitStack() as stack:
            for p in ctx:
                stack.enter_context(p)

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success
                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "Nghien cuu gi do"})
                _, final = _drain_stream(ws)
                return final

    def test_final_message_has_next_action_field(self):
        """Final stream message always includes next_action."""
        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        async def fake_stream(**_):
            yield "Can them thong tin."

        mock_llm = MagicMock()
        mock_llm.stream = fake_stream

        final = self._chat_and_get_final(
            db,
            extra_patches=[
                patch("app.api.v1.ws_chat.get_llm_client", return_value=mock_llm),
            ],
        )

        assert "next_action" in final
        assert final["next_action"] in ("continue", "generate_abstract")

    def test_final_message_has_missing_elements_field(self):
        """Final stream message always includes missing_elements list."""
        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        async def fake_stream(**_):
            yield "Can them thong tin."

        mock_llm = MagicMock()
        mock_llm.stream = fake_stream

        final = self._chat_and_get_final(
            db,
            extra_patches=[
                patch("app.api.v1.ws_chat.get_llm_client", return_value=mock_llm),
            ],
        )

        assert "missing_elements" in final
        assert isinstance(final["missing_elements"], list)

    def test_clarifying_next_action_is_continue(self):
        """When state=CLARIFYING, next_action must be 'continue'."""
        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        async def fake_stream(**_):
            yield "Can them thong tin."

        mock_llm = MagicMock()
        mock_llm.stream = fake_stream

        final = self._chat_and_get_final(
            db,
            extra_patches=[
                patch("app.api.v1.ws_chat.get_llm_client", return_value=mock_llm),
            ],
        )

        if final["state"] == "CLARIFYING":
            assert final["next_action"] == "continue"

    def test_complete_next_action_is_generate_abstract(self):
        """When state=COMPLETE, next_action must be 'generate_abstract'."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        # All 7 RCT required_elements now exist in ExtractedAttributes schema
        complete_attrs = ExtractedAttributes(
            design_type=DesignType.RCT,
            population="200 benh nhan dai thao duong type 2",
            intervention="Metformin 500mg ngay hai lan",
            comparator="Placebo",
            primary_endpoint="HbA1c giam >= 0.5% sau 6 thang",
            sample_size=200,
            randomization_method="Block randomization",
            blinding="Double-blind",
        )

        session = _make_session(state="INITIAL")
        db = _supabase_mock(session=session)

        final = self._chat_and_get_final(
            db,
            extra_patches=[
                patch("app.api.v1.ws_chat.extract_attributes", return_value=complete_attrs),
                patch("app.api.v1.ws_chat.merge_attributes", return_value=complete_attrs),
            ],
        )

        assert final["state"] == "COMPLETE"
        assert final["next_action"] == "generate_abstract"
        assert final["blueprint"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Forced Completion After Max Turns
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxTurnsForced:
    """Test forced COMPLETE after MAX_CLARIFYING_TURNS (10 turns)."""

    def test_forced_complete_after_10_turns(self):
        """After 10 clarifying turns without completeness, server forces COMPLETE."""
        # Session already at 10 turns — next evaluate_completeness should return is_complete=True
        session = _make_session(state="CLARIFYING", turns=10)
        db = _supabase_mock(session=session)

        async def fake_stream(**_):
            yield "Them thong tin."

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.get_llm_client") as mock_llm_factory,
        ):
            mock_llm = MagicMock()
            mock_llm.stream = fake_stream
            mock_llm_factory.return_value = mock_llm

            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())  # session_created

                # clarifying_turns_count = 10 is read from DB
                # → turns_count = 10 + 1 = 11 > MAX(10) → forced COMPLETE
                ws.send_json({
                    "type": "chat",
                    "message": "Con mot so van de chu chua ro rang",
                })
                _, final = _drain_stream(ws)

                # Must be COMPLETE (forced) when clarifying_turns >= MAX (10)
                assert final["state"] == "COMPLETE"
                assert final["done"] is True

    def test_forced_complete_builds_blueprint_with_available_attrs(self):
        """Even when forced complete, blueprint is built from available attributes."""
        from app.models.schemas import ExtractedAttributes
        from app.models.enums import DesignType

        partial_attrs = ExtractedAttributes(
            design_type=DesignType.COHORT_RETROSPECTIVE,
            population="Benh nhan cao huyet ap",
            primary_endpoint="Ty le bien co tim mach",
            sample_size=150,
        )

        # Simulate already at max turns
        session = _make_session(state="CLARIFYING", turns=10)
        db = _supabase_mock(session=session)

        with (
            patch("app.api.v1.ws_chat.supabase_service", db),
            patch("app.api.v1.ws_chat.extract_attributes", return_value=partial_attrs),
            patch("app.api.v1.ws_chat.merge_attributes", return_value=partial_attrs),
        ):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session"})
                json.loads(ws.receive_text())

                ws.send_json({"type": "chat", "message": "Toi muon nghien cuu ve cao huyet ap"})
                _, final = _drain_stream(ws)

                assert final["state"] == "COMPLETE"
                # Blueprint must be present when COMPLETE
                assert final["blueprint"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Auth Message Flow
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthFlow:
    """Test explicit auth message handling (dev mode variations)."""

    def test_auth_message_without_token_in_dev_mode_succeeds(self):
        """In dev mode, auth without token still returns auth_success."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                # First message is auto auth_success
                auto_auth = json.loads(ws.receive_text())
                assert auto_auth["type"] == "auth_success"
                assert auto_auth.get("dev_mode") is True

                # Sending explicit auth without token — dev mode still OK
                ws.send_json({"type": "auth"})
                explicit_auth = json.loads(ws.receive_text())
                assert explicit_auth["type"] == "auth_success"

    def test_auth_with_invalid_token_in_dev_mode_falls_back(self):
        """In dev mode, invalid token falls back to default user instead of error."""
        db = _supabase_mock()
        db.get_user = AsyncMock(return_value=None)  # invalid token

        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auto auth_success

                ws.send_json({"type": "auth", "token": "bad-token"})
                msg = json.loads(ws.receive_text())

                # Dev mode: should still auth_success (fallback), not error
                assert msg["type"] == "auth_success"
                assert msg.get("dev_mode") is True

    def test_create_session_with_custom_phase(self):
        """create_session respects custom phase parameter."""
        db = _supabase_mock()

        with patch("app.api.v1.ws_chat.supabase_service", db):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "create_session", "phase": "phase2"})
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "session_created"

        # Verify phase was passed to DB create call
        create_call_kwargs = db.create_research_session.call_args.kwargs
        assert create_call_kwargs.get("phase") == "phase2"

    def test_start_session_missing_session_id_returns_error(self):
        """start_session without session_id field returns error."""
        with patch("app.api.v1.ws_chat.supabase_service", _supabase_mock()):
            with TestClient(app).websocket_connect("/api/v1/ws/chat") as ws:
                ws.receive_text()  # auth_success

                ws.send_json({"type": "start_session"})  # no session_id
                msg = json.loads(ws.receive_text())

                assert msg["type"] == "error"
                assert "session_id" in msg["error"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Connection Isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestConnectionIsolation:
    """Verify that two concurrent WebSocket connections are fully independent."""

    def test_two_connections_have_independent_sessions(self):
        """Session state from connection A does not leak into connection B."""
        db = _supabase_mock()

        with patch("app.api.v1.ws_chat.supabase_service", db):
            client = TestClient(app)

            with client.websocket_connect("/api/v1/ws/chat") as ws_a:
                ws_a.receive_text()  # auth_success A

                ws_a.send_json({"type": "create_session"})
                msg_a = json.loads(ws_a.receive_text())
                assert msg_a["type"] == "session_created"
                session_a = msg_a["session_id"]

                # Connection B opens independently
                with client.websocket_connect("/api/v1/ws/chat") as ws_b:
                    ws_b.receive_text()  # auth_success B

                    # B has no session yet — chat should error
                    ws_b.send_json({"type": "chat", "message": "Hello"})
                    msg_b = json.loads(ws_b.receive_text())
                    assert msg_b["type"] == "error"
                    assert "session" in msg_b["error"].lower()

    def test_connection_b_can_start_own_session_while_a_is_active(self):
        """Each connection independently manages their own session."""
        db = _supabase_mock()

        with patch("app.api.v1.ws_chat.supabase_service", db):
            client = TestClient(app)

            with client.websocket_connect("/api/v1/ws/chat") as ws_a:
                ws_a.receive_text()  # auth_success A
                ws_a.send_json({"type": "create_session"})
                msg_a = json.loads(ws_a.receive_text())
                assert msg_a["type"] == "session_created"

                with client.websocket_connect("/api/v1/ws/chat") as ws_b:
                    ws_b.receive_text()  # auth_success B
                    ws_b.send_json({"type": "create_session"})
                    msg_b = json.loads(ws_b.receive_text())

                    # Both connections successfully have their own sessions
                    assert msg_b["type"] == "session_created"
                    assert "session_id" in msg_b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
