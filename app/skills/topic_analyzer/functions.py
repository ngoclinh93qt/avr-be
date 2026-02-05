from app.core.llm_router import llm_router
from app.skills.topic_analyzer.prompts import *
import json

# RAG is optional - disable for faster testing
RAG_ENABLED = False


def _format_papers(papers: list, limit: int = 10) -> str:
    if not papers:
        return "No similar papers found in database."
    return "\n".join([
        f"- [{p.get('year', 'N/A')}] {p.get('title', 'Untitled')}: {p.get('abstract', '')[:200]}..."
        for p in papers[:limit]
    ])


async def _get_similar_papers(abstract: str, top_k: int = 20) -> list:
    """Get similar papers from RAG if enabled, otherwise return empty list."""
    if not RAG_ENABLED:
        return []
    try:
        from app.core.rag_engine import rag_engine
        return await rag_engine.find_similar_papers(abstract, top_k=top_k)
    except Exception as e:
        print(f"RAG error: {e}")
        return []


async def score_novelty(abstract: str) -> dict:
    """Score novelty 0-100 with RAG comparison"""
    similar = await _get_similar_papers(abstract, top_k=20)
    prompt = NOVELTY_SCORER_PROMPT.format(
        abstract=abstract,
        num_papers=len(similar),
        similar_papers=_format_papers(similar)
    )
    result = await llm_router.call(prompt, json_output=True)
    result["similar_papers_count"] = len(similar)
    return result


async def analyze_gaps(abstract: str) -> dict:
    """Identify research gaps"""
    similar = await _get_similar_papers(abstract, top_k=15)
    prompt = GAP_ANALYZER_PROMPT.format(
        abstract=abstract,
        similar_papers=_format_papers(similar)
    )
    return await llm_router.call(prompt, json_output=True)


async def perform_swot(
    abstract: str,
    novelty_score: int,
    num_similar: int,
    target_tier: str = "Q2"
) -> dict:
    """SWOT analysis"""
    prompt = SWOT_ANALYZER_PROMPT.format(
        abstract=abstract,
        novelty_score=novelty_score,
        num_similar=num_similar,
        target_tier=target_tier
    )
    return await llm_router.call(prompt, json_output=True)


async def predict_publishability(
    abstract: str,
    novelty_score: int,
    gaps: list,
    strengths: list,
    weaknesses: list
) -> dict:
    """Predict publishability"""
    prompt = PUBLISHABILITY_PREDICTOR_PROMPT.format(
        abstract=abstract,
        novelty_score=novelty_score,
        gaps=json.dumps(gaps, ensure_ascii=False),
        strengths=json.dumps(strengths, ensure_ascii=False),
        weaknesses=json.dumps(weaknesses, ensure_ascii=False)
    )
    return await llm_router.call(prompt, json_output=True)


async def suggest_improvements(
    abstract: str,
    novelty_score: int,
    weaknesses: list,
    target_tier: str
) -> dict:
    """Suggest improvements"""
    prompt = IMPROVEMENT_SUGGESTER_PROMPT.format(
        abstract=abstract,
        novelty_score=novelty_score,
        weaknesses=json.dumps(weaknesses, ensure_ascii=False),
        target_tier=target_tier
    )
    return await llm_router.call(prompt, json_output=True)
