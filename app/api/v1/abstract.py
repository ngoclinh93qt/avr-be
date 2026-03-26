"""Abstract generation endpoint — Phase 1."""

import logging

from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger(__name__)

from app.core.supabase_client import supabase_service
from app.core.ws_manager import ws_manager
from app.core.ws_manager import ws_manager
from app.domain.search.journal_search import search_journals
from app.domain.search.pubmed_search import search_pubmed, build_pubmed_query
from app.domain.search.roadmap_generator import generate_roadmap
from app.models.schemas import (
    AbstractGenerateRequest, AbstractGenerateResponse,
    JournalSuggestion, ResearchBlueprint,
    NoveltyCheck, NoveltyPaper,
)
from app.models.enums import SessionStatus, ConversationState
from app.llm import get_llm_client
from app.llm.prompts.abstract_gen import (
    get_abstract_generation_prompt,
    validate_generated_abstract,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/abstract", tags=["abstract"])


# ─── Progress emitter ─────────────────────────────────────────────────────────

async def _emit(user_id: str, step: str, status: str, **data):
    """Push a processing_update event to the user's active WebSocket."""
    try:
        await ws_manager.broadcast_to_user(user_id, {
            "type": "processing_update",
            "step": step,
            "status": status,
            **data,
        })
    except Exception:
        pass  # Non-critical — WS may not be connected


# ─── Novelty commentary prompt ────────────────────────────────────────────────

_NOVELTY_COMMENTARY_SYSTEM = (
    "Bạn là mentor nghiên cứu y khoa. Trả lời bằng tiếng Việt, ngắn gọn, thực tế. "
    "Không phán xét, không block — chỉ hướng dẫn."
)

def _build_novelty_commentary_prompt(count: int, papers: list, blueprint) -> str:
    papers_text = ""
    for i, p in enumerate(papers[:3], 1):
        papers_text += f"{i}. {p.get('authors', '')} ({p.get('year', '')}) — \"{p.get('title', '')}\" — {p.get('journal', '')}\n"

    return (
        f"PubMed search cho nghiên cứu về '{blueprint.intervention_or_exposure}' "
        f"trên '{blueprint.population}' với outcome '{blueprint.primary_outcome}' "
        f"trả về ~{count} bài tương tự.\n\n"
        f"Top bài gần nhất:\n{papers_text or '(không tìm thấy bài cụ thể)'}\n\n"
        f"Thiết kế nghiên cứu: {blueprint.design_type}. "
        f"Setting: {blueprint.setting or 'không rõ'}.\n\n"
        "Viết nhận xét ngắn (2–4 câu) bằng tiếng Việt: "
        "(1) đánh giá mức độ cạnh tranh của chủ đề, "
        "(2) gợi ý 1–2 điểm khác biệt có thể khai thác để tăng tính mới. "
        "Kết bằng 1 câu ngắn trấn an: nhiều journal vẫn nhận replication study từ population khác."
    )


async def _generate_novelty_commentary(count: int, papers: list, blueprint, llm) -> str:
    """Generate a short novelty commentary using LLM (light call, ~200 tokens)."""
    try:
        prompt = _build_novelty_commentary_prompt(count, papers, blueprint)
        response = await llm.complete(
            prompt=prompt,
            system_prompt=_NOVELTY_COMMENTARY_SYSTEM,
            temperature=0.5,
            max_tokens=250,
        )
        return response.content.strip()
    except Exception:
        # Fallback template commentary
        if count < 5:
            return (
                "Chủ đề này chưa có nhiều nghiên cứu — cơ hội tốt để đóng góp. "
                "Nhiều journal chào đón nghiên cứu đầu tiên từ population của bạn."
            )
        elif count < 30:
            return (
                f"Đã có ~{count} bài tương tự. "
                "Cần làm rõ điểm khác biệt (population, setting, hoặc outcome) trong Introduction. "
                "Nhiều journal vẫn nhận replication study từ population khác."
            )
        else:
            return (
                f"Chủ đề đã được nghiên cứu nhiều (~{count} bài). "
                "Để tăng tính mới: focus vào population Việt Nam, thêm secondary outcome chưa ai đo, "
                "hoặc thu hẹp subgroup cụ thể. "
                "Nhiều journal vẫn nhận replication study từ population khác nếu address novelty rõ trong Introduction."
            )


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=AbstractGenerateResponse)
async def generate_abstract(
    request: AbstractGenerateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate estimated abstract, novelty check, journal suggestions, and research roadmap."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if session.get("conversation_state") != ConversationState.COMPLETE.value:
        raise HTTPException(
            status_code=400,
            detail="Conversation must be COMPLETE before generating abstract"
        )

    blueprint_data = session.get("blueprint")
    if not blueprint_data:
        raise HTTPException(
            status_code=400,
            detail="No blueprint found. Complete the conversation first."
        )

    try:
        blueprint = ResearchBlueprint(**blueprint_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid blueprint data: {str(e)}")

    # Rate limiting (free tier) — non-critical, skip if profile lookup fails
    try:
        tier, _ = await supabase_service.check_user_tier(user_id)
        if tier == "free":
            runs_today = await supabase_service.increment_runs_today(user_id)
            if runs_today > 3:
                raise HTTPException(
                    status_code=429,
                    detail="Daily limit reached for free tier (3 abstracts/day)"
                )
    except HTTPException:
        raise  # Re-raise 429 rate limit
    except Exception as e:
        logger.warning("[ABSTRACT] Rate limit check failed (non-critical), continuing: %s", e)

    llm = get_llm_client()
    logger.info("[ABSTRACT] Starting generation for session=%s  design=%s  population=%r",
                request.session_id, blueprint.design_type, blueprint.population)

    # ── 1. Generate abstract ──────────────────────────────────────────────────
    try:
        await _emit(user_id, "abstract", "running")
        prompt = get_abstract_generation_prompt(blueprint)
        logger.info("[ABSTRACT] Calling LLM for abstract (blueprint fields: %s)",
                    {k: v for k, v in blueprint.model_dump().items() if v})
        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=1500,
        )
        estimated_abstract = response.content.strip()
        logger.info("[ABSTRACT] LLM abstract generated — %d chars", len(estimated_abstract))

        is_valid, issues = validate_generated_abstract(estimated_abstract)
        if not is_valid:
            logger.warning("[ABSTRACT] Validation issues: %s", issues)
            warning_text = "\n\n[Cảnh báo tự động: " + "; ".join(issues) + "]"
            estimated_abstract += warning_text

        await _emit(user_id, "abstract", "done", chars=len(estimated_abstract))

    except Exception as e:
        await _emit(user_id, "abstract", "error", message=str(e))
        logger.exception("[ABSTRACT] Failed to generate abstract for session=%s", request.session_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate abstract: {str(e)}")

    # ── 2. PubMed novelty check ───────────────────────────────────────────────
    novelty_check: NoveltyCheck | None = None
    try:
        query = await build_pubmed_query(blueprint, llm)
        logger.info("[ABSTRACT] PubMed search query: %s", query)
        await _emit(user_id, "pubmed", "running", query=query)

        pubmed_result = await search_pubmed(query, max_results=5)
        logger.info("[ABSTRACT] PubMed result: count=%s  papers=%d",
                    pubmed_result.get("count"), len(pubmed_result.get("papers", [])))

        papers = [
            NoveltyPaper(
                title=p["title"],
                authors=p["authors"],
                year=p["year"],
                journal=p["journal"],
                pmid=p.get("pmid"),
            )
            for p in pubmed_result.get("papers", [])
        ]

        commentary = await _generate_novelty_commentary(
            count=pubmed_result["count"],
            papers=pubmed_result.get("papers", []),
            blueprint=blueprint,
            llm=llm,
        )
        logger.info("[ABSTRACT] Novelty commentary: %r", commentary[:100])

        novelty_check = NoveltyCheck(
            count=pubmed_result["count"],
            papers=papers,
            commentary=commentary,
            keywords_used=[pubmed_result.get("query_used", query)],
        )
        await _emit(user_id, "pubmed", "done",
                    count=pubmed_result["count"],
                    papers=len(papers),
                    query=pubmed_result.get("query_used", query))
    except Exception as e:
        await _emit(user_id, "pubmed", "error", message=str(e))
        logger.warning("[ABSTRACT] Novelty check failed (non-critical): %s", e)

    # ── 3. Journal suggestions ────────────────────────────────────────────────
    journal_suggestions: list[JournalSuggestion] = []
    try:
        search_query = (
            f"{blueprint.population} {blueprint.primary_outcome} "
            f"{blueprint.intervention_or_exposure}"
        )
        logger.info("[ABSTRACT] Journal search query: %r", search_query[:100])
        await _emit(user_id, "journals", "running", query=search_query[:80])

        journals = search_journals(
            query=search_query,
            specialty=blueprint.specialty,
            top_k=5,
        )
        logger.info("[ABSTRACT] Journals found: %d", len(journals))
        journal_suggestions = [
            JournalSuggestion(
                journal_id=j["journal_id"],
                name=j["name"],
                issn=j.get("issn"),
                impact_factor=j.get("impact_factor"),
                specialty=j.get("specialty"),
                open_access=j.get("open_access"),
                abstract_limit=j.get("abstract_limit"),
                citation_style=j.get("citation_style"),
                similarity_score=j["similarity_score"],
            )
            for j in journals
        ]
        await _emit(user_id, "journals", "done", count=len(journal_suggestions))
    except Exception as e:
        await _emit(user_id, "journals", "error", message=str(e))
        logger.warning("[ABSTRACT] Journal search failed (non-critical): %s", e)

    # ── 4. Research roadmap ───────────────────────────────────────────────────
    try:
        await _emit(user_id, "roadmap", "running")
        roadmap = generate_roadmap(blueprint)
        logger.info("[ABSTRACT] Roadmap generated: design=%s  steps=%d",
                    roadmap.design_type if roadmap else None,
                    len(roadmap.steps) if roadmap else 0)
        await _emit(user_id, "roadmap", "done",
                    steps=len(roadmap.steps) if roadmap else 0)
    except Exception as e:
        await _emit(user_id, "roadmap", "error", message=str(e))
        logger.warning("[ABSTRACT] Roadmap generation failed (non-critical): %s", e)
        roadmap = None

    # ── 5. Persist to session ─────────────────────────────────────────────────
    
    # Inject reports into blueprint for persistence
    if blueprint:
        bp_dict = blueprint.model_dump()
        bp_dict["novelty_check"] = novelty_check.model_dump() if novelty_check else None
        bp_dict["roadmap"] = roadmap.model_dump() if roadmap else None
    else:
        bp_dict = None

    await supabase_service.update_research_session(
        request.session_id,
        {
            "estimated_abstract": estimated_abstract,
            "journal_suggestions": [j.model_dump() for j in journal_suggestions],
            "status": SessionStatus.ABSTRACT_READY.value,
            "blueprint": bp_dict
        }
    )

    await supabase_service.append_abstract_version(request.session_id, estimated_abstract)

    await supabase_service.add_conversation_turn(
        session_id=request.session_id,
        role="assistant",
        content=(
            f"Đã tạo Abstract ước tính. "
            f"Kiểm tra độ mới: ~{novelty_check.count if novelty_check else '?'} bài tương tự trên PubMed. "
            f"Gợi ý {len(journal_suggestions)} tạp chí phù hợp."
        ),
    )

    await _emit(user_id, "all", "done")

    return AbstractGenerateResponse(
        session_id=request.session_id,
        estimated_abstract=estimated_abstract,
        journal_suggestions=journal_suggestions,
        blueprint=blueprint,
        status=SessionStatus.ABSTRACT_READY,
        novelty_check=novelty_check,
        roadmap=roadmap,
    )
