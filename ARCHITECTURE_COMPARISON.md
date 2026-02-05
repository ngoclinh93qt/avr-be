# Architecture Comparison: REST vs WebSocket

## 🔄 Old Architecture (REST API)

### Request Flow
```
┌─────────┐                                    ┌─────────┐
│         │  POST /api/v1/topic/analyze        │         │
│ Client  │────────────────────────────────────>│ Server  │
│         │  {                                  │         │
│         │    abstract: "...",                 │         │
│         │    skip_clarification: true/false   │         │
│         │  }                                  │         │
│         │                                     │         │
│         │                                     │  [Processing]
│         │                                     │  - Assess
│         │         [30-60 seconds wait]        │  - Analyze
│         │         [No feedback]               │  - Generate
│         │                                     │         │
│         │  Response (after completion)        │         │
│         │<────────────────────────────────────│         │
│         │  {                                  │         │
│         │    status: "complete",              │         │
│         │    novelty: {...},                  │         │
│         │    gaps: [...],                     │         │
│         │    ...                              │         │
│         │  }                                  │         │
└─────────┘                                    └─────────┘
```

### Problems
❌ **No realtime feedback** - User waits blindly
❌ **Single request/response** - Cannot clarify mid-process
❌ **skip_clarification flag** - Either skip or fail, no conversation
❌ **Timeout risk** - Long analysis may timeout
❌ **Poor UX** - No progress indication

### Code Structure
```
app/api/v1/topic.py
    └── @router.post("/analyze")
         └── TopicAnalyzerService.analyze()
              ├── assess_completeness()
              ├── if incomplete and not skip_clarification:
              │    └── return {status: "needs_clarification"}
              └── [Run full pipeline, no updates]
```

---

## ⚡ New Architecture (WebSocket)

### Connection Flow
```
┌─────────┐                                    ┌─────────┐
│         │  WS: /api/v1/ws/topic/analyze      │         │
│ Client  │◄──────────────────────────────────►│ Server  │
│         │                                     │         │
└─────────┘                                    └─────────┘
```

### Message Exchange
```
Client                          Server
  │                               │
  │──── user_message ────────────►│ {abstract: "..."}
  │                               │
  │◄─── session_started ──────────│ {session_id: "abc123"}
  │                               │
  │◄─── agent_thinking ───────────│ "Assessing..." [10%]
  │                               │
  │◄─── agent_thinking ───────────│ "Checking completeness..." [20%]
  │                               │
  │                        ┌──────┤
  │                        │ If incomplete:
  │                        └──────┤
  │◄─── clarification_needed ─────│ {questions: [...]}
  │                               │
  │──── user_answer ──────────────►│ Q1 answer
  │──── user_answer ──────────────►│ Q2 answer
  │──── user_answer ──────────────►│ Q3 answer
  │                               │
  │◄─── agent_thinking ───────────│ "Enriching abstract..." [40%]
  │                               │
  │◄─── analysis_progress ────────│ "Novelty scoring..." [60%]
  │◄─── analysis_progress ────────│ "Gap analysis..." [70%]
  │◄─── analysis_progress ────────│ "SWOT analysis..." [80%]
  │◄─── analysis_progress ────────│ "Publishability..." [90%]
  │◄─── analysis_progress ────────│ "Suggestions..." [95%]
  │                               │
  │◄─── analysis_complete ────────│ {result: {...}} [100%]
  │                               │
  └───────────────────────────────┘
```

### Benefits
✅ **Bidirectional communication** - Natural conversation
✅ **Realtime progress** - User sees every step (0-100%)
✅ **Interactive clarification** - Ask/answer in same connection
✅ **No timeout issues** - Streaming updates keep connection alive
✅ **Better UX** - Progress bar, status messages, partial results
✅ **State management** - Session persists throughout conversation

### Code Structure
```
app/api/v1/ws_topic.py
    └── @router.websocket("/ws/topic/analyze")
         ├── Accept connection
         ├── Wait for user_message
         ├── Send session_started
         │
         ├── TopicAnalyzerStreamingService.assess_input()
         │    └── Callback: send agent_thinking updates
         │
         ├── If incomplete:
         │    ├── Send clarification_needed
         │    ├── Wait for user_answer(s)
         │    └── TopicAnalyzerStreamingService.enrich_abstract()
         │
         └── TopicAnalyzerStreamingService.analyze_full()
              └── Callback: send analysis_progress updates
                   ├── [50%] Novelty scoring
                   ├── [70%] Gap analysis
                   ├── [80%] SWOT analysis
                   ├── [90%] Publishability
                   └── [100%] Complete
```

---

## 📊 Feature Comparison

| Feature | REST API | WebSocket |
|---------|----------|-----------|
| **Realtime Updates** | ❌ No | ✅ Yes (0-100%) |
| **Clarification Flow** | ⚠️ Two requests | ✅ Same connection |
| **Progress Visibility** | ❌ None | ✅ Step-by-step |
| **State Management** | ❌ Stateless | ✅ Session-based |
| **Timeout Risk** | ⚠️ High (30-60s) | ✅ Low (streaming) |
| **User Feedback** | ❌ Only at end | ✅ Continuous |
| **Error Handling** | ⚠️ All or nothing | ✅ Recoverable |
| **Partial Results** | ❌ No | ✅ Yes |
| **Connection Type** | Request/Response | Persistent |
| **Best For** | Batch processing | Interactive UI |

---

## 🔧 Implementation Details

### Session Management

**REST (Old):**
```python
# Stateless - no session
def analyze(request: TopicAnalyzeFullRequest):
    if not skip_clarification and incomplete:
        return {"status": "needs_clarification"}
    # User must make new request with answers
```

**WebSocket (New):**
```python
# Stateful - maintains session
session = session_manager.create_session(abstract)
session.assessment = assessment
session.user_answers = {...}
session.enriched_abstract = enriched
session.analysis_results = {...}
```

### Progress Reporting

**REST (Old):**
```python
# No progress updates
result = await service.analyze(abstract)
return result  # After 30-60s
```

**WebSocket (New):**
```python
# Continuous progress updates
await service.analyze_full(
    abstract,
    on_progress=lambda step, msg, progress, partial:
        send_progress(websocket, step, msg, progress, partial)
)

# Server sends:
# [50%] "Analyzing novelty..."
# [70%] "Identifying gaps..."
# [80%] "SWOT analysis..."
# [100%] "Complete!"
```

### Error Handling

**REST (Old):**
```python
# Exception breaks entire request
try:
    result = analyze()
except Exception as e:
    raise HTTPException(500, str(e))
```

**WebSocket (New):**
```python
# Graceful error messages
try:
    result = analyze()
except Exception as e:
    await send_error(
        websocket,
        error="Analysis failed",
        details=str(e),
        recoverable=True  # User can retry
    )
```

---

## 🎯 Migration Path

### Keep Both Endpoints

**REST API** (`POST /api/v1/topic/analyze`) - For:
- Simple scripts
- Batch processing
- No UI needed
- Legacy integrations

**WebSocket** (`WS /api/v1/ws/topic/analyze`) - For:
- Web applications
- Mobile apps
- Interactive interfaces
- Real-time requirements

### Recommended Usage

```python
# Use REST for batch processing
for abstract in abstracts:
    result = requests.post('/api/v1/topic/analyze', json={
        'abstract': abstract,
        'skip_clarification': True  # Auto-infer missing data
    })

# Use WebSocket for interactive UI
ws = new WebSocket('/api/v1/ws/topic/analyze')
ws.onmessage = (event) => {
    // Show progress, handle clarification, display results
}
```

---

## 📈 Performance Impact

### Latency
- **REST**: Single RTT + processing time
- **WebSocket**: Initial handshake + streaming (lower perceived latency)

### Throughput
- **REST**: Better for high-volume batch jobs
- **WebSocket**: Better for real-time user interactions

### Resource Usage
- **REST**: Memory released after response
- **WebSocket**: Session memory held during connection
  - **Mitigation**: Auto-cleanup after 24h of inactivity

---

## 🔒 Security Considerations

### REST API
```python
# Standard HTTP security
- CORS
- Rate limiting
- JWT authentication (if needed)
```

### WebSocket
```python
# Additional considerations
- Connection limits per IP
- Idle timeout (5 min default)
- Message size limits
- Authentication token in initial message
- Heartbeat/ping-pong for keep-alive
```

---

## 🧪 Testing Comparison

### REST Testing
```bash
# Simple curl
curl -X POST http://localhost:8000/api/v1/topic/analyze \
  -H "Content-Type: application/json" \
  -d '{"abstract": "...", "skip_clarification": true}'
```

### WebSocket Testing
```bash
# Requires WebSocket client
wscat -c ws://localhost:8000/api/v1/ws/topic/analyze
# Or use provided HTML/Python clients
```

---

## 📝 Summary

| Aspect | REST | WebSocket |
|--------|------|-----------|
| **Communication** | One-way | Bidirectional |
| **User Experience** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Complexity** | Simple | Moderate |
| **Use Case** | Batch/Scripts | Interactive UI |
| **skip_clarification** | Required flag | Natural flow |
| **Progress** | None | Real-time |
| **Recommendation** | Keep for compatibility | Use for new features |

---

## 🎨 UI Examples

### REST Approach
```
[Submit Button]

[Loading spinner for 30-60s...]

[Results displayed]
```

### WebSocket Approach
```
[Submit Button]

[Progress Bar: 20%] "Assessing completeness..."
[Progress Bar: 30%] "Need more info..."

┌─────────────────────────────┐
│ Please clarify:             │
│ 1. What methodology? [____] │
│ 2. What population?  [____] │
│ [Submit Answers]            │
└─────────────────────────────┘

[Progress Bar: 60%] "Analyzing novelty..."
[Progress Bar: 80%] "SWOT analysis..."
[Progress Bar: 100%] "Complete!"

[Results displayed with animations]
```

---

**Conclusion:** The WebSocket redesign eliminates the need for the `skip_clarification` flag by enabling natural, real-time conversation between client and server, dramatically improving user experience while maintaining backward compatibility through the existing REST endpoint.
