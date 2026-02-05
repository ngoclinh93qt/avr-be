"""
REST API endpoints for Topic Analyzer (non-realtime).

For realtime WebSocket API, see ws_topic.py
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import TopicAnalyzeFullRequest, TopicAnalyzeFullResponse
from app.services.topic_analyzer import TopicAnalyzerService

router = APIRouter()
service = TopicAnalyzerService()


@router.post("/analyze", response_model=TopicAnalyzeFullResponse)
async def analyze_topic(request: TopicAnalyzeFullRequest):
    """
    Full Topic Analyzer Pipeline (REST - Non-realtime).

    Pipeline Steps:
    1. INPUT CLARIFICATION: Assess completeness, generate questions if needed.
    2. PARALLEL ANALYSIS: Run novelty scoring, gap analysis, and SWOT in parallel.
    3. SEQUENTIAL ANALYSIS: Predict publishability, then suggest improvements.
    4. RESPONSE AGGREGATION: Combine all results.

    If the input is incomplete and `skip_clarification` is False, the response
    will have status "needs_clarification" with questions for the user.

    Note: For realtime progress updates, use the WebSocket endpoint at
    /api/v1/ws/topic/analyze instead.
    """
    try:
        result = await service.analyze(
            abstract=request.abstract,
            language=request.language,
            user_responses=request.user_responses,
            skip_clarification=request.skip_clarification,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
