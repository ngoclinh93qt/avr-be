from app.core.llm_router import llm_router
from app.core.embedding_service import embedding_service
from app.db.repositories.journal_repo import journal_repo
from app.skills.journal_matcher.prompts import *
import json


def _format_journals(journals: list) -> str:
    return "\n".join([
        f"- {j['name']} | IF: {j['impact_factor']} | APC: ${j['apc']} | OA: {j['open_access']}"
        for j in journals
    ])


async def rank_journals(
    abstract: str,
    max_apc: int = 500,
    min_if: float = 0.5,
    max_if: float = 5.0,
    oa_only: bool = False,
    specialty: str = None
) -> dict:
    """Rank journals by fit"""
    # Filter from database
    candidates = await journal_repo.filter_journals(
        max_apc=max_apc, min_if=min_if, max_if=max_if,
        oa_only=oa_only, specialty=specialty
    )
    
    # Semantic ranking
    scored = []
    for j in candidates:
        score = embedding_service.similarity(abstract, j["scope"])
        scored.append({**j, "semantic_score": score})
    
    top50 = sorted(scored, key=lambda x: x["semantic_score"], reverse=True)[:50]
    
    # LLM refinement
    prompt = JOURNAL_RANKER_PROMPT.format(
        abstract=abstract,
        journals=_format_journals(top50),
        max_apc=max_apc,
        min_if=min_if,
        max_if=max_if,
        oa_only=oa_only,
        specialty=specialty or "General"
    )
    return await llm_router.call(prompt, json_output=True)


async def check_predatory(
    journal_name: str,
    publisher: str = None,
    issn: str = None
) -> dict:
    """Check predatory status"""
    # Database lookups
    in_doaj = await journal_repo.check_doaj(journal_name)
    in_scopus = await journal_repo.check_scopus(journal_name)
    in_pubmed = await journal_repo.check_pubmed(journal_name)
    in_bealls = await journal_repo.check_bealls(journal_name)
    
    # Quick verdict
    if in_bealls:
        return {"is_predatory": True, "confidence": 0.95, "risk_level": "danger", "recommendation": "avoid"}
    if in_doaj and in_scopus and in_pubmed:
        return {"is_predatory": False, "confidence": 0.95, "risk_level": "safe", "recommendation": "proceed"}
    
    # LLM for unclear cases
    prompt = PREDATORY_DETECTOR_PROMPT.format(
        journal_name=journal_name,
        publisher=publisher or "Unknown",
        issn=issn or "Unknown",
        in_doaj=in_doaj, in_scopus=in_scopus,
        in_pubmed=in_pubmed, in_bealls=in_bealls
    )
    return await llm_router.call(prompt, json_output=True)


async def calculate_apc(journals: list, budget: int) -> dict:
    """Calculate costs and waivers"""
    prompt = APC_CALCULATOR_PROMPT.format(
        journals=_format_journals(journals),
        budget=budget
    )
    return await llm_router.call(prompt, json_output=True)


async def estimate_timeline(journals: list, deadline: str = None) -> dict:
    """Estimate timeline"""
    prompt = TIMELINE_ESTIMATOR_PROMPT.format(
        journals=_format_journals(journals),
        deadline=deadline or "No specific deadline"
    )
    return await llm_router.call(prompt, json_output=True)


async def plan_backup(
    primary_journal: str,
    match_score: int,
    alternatives: list
) -> dict:
    """Create backup plan"""
    prompt = BACKUP_PLANNER_PROMPT.format(
        primary_journal=primary_journal,
        match_score=match_score,
        alternatives=_format_journals(alternatives)
    )
    return await llm_router.call(prompt, json_output=True)
