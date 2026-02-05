"""
Example WebSocket client for testing realtime Topic Analyzer.

Usage:
    python examples/test_ws_client.py
"""

import asyncio
import json

import websockets


async def test_topic_analyzer():
    """Test the WebSocket topic analyzer endpoint."""
    uri = "ws://localhost:8000/api/v1/ws/topic/analyze"

    print("🔌 Connecting to WebSocket...")

    async with websockets.connect(uri) as websocket:
        print("✅ Connected!\n")

        # ══════════════════════════════════════════════════════════
        # Step 1: Send initial abstract
        # ══════════════════════════════════════════════════════════
        abstract = """
        A study investigating machine learning techniques for predicting
        patient outcomes in cardiovascular disease.
        """

        initial_message = {
            "type": "user_message",
            "abstract": abstract.strip(),
            "language": "en",
        }

        print("📤 Sending abstract...")
        await websocket.send(json.dumps(initial_message))

        # ══════════════════════════════════════════════════════════
        # Step 2: Listen for messages
        # ══════════════════════════════════════════════════════════
        session_id = None
        clarification_questions = []

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                msg_type = data.get("type")

                # ──────────────────────────────────────────────────
                # Session Started
                # ──────────────────────────────────────────────────
                if msg_type == "session_started":
                    session_id = data.get("session_id")
                    print(f"🎯 Session started: {session_id}\n")

                # ──────────────────────────────────────────────────
                # Agent Thinking (Status Updates)
                # ──────────────────────────────────────────────────
                elif msg_type == "agent_thinking":
                    message_text = data.get("message")
                    step = data.get("step")
                    progress = data.get("progress")
                    print(f"💭 [{progress}%] {message_text} ({step})")

                # ──────────────────────────────────────────────────
                # Clarification Needed
                # ──────────────────────────────────────────────────
                elif msg_type == "clarification_needed":
                    print("\n❓ Clarification needed:")
                    print(f"   {data.get('intro_message')}\n")

                    questions = data.get("questions", [])
                    clarification_questions = questions

                    for i, q in enumerate(questions, 1):
                        print(f"   {i}. [{q['element']}] {q['question']}")
                        print(f"      Priority: {q['priority']}")

                    print("\n📝 Answering questions...")

                    # Send answers (simulated)
                    for q in questions:
                        answer = {
                            "type": "user_answer",
                            "question_id": q["id"],
                            "answer": f"This is a simulated answer for {q['element']}",
                            "session_id": session_id,
                        }
                        await websocket.send(json.dumps(answer))
                        await asyncio.sleep(0.5)  # Simulate user typing

                # ──────────────────────────────────────────────────
                # Analysis Progress
                # ──────────────────────────────────────────────────
                elif msg_type == "analysis_progress":
                    step = data.get("step")
                    message_text = data.get("message")
                    progress = data.get("progress")
                    partial = data.get("partial_result")

                    print(f"\n🔬 [{progress}%] {step.upper()}: {message_text}")

                    if partial:
                        print(f"   Partial result: {json.dumps(partial, indent=2)}")

                # ──────────────────────────────────────────────────
                # Analysis Complete
                # ──────────────────────────────────────────────────
                elif msg_type == "analysis_complete":
                    print("\n✨ Analysis complete!\n")

                    result = data.get("result", {})
                    processing_time = data.get("processing_time_seconds")

                    print("═" * 60)
                    print("FINAL RESULTS")
                    print("═" * 60)

                    # Novelty
                    novelty = result.get("novelty", {})
                    print(f"\n📊 NOVELTY SCORE: {novelty.get('score')}/100")
                    print(f"   {novelty.get('reasoning')}")

                    # Publishability
                    pub = result.get("publishability", {})
                    print(f"\n📈 PUBLISHABILITY: {pub.get('level')} ({pub.get('target_tier')})")
                    print(f"   Confidence: {pub.get('confidence')}")
                    print(f"   {pub.get('reasoning')}")

                    # Gaps
                    gaps = result.get("gaps", [])
                    print(f"\n🔍 RESEARCH GAPS ({len(gaps)}):")
                    for gap in gaps[:3]:
                        print(f"   - [{gap.get('type')}] {gap.get('description')}")

                    # Suggestions
                    suggestions = result.get("suggestions", [])
                    print(f"\n💡 SUGGESTIONS ({len(suggestions)}):")
                    for sug in suggestions[:3]:
                        print(f"   - {sug.get('action')} (Impact: {sug.get('impact')})")

                    print(f"\n⏱️  Processing time: {processing_time}s")
                    print("═" * 60)

                    break  # Done!

                # ──────────────────────────────────────────────────
                # Error
                # ──────────────────────────────────────────────────
                elif msg_type == "error":
                    error = data.get("error")
                    details = data.get("details")
                    recoverable = data.get("recoverable")

                    print(f"\n❌ Error: {error}")
                    if details:
                        print(f"   Details: {details}")
                    print(f"   Recoverable: {recoverable}")

                    if not recoverable:
                        break

            except websockets.exceptions.ConnectionClosed:
                print("\n🔌 Connection closed")
                break


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  AVR Topic Analyzer - WebSocket Test Client              ║
╚═══════════════════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(test_topic_analyzer())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
