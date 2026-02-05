# 🔌 WebSocket Realtime Topic Analyzer

## 🎯 Quick Overview

The AVR Topic Analyzer now supports **realtime WebSocket communication**, enabling interactive conversations with users during the analysis process.

### What's New?
- ✅ **Realtime progress updates** (0-100%)
- ✅ **Interactive clarification** (no more `skip_clarification` flag!)
- ✅ **Bidirectional chat** (ask questions, get answers)
- ✅ **Better UX** (no blind waiting)
- ✅ **No timeouts** (streaming keeps connection alive)

---

## 🚀 Quick Start

### 1. Install & Run
```bash
cd /Users/linh/linh/avr
source venv/bin/activate
pip install websockets  # For Python client

# Start server
uvicorn app.main:app --reload
```

### 2. Test with Python Client
```bash
python examples/test_ws_client.py
```

### 3. Test with Browser
```bash
open examples/test_ws_client.html
```

---

## 📁 Project Structure

```
avr/
├── app/
│   ├── api/v1/
│   │   ├── ws_topic.py              # 🆕 WebSocket endpoint
│   │   └── topic.py                 # Original REST endpoint
│   │
│   ├── core/
│   │   └── session_manager.py       # 🆕 Session state management
│   │
│   ├── models/
│   │   ├── ws_schemas.py            # 🆕 WebSocket message types
│   │   └── schemas.py               # Original Pydantic models
│   │
│   └── services/
│       ├── topic_analyzer_streaming.py  # 🆕 Streaming service
│       └── topic_analyzer.py            # Original service
│
├── examples/
│   ├── test_ws_client.py            # 🆕 Python test client
│   └── test_ws_client.html          # 🆕 HTML test client
│
├── docs/
│   └── websocket_flow_diagram.txt   # 🆕 Visual flow diagram
│
├── WEBSOCKET_REDESIGN.md            # 🆕 Complete technical docs
├── ARCHITECTURE_COMPARISON.md       # 🆕 REST vs WebSocket
├── QUICKSTART_WEBSOCKET.md          # 🆕 Getting started guide
└── WEBSOCKET_SUMMARY.md             # 🆕 Implementation summary
```

---

## 🔄 Comparison: Before vs After

### Before (REST API)
```javascript
// Single request, wait 60s
const response = await fetch('/api/v1/topic/analyze', {
    method: 'POST',
    body: JSON.stringify({
        abstract: "...",
        skip_clarification: true  // ❌ Must choose!
    })
});

// [Wait 60 seconds with no feedback...]

const result = await response.json();
```

### After (WebSocket)
```javascript
// Interactive conversation
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/topic/analyze');

ws.send(JSON.stringify({
    type: 'user_message',
    abstract: '...'
}));

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // ✅ Realtime updates!
    if (data.type === 'agent_thinking') {
        console.log(`[${data.progress}%] ${data.message}`);
    }

    // ✅ Interactive clarification!
    if (data.type === 'clarification_needed') {
        data.questions.forEach(q => {
            const answer = prompt(q.question);
            ws.send(JSON.stringify({
                type: 'user_answer',
                question_id: q.id,
                answer: answer
            }));
        });
    }

    // ✅ Final results
    if (data.type === 'analysis_complete') {
        console.log('Done!', data.result);
    }
};
```

---

## 📊 Message Flow

```
Client                          Server
  │
  ├──── user_message ────────────► (abstract)
  │
  ◄──── session_started ──────────┤ session_id
  ◄──── agent_thinking ───────────┤ [10%] Assessing...
  ◄──── agent_thinking ───────────┤ [20%] 45% complete
  │
  ◄──── clarification_needed ─────┤ Questions: [...]
  │
  ├──── user_answer ──────────────► Q1 answer
  ├──── user_answer ──────────────► Q2 answer
  │
  ◄──── agent_thinking ───────────┤ [40%] Enriching...
  ◄──── analysis_progress ────────┤ [60%] Novelty: 72/100
  ◄──── analysis_progress ────────┤ [70%] 5 gaps found
  ◄──── analysis_progress ────────┤ [80%] SWOT done
  ◄──── analysis_progress ────────┤ [90%] Publishability: Q2
  │
  ◄──── analysis_complete ────────┤ [100%] Full results
  │
```

---

## 🛠️ API Reference

### WebSocket Endpoint
```
ws://localhost:8000/api/v1/ws/topic/analyze
```

### Client → Server Messages

**user_message** (Initial abstract)
```json
{
    "type": "user_message",
    "abstract": "Your research abstract...",
    "language": "en"
}
```

**user_answer** (Answer clarification question)
```json
{
    "type": "user_answer",
    "question_id": "methodology",
    "answer": "Random forests",
    "session_id": "abc-123"
}
```

### Server → Client Messages

**session_started**
```json
{
    "type": "session_started",
    "session_id": "abc-123",
    "timestamp": "2025-01-19T10:30:00"
}
```

**agent_thinking** (Status updates)
```json
{
    "type": "agent_thinking",
    "message": "Assessing completeness...",
    "step": "assessing",
    "progress": 20
}
```

**clarification_needed** (Ask questions)
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
    ]
}
```

**analysis_progress** (Step updates)
```json
{
    "type": "analysis_progress",
    "step": "novelty",
    "message": "Novelty score: 72/100",
    "progress": 60,
    "partial_result": {"novelty_score": 72}
}
```

**analysis_complete** (Final results)
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

**error**
```json
{
    "type": "error",
    "error": "Invalid abstract",
    "details": "Too short",
    "recoverable": true
}
```

---

## 🧪 Testing

### Python Client
```bash
python examples/test_ws_client.py
```

Expected output:
```
🔌 Connecting to WebSocket...
✅ Connected!

📤 Sending abstract...
🎯 Session started: abc-123-xyz

💭 [10%] Assessing abstract completeness... (assessing)
💭 [20%] Completeness assessed: 35% complete (assessing)

❓ Clarification needed:
   1. [methodology] What specific ML techniques?
   2. [population] What patient population?

📝 Answering questions...

🔬 [60%] NOVELTY: Analyzing novelty and prior art...
🔬 [80%] SWOT: Performing SWOT analysis...

✨ Analysis complete!

📊 NOVELTY SCORE: 72/100
📈 PUBLISHABILITY: MEDIUM (Q2)
⏱️  Processing time: 45.2s
```

### HTML Client
```bash
open examples/test_ws_client.html
```

Features:
- Real-time progress bar
- Interactive question forms
- Animated status messages
- Results visualization

---

## 🎨 Frontend Integration

### React Example
```jsx
import { useEffect, useState } from 'react';

function TopicAnalyzer() {
    const [ws, setWs] = useState(null);
    const [progress, setProgress] = useState(0);
    const [questions, setQuestions] = useState([]);

    useEffect(() => {
        const socket = new WebSocket(
            'ws://localhost:8000/api/v1/ws/topic/analyze'
        );

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'agent_thinking':
                    setProgress(data.progress);
                    break;
                case 'clarification_needed':
                    setQuestions(data.questions);
                    break;
                case 'analysis_complete':
                    showResults(data.result);
                    break;
            }
        };

        setWs(socket);
        return () => socket.close();
    }, []);

    const analyze = (abstract) => {
        ws.send(JSON.stringify({
            type: 'user_message',
            abstract: abstract,
            language: 'en'
        }));
    };

    return (
        <div>
            <textarea onChange={(e) => analyze(e.target.value)} />
            <ProgressBar value={progress} />
            {questions.map(q => (
                <Question key={q.id} question={q} ws={ws} />
            ))}
        </div>
    );
}
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [WEBSOCKET_REDESIGN.md](WEBSOCKET_REDESIGN.md) | Complete technical documentation |
| [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) | REST vs WebSocket comparison |
| [QUICKSTART_WEBSOCKET.md](QUICKSTART_WEBSOCKET.md) | Quick start guide |
| [WEBSOCKET_SUMMARY.md](WEBSOCKET_SUMMARY.md) | Implementation summary |
| [docs/websocket_flow_diagram.txt](docs/websocket_flow_diagram.txt) | Visual flow diagram |

---

## ✅ Benefits

### For Users
- 📊 See progress in real-time (no blind waiting)
- 💬 Natural conversation flow (ask/answer)
- ⚡ Faster perceived response time
- 🔄 Can provide clarifications without restarting

### For Developers
- 🎯 Clean separation of concerns
- 🧪 Easy to test with provided clients
- 📝 Type-safe with Pydantic schemas
- 🔌 Extensible for future features

---

## 🔐 Production Considerations

**Implemented:**
- ✅ Input validation
- ✅ Error handling
- ✅ CORS configured
- ✅ Session management

**TODO for Production:**
- [ ] JWT authentication
- [ ] Rate limiting
- [ ] Redis session storage
- [ ] Connection pooling
- [ ] Heartbeat/ping-pong
- [ ] Load balancer config

---

## 🐛 Troubleshooting

**Connection refused:**
```bash
# Check server is running
curl http://localhost:8000/health
```

**Module not found:**
```bash
pip install websockets
```

**No progress updates:**
```bash
# Check LLM API keys in .env
cat .env | grep API_KEY
```

---

## 🎓 Learn More

**Key Files to Explore:**
1. [`app/api/v1/ws_topic.py`](app/api/v1/ws_topic.py) - WebSocket handler
2. [`app/models/ws_schemas.py`](app/models/ws_schemas.py) - Message schemas
3. [`app/services/topic_analyzer_streaming.py`](app/services/topic_analyzer_streaming.py) - Streaming service
4. [`app/core/session_manager.py`](app/core/session_manager.py) - Session management

**External Resources:**
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

## 🚀 What's Next?

Potential enhancements:
- [ ] Resume disconnected sessions
- [ ] Export results (PDF/JSON)
- [ ] Chat history
- [ ] Voice input
- [ ] Multi-user collaboration
- [ ] Real-time abstract comparison

---

## 📝 Summary

The WebSocket redesign eliminates the `skip_clarification` flag by providing **natural, realtime conversation** between client and server, dramatically improving user experience while maintaining backward compatibility.

**Get Started:** [QUICKSTART_WEBSOCKET.md](QUICKSTART_WEBSOCKET.md)

---

Built with ❤️ using FastAPI + WebSockets
