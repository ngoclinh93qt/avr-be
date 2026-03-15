"""Manuscript outline endpoint (Phase 3)."""

from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.domain.search.journal_search import get_journal_by_id
from app.domain.gate.gate_engine import can_proceed_to_outline
from app.models.schemas import (
    OutlineGenerateRequest, OutlineGenerateResponse,
    JournalMetadata, OutlineSection,
    ResearchBlueprint
)
from app.models.enums import SessionStatus, GateResult
from app.llm import get_llm_client
from app.llm.prompts.manuscript_outline import (
    get_manuscript_outline_prompt,
    get_default_outline,
    calculate_total_word_count,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/outline", tags=["outline"])


@router.post("/generate", response_model=OutlineGenerateResponse)
async def generate_outline(
    request: OutlineGenerateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate manuscript outline for a target journal."""
    # Get session
    session = await supabase_service.get_research_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check user tier - Phase 3 is paid
    tier, can_access = await supabase_service.check_user_tier(user_id)
    if not can_access:
        raise HTTPException(
            status_code=403,
            detail="Outline generation requires paid subscription"
        )

    # Check gate result (R-12: Outline only after Gate pass)
    gate_result = session.get("gate_result")
    if not gate_result:
        raise HTTPException(
            status_code=400,
            detail="Must run gate check before generating outline"
        )

    if not can_proceed_to_outline(GateResult(gate_result)):
        raise HTTPException(
            status_code=400,
            detail="Gate check must PASS before generating outline"
        )

    # Get blueprint
    blueprint_data = session.get("blueprint")
    if not blueprint_data:
        raise HTTPException(
            status_code=400,
            detail="No blueprint found"
        )

    try:
        blueprint = ResearchBlueprint(**blueprint_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blueprint: {str(e)}"
        )

    # Get journal metadata
    journal_metadata = None
    journal_meta_response = None

    if request.target_journal_id:
        journal_data = get_journal_by_id(request.target_journal_id)
        if journal_data:
            journal_metadata = journal_data
            journal_meta_response = JournalMetadata(
                journal_id=journal_data["journal_id"],
                name=journal_data["name"],
                issn=journal_data.get("issn"),
                impact_factor=journal_data.get("impact_factor"),
                word_limits=journal_data.get("word_limits"),
                section_requirements=journal_data.get("section_requirements", []),
                author_guidelines_url=journal_data.get("author_guidelines_url"),
            )

    if not journal_meta_response:
        # Create a generic journal metadata
        journal_meta_response = JournalMetadata(
            journal_id=request.target_journal_id or "generic",
            name="Generic Medical Journal",
            issn=None,
            impact_factor=None,
            word_limits={"abstract": 300, "manuscript": 4000},
            section_requirements=["IMRaD format"],
        )

    # Generate outline
    try:
        llm = get_llm_client()
        prompt = get_manuscript_outline_prompt(
            blueprint=blueprint,
            validated_abstract=request.validated_abstract,
            journal_metadata=journal_metadata,
        )

        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=2000,
        )

        # Parse LLM response into structured outline
        outline_text = response.content.strip()
        outline_sections = _parse_outline_response(outline_text, blueprint)

    except Exception as e:
        # Fallback to default outline
        outline_sections = [
            OutlineSection(**s)
            for s in get_default_outline(blueprint, journal_metadata)
        ]

    # Calculate totals
    total_word_count = calculate_total_word_count(
        [s.model_dump() for s in outline_sections]
    )

    # Estimate figures/tables based on design
    estimated_figures = _estimate_figures(blueprint)
    estimated_tables = _estimate_tables(blueprint)
    references_suggested = _estimate_references(blueprint)

    # Save outline as text
    outline_text = _format_outline_as_text(outline_sections)

    # Update session
    await supabase_service.update_research_session(
        request.session_id,
        {
            "target_journal_id": request.target_journal_id,
            "manuscript_outline": outline_text,
            "status": SessionStatus.OUTLINE_READY.value,
        }
    )

    return OutlineGenerateResponse(
        session_id=request.session_id,
        target_journal=journal_meta_response,
        outline=outline_sections,
        total_word_count=total_word_count,
        estimated_figures=estimated_figures,
        estimated_tables=estimated_tables,
        references_suggested=references_suggested,
    )


def _parse_outline_response(text: str, blueprint: ResearchBlueprint) -> list[OutlineSection]:
    """Parse LLM response into OutlineSection objects."""
    # For now, return default outline if parsing fails
    # A more sophisticated parser could be added later
    default = get_default_outline(blueprint, None)
    return [OutlineSection(**s) for s in default]


def _estimate_figures(blueprint: ResearchBlueprint) -> int:
    """Estimate number of figures based on design."""
    from app.models.enums import DesignType

    estimates = {
        DesignType.RCT: 2,  # CONSORT + main result
        DesignType.COHORT_PROSPECTIVE: 2,  # Flow + KM curve
        DesignType.COHORT_RETROSPECTIVE: 1,
        DesignType.CASE_CONTROL: 1,
        DesignType.CROSS_SECTIONAL: 1,
        DesignType.DIAGNOSTIC_ACCURACY: 2,  # Flow + ROC
        DesignType.SYSTEMATIC_REVIEW: 2,  # PRISMA + Forest
        DesignType.META_ANALYSIS: 3,  # PRISMA + Forest + Funnel
    }

    return estimates.get(blueprint.design_type, 1)


def _estimate_tables(blueprint: ResearchBlueprint) -> int:
    """Estimate number of tables based on design."""
    from app.models.enums import DesignType

    estimates = {
        DesignType.RCT: 3,  # Baseline + primary + secondary
        DesignType.COHORT_PROSPECTIVE: 3,
        DesignType.COHORT_RETROSPECTIVE: 2,
        DesignType.CASE_CONTROL: 3,  # Demographics + univariate + multivariate
        DesignType.CROSS_SECTIONAL: 2,
        DesignType.DIAGNOSTIC_ACCURACY: 2,  # Characteristics + 2x2 table
        DesignType.SYSTEMATIC_REVIEW: 2,  # Study characteristics + quality
        DesignType.META_ANALYSIS: 3,
    }

    return estimates.get(blueprint.design_type, 2)


def _estimate_references(blueprint: ResearchBlueprint) -> int:
    """Estimate number of references based on design."""
    from app.models.enums import DesignType

    estimates = {
        DesignType.RCT: 35,
        DesignType.COHORT_PROSPECTIVE: 35,
        DesignType.COHORT_RETROSPECTIVE: 30,
        DesignType.CASE_CONTROL: 30,
        DesignType.CROSS_SECTIONAL: 25,
        DesignType.DIAGNOSTIC_ACCURACY: 30,
        DesignType.SYSTEMATIC_REVIEW: 50,
        DesignType.META_ANALYSIS: 60,
        DesignType.CASE_REPORT: 15,
        DesignType.CASE_SERIES: 20,
    }

    return estimates.get(blueprint.design_type, 30)


def _format_outline_as_text(sections: list[OutlineSection]) -> str:
    """Format outline sections as readable text."""
    lines = []

    for section in sections:
        lines.append(f"## {section.section_name}")
        lines.append(f"Word count: {section.word_count_suggested}")

        if section.key_points:
            lines.append("Key points:")
            for point in section.key_points:
                lines.append(f"  - {point}")

        if section.subsections:
            lines.append("Subsections:")
            for sub in section.subsections:
                lines.append(f"  - {sub}")

        if section.tips:
            lines.append("Tips:")
            for tip in section.tips:
                lines.append(f"  - {tip}")

        lines.append("")

    return "\n".join(lines)
