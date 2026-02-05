# WebSocket Topic Analyzer - Quick Start Guide

## 🚀 Installation & Setup

### 1. Install Dependencies
```bash
cd /Users/linh/linh/avr
source venv/bin/activate
pip install websockets  # For Python client
```

### 2. Start the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     WebSocket route registered: /api/v1/ws/topic/analyze
```

---

## 🧪 Test the WebSocket Endpoint

### Option 1: Python Client (Recommended)
```bash
python examples/test_ws_client.py
```

**Expected Output:**
```
🔌 Connecting to WebSocket...
✅ Connected!

📤 Sending abstract...
🎯 Session started: abc-123-xyz

💭 [10%] Assessing abstract completeness... (assessing)
💭 [20%] Completeness assessed: 35% complete (assessing)

❓ Clarification needed:
   Your abstract is missing some critical information:

   1. [methodology] What specific machine learning techniques will you use?
      Priority: 1
   2. [population] What is your target patient population?
      Priority: 1

📝 Answering questions...

🔬 [60%] NOVELTY: Analyzing novelty and prior art...
🔬 [70%] GAPS: Identifying research gaps...
🔬 [80%] SWOT: Performing SWOT analysis...
🔬 [90%] PUBLISHABILITY: Predicting publishability...

✨ Analysis complete!

═══════════════════════════════════════════════════════════
FINAL RESULTS
═══════════════════════════════════════════════════════════

📊 NOVELTY SCORE: 72/100
   Your approach combines existing ML techniques in a novel way...

📈 PUBLISHABILITY: MEDIUM (Q2)
   Confidence: 0.75
   This research has good potential for Q2 journals...

⏱️  Processing time: 45.2s
═══════════════════════════════════════════════════════════
```

### Option 2: HTML Client (Visual Interface)
```bash
# Server must be running on http://localhost:8000
open examples/test_ws_client.html
```

Then:
1. Enter your abstract
2. Click "🚀 Analyze Topic"
3. Watch real-time progress
4. Answer clarification questions (if needed)
5. See results with visualizations

### Option 3: Command Line (wscat)
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/api/v1/ws/topic/analyze

# Send message (paste this JSON)
{"type": "user_message", "abstract": "A study investigating machine learning techniques for predicting patient outcomes in cardiovascular disease.", "language": "en"}

# You'll receive messages like:
< {"type":"session_started","session_id":"..."}
< {"type":"agent_thinking","message":"Assessing...","progress":10}
< {"type":"clarification_needed","questions":[...]}

# Answer questions
> {"type":"user_answer","question_id":"methodology","answer":"Random forests","session_id":"..."}

# Continue receiving progress updates...
< {"type":"analysis_progress","step":"novelty","progress":60}
< {"type":"analysis_complete","result":{...}}
```

---

## 💡 Example: Custom Integration

### JavaScript/React Example

```jsx
import { useState, useEffect } from 'react';

function TopicAnalyzer() {
    const [ws, setWs] = useState(null);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('');
    const [questions, setQuestions] = useState([]);
    const [results, setResults] = useState(null);
    const [sessionId, setSessionId] = useState(null);

    const connect = () => {
        const socket = new WebSocket('ws://localhost:8000/api/v1/ws/topic/analyze');

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'session_started':
                    setSessionId(data.session_id);
                    break;

                case 'agent_thinking':
                    setProgress(data.progress);
                    setStatus(data.message);
                    break;

                case 'clarification_needed':
                    setQuestions(data.questions);
                    break;

                case 'analysis_progress':
                    setProgress(data.progress);
                    setStatus(`${data.step}: ${data.message}`);
                    break;

                case 'analysis_complete':
                    setResults(data.result);
                    setProgress(100);
                    break;
            }
        };

        setWs(socket);
    };

    const analyze = (abstract) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'user_message',
                abstract: abstract,
                language: 'en'
            }));
        }
    };

    const answerQuestion = (questionId, answer) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'user_answer',
                question_id: questionId,
                answer: answer,
                session_id: sessionId
            }));
        }
    };

    useEffect(() => {
        connect();
        return () => ws?.close();
    }, []);

    return (
        <div>
            <textarea onChange={(e) => analyze(e.target.value)} />

            <ProgressBar value={progress} />
            <p>{status}</p>

            {questions.length > 0 && (
                <QuestionForm
                    questions={questions}
                    onSubmit={answerQuestion}
                />
            )}

            {results && <ResultsDisplay results={results} />}
        </div>
    );
}
```

### Python AsyncIO Example

```python
import asyncio
import websockets
import json

async def analyze_abstract(abstract: str):
    """Analyze a research abstract using WebSocket."""

    uri = "ws://localhost:8000/api/v1/ws/topic/analyze"
    session_id = None

    async with websockets.connect(uri) as ws:
        # Send abstract
        await ws.send(json.dumps({
            'type': 'user_message',
            'abstract': abstract,
            'language': 'en'
        }))

        # Handle messages
        async for message in ws:
            data = json.loads(message)

            if data['type'] == 'session_started':
                session_id = data['session_id']
                print(f"Session: {session_id}")

            elif data['type'] == 'agent_thinking':
                print(f"[{data['progress']}%] {data['message']}")

            elif data['type'] == 'clarification_needed':
                print("\nPlease answer these questions:")
                for q in data['questions']:
                    print(f"\n{q['question']}")
                    answer = input("> ")

                    await ws.send(json.dumps({
                        'type': 'user_answer',
                        'question_id': q['id'],
                        'answer': answer,
                        'session_id': session_id
                    }))

            elif data['type'] == 'analysis_progress':
                print(f"[{data['progress']}%] {data['step']}: {data['message']}")

            elif data['type'] == 'analysis_complete':
                print("\n✨ Analysis Complete!")
                result = data['result']

                print(f"\nNovelty Score: {result['novelty']['score']}/100")
                print(f"Publishability: {result['publishability']['level']}")
                print(f"Target Tier: {result['publishability']['target_tier']}")

                return result

# Usage
abstract = """
A study investigating machine learning techniques for
predicting patient outcomes in cardiovascular disease.
"""

result = asyncio.run(analyze_abstract(abstract))
```

---

## 🔍 Debugging

### Check WebSocket Connection
```bash
# Server logs should show:
INFO:     ('127.0.0.1', 54321) - "WebSocket /api/v1/ws/topic/analyze" [accepted]
INFO:     connection open
```

### Enable Debug Logging
```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**1. Connection Refused**
```
Error: WebSocket connection failed
```
**Fix:** Ensure server is running on port 8000

**2. Module Not Found**
```
ModuleNotFoundError: No module named 'websockets'
```
**Fix:** `pip install websockets`

**3. CORS Issues (Browser)**
```
Cross-Origin Request Blocked
```
**Fix:** CORS is already configured in app/main.py for `*` origins

**4. Timeout During Analysis**
```
Connection closed unexpectedly
```
**Fix:** Check LLM API keys in .env file

---

## 📊 Message Reference

### Client → Server

**Initial Message:**
```json
{
    "type": "user_message",
    "abstract": "Your research abstract...",
    "language": "en"
}
```

**Answer Message:**
```json
{
    "type": "user_answer",
    "question_id": "methodology",
    "answer": "Random forests and neural networks",
    "session_id": "abc-123"
}
```

### Server → Client

**Session Started:**
```json
{
    "type": "session_started",
    "session_id": "abc-123",
    "timestamp": "2025-01-19T10:30:00"
}
```

**Thinking Update:**
```json
{
    "type": "agent_thinking",
    "message": "Assessing completeness...",
    "step": "assessing",
    "progress": 20
}
```

**Clarification Request:**
```json
{
    "type": "clarification_needed",
    "intro_message": "Need more details:",
    "questions": [
        {
            "id": "methodology",
            "question": "What ML techniques?",
            "element": "methodology",
            "priority": 1
        }
    ],
    "skip_allowed": false
}
```

**Progress Update:**
```json
{
    "type": "analysis_progress",
    "step": "novelty",
    "message": "Scoring novelty...",
    "progress": 60,
    "partial_result": {
        "novelty_score": 72
    }
}
```

**Complete:**
```json
{
    "type": "analysis_complete",
    "result": {
        "novelty": {...},
        "gaps": [...],
        "swot": {...},
        "publishability": {...},
        "suggestions": [...]
    },
    "processing_time_seconds": 45.2
}
```

---

## 🎓 Next Steps

1. **Explore the code:**
   - [`app/api/v1/ws_topic.py`](app/api/v1/ws_topic.py) - WebSocket handler
   - [`app/models/ws_schemas.py`](app/models/ws_schemas.py) - Message schemas
   - [`app/services/topic_analyzer_streaming.py`](app/services/topic_analyzer_streaming.py) - Streaming service

2. **Read documentation:**
   - [WEBSOCKET_REDESIGN.md](WEBSOCKET_REDESIGN.md) - Full redesign details
   - [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) - REST vs WebSocket

3. **Customize:**
   - Modify message schemas for your needs
   - Add authentication
   - Implement caching
   - Add more analysis steps

4. **Deploy:**
   - Use reverse proxy (nginx) for WebSocket
   - Configure load balancing with sticky sessions
   - Set up Redis for session persistence

---

## 📞 Support

For issues or questions:
1. Check server logs: `uvicorn app.main:app --log-level debug`
2. Test with provided clients first
3. Verify LLM API keys in `.env`
4. Review WebSocket message flow

Happy analyzing! 🚀
