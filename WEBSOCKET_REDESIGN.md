# WebSocket Realtime Topic Analyzer - Redesign Documentation

## 🎯 Overview

The Topic Analyzer has been redesigned to support **realtime WebSocket communication**, enabling:
- ✅ Interactive clarification dialogue before analysis
- ✅ Realtime progress updates during analysis
- ✅ Streaming results as they become available
- ✅ Natural conversational flow

## 🏗️ Architecture

### Previous Design (REST API)
```
Client → POST /api/v1/topic/analyze
         ↓
    [Wait 30-60s]
         ↓
    ← Response with results
```

**Problems:**
- No feedback during long analysis
- Clarification requires second request
- User sees nothing until completion
- `skip_clarification` flag bypasses conversation

### New Design (WebSocket)
```
Client ↔ WebSocket /api/v1/ws/topic/analyze
    │
    ├─ Send abstract
    ├─ Receive: session_started
    ├─ Receive: agent_thinking (status updates)
    ├─ Receive: clarification_needed (if incomplete)
    ├─ Send: user_answer (for each question)
    ├─ Receive: analysis_progress (novelty, gaps, swot...)
    └─ Receive: analysis_complete (final results)
```

**Benefits:**
- ✅ Realtime bidirectional communication
- ✅ Natural conversation flow
- ✅ Progress visibility (0-100%)
- ✅ No timeout issues
- ✅ Better UX for long operations

---

## 📁 New Files Created

### 1. Message Schemas
**File:** [`app/models/ws_schemas.py`](app/models/ws_schemas.py)

Defines all WebSocket message types:

**Client → Server:**
- `UserMessage`: Initial abstract submission
- `UserAnswer`: Answer to clarification question

**Server → Client:**
- `SessionStarted`: Connection confirmation
- `AgentThinking`: Processing status updates
- `ClarificationNeeded`: Questions for user
- `AnalysisProgress`: Step-by-step progress
- `AnalysisComplete`: Final results
- `ErrorMessage`: Error handling

### 2. Session Manager
**File:** [`app/core/session_manager.py`](app/core/session_manager.py)

Manages conversation state:
```python
class ConversationSession:
    session_id: str
    abstract: str
    assessment: dict
    user_answers: dict
    enriched_abstract: str
    analysis_results: dict
    is_complete: bool
```

**Methods:**
- `create_session()` - Initialize new conversation
- `add_user_answer()` - Store clarification answers
- `store_analysis_result()` - Save partial results
- `mark_complete()` - Finalize session

### 3. Streaming Service
**File:** [`app/services/topic_analyzer_streaming.py`](app/services/topic_analyzer_streaming.py)

Analysis service with callback support:

```python
class TopicAnalyzerStreamingService:
    async def assess_input(
        abstract: str,
        on_thinking: Callable  # Progress callback
    ) -> dict

    async def get_clarification_questions(
        abstract: str,
        assessment: dict,
        on_thinking: Callable
    ) -> dict

    async def enrich_abstract(
        abstract: str,
        user_answers: dict,
        missing_elements: list,
        on_thinking: Callable
    ) -> str

    async def analyze_full(
        abstract: str,
        on_progress: Callable  # Step-by-step progress
    ) -> dict
```

### 4. WebSocket Handler
**File:** [`app/api/v1/ws_topic.py`](app/api/v1/ws_topic.py)

WebSocket endpoint implementation:
```python
@router.websocket("/ws/topic/analyze")
async def websocket_topic_analyze(websocket: WebSocket)
```

**Flow:**
1. Accept connection
2. Wait for abstract
3. Assess completeness
4. If incomplete → request clarification
5. Wait for answers
6. Enrich abstract
7. Run full analysis with progress updates
8. Send final results

---

## 🔄 Message Flow

### Scenario 1: Complete Abstract (No Clarification)

```
Client: {type: "user_message", abstract: "..."}
Server: {type: "session_started", session_id: "abc123"}
Server: {type: "agent_thinking", message: "Assessing...", progress: 10}
Server: {type: "agent_thinking", message: "90% complete, ready!", progress: 45}
Server: {type: "analysis_progress", step: "novelty", progress: 60, ...}
Server: {type: "analysis_progress", step: "gaps", progress: 70, ...}
Server: {type: "analysis_progress", step: "swot", progress: 80, ...}
Server: {type: "analysis_progress", step: "publishability", progress: 90, ...}
Server: {type: "analysis_complete", result: {...}}
```

### Scenario 2: Incomplete Abstract (With Clarification)

```
Client: {type: "user_message", abstract: "ML in healthcare"}
Server: {type: "session_started", session_id: "xyz789"}
Server: {type: "agent_thinking", message: "Assessing...", progress: 20}
Server: {
    type: "clarification_needed",
    intro_message: "Need more details:",
    questions: [
        {id: "methodology", question: "What ML techniques?", priority: 1},
        {id: "population", question: "What patient population?", priority: 1},
        {id: "outcome", question: "What outcomes measured?", priority: 2}
    ]
}

# User answers via UI
Client: {type: "user_answer", question_id: "methodology", answer: "Random forests"}
Client: {type: "user_answer", question_id: "population", answer: "ICU patients"}
Client: {type: "user_answer", question_id: "outcome", answer: "30-day mortality"}

Server: {type: "agent_thinking", message: "Enriching...", progress: 30}
Server: {type: "analysis_progress", step: "novelty", ...}
...
Server: {type: "analysis_complete", result: {...}}
```

---

## 🧪 Testing

### Python Client
```bash
# Install websockets
pip install websockets

# Run test client
python examples/test_ws_client.py
```

### HTML Client
```bash
# Start server
uvicorn app.main:app --reload

# Open in browser
open examples/test_ws_client.html
```

### Manual Testing with wscat
```bash
npm install -g wscat
wscat -c ws://localhost:8000/api/v1/ws/topic/analyze

# Send message
{"type": "user_message", "abstract": "Your abstract here", "language": "en"}
```

---

## 🔧 Configuration

No additional configuration needed. WebSocket support is built into FastAPI.

**Optional:** For production, consider:
1. **Session persistence**: Replace in-memory `SessionManager` with Redis
2. **Load balancing**: Use sticky sessions for WebSocket routing
3. **Timeout handling**: Add connection timeout logic
4. **Rate limiting**: Implement per-IP connection limits

---

## 🚀 Usage Example

### JavaScript/TypeScript Client

```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/topic/analyze');

ws.onopen = () => {
    // Send abstract
    ws.send(JSON.stringify({
        type: 'user_message',
        abstract: 'Your research abstract here...',
        language: 'en'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch(data.type) {
        case 'session_started':
            console.log('Session:', data.session_id);
            break;

        case 'agent_thinking':
            updateProgress(data.progress, data.message);
            break;

        case 'clarification_needed':
            showQuestions(data.questions);
            break;

        case 'analysis_progress':
            updateAnalysisStep(data.step, data.message, data.progress);
            break;

        case 'analysis_complete':
            displayResults(data.result);
            break;

        case 'error':
            showError(data.error, data.details);
            break;
    }
};

// Answer clarification questions
function answerQuestion(questionId, answer, sessionId) {
    ws.send(JSON.stringify({
        type: 'user_answer',
        question_id: questionId,
        answer: answer,
        session_id: sessionId
    }));
}
```

### Python Client

```python
import asyncio
import websockets
import json

async def analyze_topic(abstract: str):
    uri = "ws://localhost:8000/api/v1/ws/topic/analyze"

    async with websockets.connect(uri) as ws:
        # Send abstract
        await ws.send(json.dumps({
            'type': 'user_message',
            'abstract': abstract,
            'language': 'en'
        }))

        session_id = None

        # Listen for messages
        async for message in ws:
            data = json.loads(message)

            if data['type'] == 'session_started':
                session_id = data['session_id']

            elif data['type'] == 'clarification_needed':
                # Answer questions
                for q in data['questions']:
                    answer = input(f"{q['question']}: ")
                    await ws.send(json.dumps({
                        'type': 'user_answer',
                        'question_id': q['id'],
                        'answer': answer,
                        'session_id': session_id
                    }))

            elif data['type'] == 'analysis_complete':
                print("Results:", data['result'])
                break

asyncio.run(analyze_topic("Your abstract here"))
```

---

## 📊 Progress Tracking

Progress is reported in 0-100% increments:

| Stage | Progress | Description |
|-------|----------|-------------|
| Connection | 0% | WebSocket established |
| Assessment | 10-20% | Checking abstract completeness |
| Clarification | 25-40% | Generating/answering questions |
| Enrichment | 40-50% | Enhancing abstract with answers |
| Novelty | 50-60% | Scoring novelty and prior art |
| Gaps | 65-70% | Identifying research gaps |
| SWOT | 75-80% | Strengths/weaknesses analysis |
| Publishability | 85-90% | Predicting publication success |
| Suggestions | 95-100% | Generating improvements |
| Complete | 100% | Final results ready |

---

## 🔐 Security Considerations

1. **Rate Limiting**: Implement connection limits per IP
2. **Authentication**: Add token-based auth for production
3. **Input Validation**: All messages validated via Pydantic
4. **Timeout**: Auto-disconnect idle connections (default: 5 min)
5. **Error Handling**: All exceptions caught and reported gracefully

---

## 🐛 Error Handling

All errors are sent as `ErrorMessage`:

```json
{
    "type": "error",
    "error": "Invalid abstract",
    "details": "Abstract must be at least 10 characters",
    "recoverable": true
}
```

**Recoverable errors**: User can retry
**Non-recoverable errors**: Connection will be closed

---

## 🎨 Frontend Integration

### React Example

```tsx
import { useEffect, useState } from 'react';

function TopicAnalyzer() {
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('');
    const [questions, setQuestions] = useState([]);
    const [results, setResults] = useState(null);

    const analyze = (abstract: string) => {
        const socket = new WebSocket('ws://localhost:8000/api/v1/ws/topic/analyze');

        socket.onopen = () => {
            socket.send(JSON.stringify({
                type: 'user_message',
                abstract: abstract,
                language: 'en'
            }));
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'agent_thinking') {
                setProgress(data.progress);
                setStatus(data.message);
            } else if (data.type === 'clarification_needed') {
                setQuestions(data.questions);
            } else if (data.type === 'analysis_complete') {
                setResults(data.result);
                setProgress(100);
            }
        };

        setWs(socket);
    };

    return (
        <div>
            <textarea onChange={(e) => analyze(e.target.value)} />
            <ProgressBar value={progress} />
            <p>{status}</p>
            {questions.length > 0 && <QuestionForm questions={questions} ws={ws} />}
            {results && <ResultsDisplay results={results} />}
        </div>
    );
}
```

---

## 🔄 Migration from REST API

**Old REST endpoint** (`POST /api/v1/topic/analyze`) is still available for:
- Backward compatibility
- Non-interactive batch processing
- Simple integrations

**When to use WebSocket:**
- Interactive web applications
- Real-time progress needed
- User clarification required
- Long-running operations

**When to use REST:**
- Simple scripts
- Batch processing
- No UI feedback needed
- Legacy integrations

---

## 📈 Performance

**Expected timings:**
- Connection: < 100ms
- Assessment: 2-5s
- Clarification Q gen: 3-6s
- Full analysis: 30-60s

**Optimization tips:**
1. Cache embeddings for similar abstracts
2. Use faster LLM for thinking messages (Haiku)
3. Parallel analysis steps where possible
4. Implement result caching

---

## 🎯 Next Steps

Potential enhancements:

1. **Chat History**: Allow reviewing past analyses
2. **Resume Session**: Reconnect to in-progress analysis
3. **Multi-language**: Real-time language detection
4. **Voice Input**: Speech-to-text for abstract entry
5. **Collaborative**: Multiple users analyzing same abstract
6. **Export**: Download results as PDF/JSON
7. **Comparison**: Side-by-side analysis of multiple abstracts

---

## 📚 Additional Resources

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

## 🤝 Contributing

For bug reports or feature requests related to WebSocket functionality, please:
1. Test with the provided example clients
2. Include WebSocket message logs
3. Specify client library/framework used
4. Describe expected vs actual behavior
