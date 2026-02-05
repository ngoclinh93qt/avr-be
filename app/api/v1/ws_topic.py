"""
WebSocket endpoint for realtime Topic Analyzer with authentication.

Flow:
1. Client connects with token (query param or first message)
2. Server authenticates and checks connection limits
3. Server sends session_started
4. Client sends abstract → Server assesses completeness
5. If incomplete → Server sends clarification_needed
6. Client answers questions → Server enriches abstract
7. Server runs full analysis with progress updates
8. Server sends analysis_complete with results
9. Results are saved to Supabase for history
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.session_manager import session_manager
from app.core.ws_manager import ws_manager
from app.core.supabase_client import supabase_service
from app.models.ws_schemas import (
    AgentThinking,
    AnalysisComplete,
    AnalysisProgress,
    ClarificationNeeded,
    ClarificationQuestion,
    ErrorMessage,
    MessageType,
    SessionStarted,
)
from app.services.topic_analyzer_streaming import TopicAnalyzerStreamingService

router = APIRouter()
service = TopicAnalyzerStreamingService()


async def send_message(websocket: WebSocket, message: dict):
    """Send a message to the WebSocket client."""
    await websocket.send_json(message)


async def send_thinking(websocket: WebSocket, message: str, step: str, progress: int):
    """Send thinking status update."""
    msg = AgentThinking(message=message, step=step, progress=progress)
    await send_message(websocket, msg.model_dump())


async def send_progress(
    websocket: WebSocket,
    step: str,
    message: str,
    progress: int,
    partial_result: Optional[dict] = None,
):
    """Send analysis progress update."""
    msg = AnalysisProgress(
        step=step, message=message, progress=progress, partial_result=partial_result
    )
    await send_message(websocket, msg.model_dump())


async def send_error(
    websocket: WebSocket,
    error: str,
    details: Optional[str] = None,
    recoverable: bool = True,
):
    """Send error message."""
    msg = ErrorMessage(error=error, details=details, recoverable=recoverable)
    await send_message(websocket, msg.model_dump())


async def authenticate_websocket(
    websocket: WebSocket, token: Optional[str]
) -> Optional[dict]:
    """
    Authenticate WebSocket connection.

    Returns user dict if authenticated, None otherwise.
    """
    if not token:
        return None

    try:
        user = await supabase_service.get_user(token)
        if user:
            return {"id": user.id, "email": user.email}
    except Exception:
        pass

    return None


async def save_results_to_supabase(
    user_id: str,
    abstract: str,
    language: str,
    keywords: list[str],
    assessment: dict,
    final_result: dict,
    papers: list[dict],
):
    """Save research results to Supabase."""
    try:
        # Create research session
        session = await supabase_service.create_research_session(
            user_id=user_id,
            abstract=abstract,
            language=language,
        )

        session_id = session.get("id")
        if not session_id:
            return

        # Update session with results
        await supabase_service.update_research_session(
            session_id=session_id,
            updates={
                "status": "completed",
                "keywords": keywords,
                "assessment": assessment,
                "analysis_result": final_result,
                "total_papers_found": final_result.get("metadata", {}).get(
                    "total_found", 0
                ),
                "total_papers_ranked": len(papers),
                "avg_similarity": final_result.get("metadata", {}).get(
                    "avg_similarity", 0.0
                ),
                "processing_time_seconds": final_result.get("metadata", {}).get(
                    "processing_time_seconds", 0.0
                ),
            },
        )

        # Save papers
        if papers:
            await supabase_service.save_research_papers(
                session_id=session_id,
                papers=papers,
            )

    except Exception as e:
        print(f"Failed to save results to Supabase: {e}")


@router.websocket("/ws/topic/analyze")
async def websocket_topic_analyze(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Auth token"),
):
    """
    WebSocket endpoint for realtime topic analysis with authentication.

    Authentication:
    - Pass token as query param: /ws/topic/analyze?token=xxx
    - Or send as first message: {"type": "auth", "token": "xxx"}

    Protocol:
    - Client connects (with optional token)
    - If no token in query, client sends auth message first
    - Server: session_started (with user info if authenticated)
    - Client: user_message (with abstract)
    - Server: agent_thinking, clarification_needed (if needed)
    - Client: user_answer (for each question)
    - Server: agent_thinking, analysis_progress (multiple), analysis_complete
    """
    user: Optional[dict] = None
    session_id: Optional[str] = None
    db_session_abstract: Optional[str] = None
    db_session_language: str = "auto"
    db_session_keywords: list[str] = []
    db_session_assessment: dict = {}

    # ════════════════════════════════════════════════════════════════════════
    # Authentication Phase
    # ════════════════════════════════════════════════════════════════════════

    # Try to authenticate from query param
    if token:
        user = await authenticate_websocket(websocket, token)

    # Check connection limit for authenticated users
    if user:
        if not ws_manager.can_connect(user["id"]):
            await websocket.accept()
            await send_error(
                websocket,
                "Connection limit exceeded",
                f"Maximum {ws_manager.max_connections_per_user} concurrent connections allowed. "
                "Please close other sessions first.",
                recoverable=False,
            )
            await websocket.close(code=1008, reason="Connection limit exceeded")
            return

        # Register connection with manager
        connection = await ws_manager.connect(websocket, user["id"])
        if not connection:
            return
    else:
        # Allow unauthenticated connections (will try auth via message)
        await websocket.accept()

    try:
        # ════════════════════════════════════════════════════════════════════
        # Session Initialization
        # ════════════════════════════════════════════════════════════════════
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # Handle auth message if not yet authenticated
            if msg_type == "auth" and not user:
                auth_token = data.get("token")
                user = await authenticate_websocket(websocket, auth_token)

                if user:
                    # Check connection limit
                    if not ws_manager.can_connect(user["id"]):
                        await send_error(
                            websocket,
                            "Connection limit exceeded",
                            f"Maximum {ws_manager.max_connections_per_user} concurrent connections allowed.",
                            recoverable=False,
                        )
                        break

                    # Register connection
                    ws_manager._connections[user["id"]].append(
                        ws_manager._connections.get(user["id"], [])
                    )

                    await send_message(
                        websocket,
                        {
                            "type": "auth_success",
                            "user": {"id": user["id"], "email": user["email"]},
                        },
                    )
                else:
                    await send_message(
                        websocket,
                        {"type": "auth_failed", "message": "Invalid token"},
                    )
                continue

            # Handle user message with abstract
            if msg_type == MessageType.USER_MESSAGE:
                abstract = data.get("abstract", "").strip()
                language = data.get("language", "auto")

                if not abstract or len(abstract) < 10:
                    await send_error(
                        websocket,
                        "Abstract too short",
                        "Please provide at least 10 characters",
                        recoverable=True,
                    )
                    continue

                # Store for later DB save
                db_session_abstract = abstract
                db_session_language = language

                # Create local session
                session = session_manager.create_session(abstract, language)
                session_id = session.session_id

                # Confirm session started
                msg = SessionStarted(
                    session_id=session_id,
                    timestamp=datetime.now().isoformat(),
                )
                response = msg.model_dump()

                # Add user info if authenticated
                if user:
                    response["user"] = {"id": user["id"], "email": user["email"]}
                    response["history_enabled"] = True
                else:
                    response["history_enabled"] = False

                await send_message(websocket, response)
                break

        # ════════════════════════════════════════════════════════════════════
        # Input Clarification Phase
        # ════════════════════════════════════════════════════════════════════
        await send_thinking(websocket, "Analyzing your abstract...", "assessing", 5)

        assessment = await service.assess_input(
            session.abstract,
            on_thinking=lambda msg, step, progress: send_thinking(
                websocket, msg, step, progress
            ),
        )

        session_manager.update_session(session_id, assessment=assessment)
        db_session_assessment = assessment

        completeness_score = assessment.get("completeness_score", 0)

        # If incomplete, ask clarification questions
        if completeness_score < 60:
            await send_thinking(
                websocket,
                "Your abstract needs more details. Preparing questions...",
                "generating",
                25,
            )

            questions_data = await service.get_clarification_questions(
                session.abstract,
                assessment,
                on_thinking=lambda msg, step, progress: send_thinking(
                    websocket, msg, step, progress
                ),
            )

            session_manager.update_session(
                session_id, clarification_questions=questions_data
            )

            # Send clarification request
            clarification_msg = ClarificationNeeded(
                intro_message=questions_data.get(
                    "intro_message",
                    "I need more information to provide accurate analysis:",
                ),
                questions=[
                    ClarificationQuestion(
                        id=q["element"],
                        question=q["question"],
                        element=q["element"],
                        priority=q["priority"],
                    )
                    for q in questions_data.get("questions", [])
                ],
                skip_allowed=False,
                skip_message=None,
            )
            await send_message(websocket, clarification_msg.model_dump())

            # ════════════════════════════════════════════════════════════════
            # Wait for User Answers
            # ════════════════════════════════════════════════════════════════
            expected_answers = len(clarification_msg.questions)
            received_answers = 0

            while received_answers < expected_answers:
                answer_data = await websocket.receive_json()

                if answer_data.get("type") == MessageType.USER_ANSWER:
                    question_id = answer_data.get("question_id")
                    answer = answer_data.get("answer", "").strip()

                    if answer:
                        session_manager.add_user_answer(session_id, question_id, answer)
                        received_answers += 1

                        await send_thinking(
                            websocket,
                            f"Received answer ({received_answers}/{expected_answers})",
                            "clarifying",
                            40 + (10 * received_answers // expected_answers),
                        )

            # Enrich abstract with answers
            session = session_manager.get_session(session_id)
            enriched_abstract = await service.enrich_abstract(
                session.abstract,
                session.user_answers,
                assessment.get("missing_critical", []),
                on_thinking=lambda msg, step, progress: send_thinking(
                    websocket, msg, step, progress
                ),
            )

            session_manager.update_session(
                session_id, enriched_abstract=enriched_abstract
            )
            abstract_to_analyze = enriched_abstract
            db_session_abstract = enriched_abstract
        else:
            await send_thinking(
                websocket,
                f"Abstract is {completeness_score}% complete. Proceeding with analysis...",
                "ready",
                45,
            )
            abstract_to_analyze = session.abstract

        # ════════════════════════════════════════════════════════════════════
        # Full Analysis Phase
        # ════════════════════════════════════════════════════════════════════
        await send_thinking(
            websocket, "Starting comprehensive analysis...", "analyzing", 50
        )

        final_result = await service.analyze_full(
            abstract_to_analyze,
            on_progress=lambda step, msg, progress, partial: send_progress(
                websocket, step, msg, progress, partial
            ),
        )

        session_manager.mark_complete(session_id, final_result)

        # Extract keywords and papers for DB storage
        db_session_keywords = final_result.get("research", {}).get("keywords", [])
        papers = [
            p.to_dict() if hasattr(p, "to_dict") else p
            for p in final_result.get("research", {}).get("papers", [])
        ]

        # ════════════════════════════════════════════════════════════════════
        # Send Final Results
        # ════════════════════════════════════════════════════════════════════
        complete_msg = AnalysisComplete(
            result=final_result,
            processing_time_seconds=final_result["metadata"]["processing_time_seconds"],
        )
        await send_message(websocket, complete_msg.model_dump())

        # ════════════════════════════════════════════════════════════════════
        # Save to Supabase (if authenticated)
        # ════════════════════════════════════════════════════════════════════
        if user and db_session_abstract:
            await save_results_to_supabase(
                user_id=user["id"],
                abstract=db_session_abstract,
                language=db_session_language,
                keywords=db_session_keywords,
                assessment=db_session_assessment,
                final_result=final_result,
                papers=papers,
            )

    except WebSocketDisconnect:
        pass

    except json.JSONDecodeError as e:
        await send_error(
            websocket,
            "Invalid JSON",
            f"Could not parse message: {str(e)}",
            recoverable=False,
        )

    except Exception as e:
        await send_error(
            websocket,
            "Internal error",
            f"Unexpected error: {str(e)}",
            recoverable=False,
        )

    finally:
        # Clean up
        if session_id:
            session_manager.delete_session(session_id)

        if user:
            ws_manager.disconnect(websocket, user["id"])

        try:
            await websocket.close()
        except Exception:
            pass
