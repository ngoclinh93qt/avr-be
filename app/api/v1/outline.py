"""Manuscript outline endpoint (Phase 3)."""

from fastapi import APIRouter, HTTPException, Depends

from app.core.supabase_client import supabase_service
from app.domain.search.journal_search import get_journal_by_id
from app.domain.gate.gate_engine import can_proceed_to_outline
from app.models.schemas import (
    OutlineGenerateRequest, OutlineGenerateResponse,
    JournalMetadata, OutlineSection,
    ResearchBlueprint, ExtractedAttributes
)
from app.models.enums import SessionStatus, GateResult
from app.llm import get_llm_client
from app.llm.prompts.manuscript_outline import (
    get_manuscript_outline_prompt,
    get_default_outline,
    parse_llm_outline_response,
    calculate_total_word_count,
    generate_title_suggestion,
    get_submission_checklist,
    SYSTEM_PROMPT
)
from app.api.deps import get_current_user_id, check_token_quota

router = APIRouter(prefix="/outline", tags=["outline"])


@router.post("/generate", response_model=OutlineGenerateResponse)
async def generate_outline(
    request: OutlineGenerateRequest,
    user_id: str = Depends(check_token_quota),
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
            status_code=402,
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

    # Resolve validated_abstract from request or session
    validated_abstract = (
        request.validated_abstract
        or session.get("submitted_abstract")
        or session.get("estimated_abstract")
        or ""
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

    # Get extracted attributes (richer per-field data from conversation)
    extracted_attrs: ExtractedAttributes | None = None
    attrs_data = session.get("extracted_attributes")
    if attrs_data and isinstance(attrs_data, dict):
        try:
            extracted_attrs = ExtractedAttributes(**attrs_data)
        except Exception:
            pass

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
    outline_sections = None
    try:
        llm = get_llm_client()
        prompt = get_manuscript_outline_prompt(
            blueprint=blueprint,
            extracted_attrs=extracted_attrs,
            validated_abstract=validated_abstract,
            journal_metadata=journal_metadata,
            custom_instructions=request.custom_instructions,
        )

        llm_response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=4000,
            user_id=user_id,
        )

        # Parse the JSON output from LLM
        parsed = parse_llm_outline_response(llm_response.content.strip())
        if parsed:
            outline_sections = [OutlineSection(**s) for s in parsed]

    except Exception:
        pass  # Fallback below

    if not outline_sections:
        # Fallback: blueprint-informed default outline (no LLM)
        outline_sections = [
            OutlineSection(**s)
            for s in get_default_outline(blueprint, journal_metadata, extracted_attrs)
        ]

    # Calculate totals
    total_word_count = calculate_total_word_count(
        [s.model_dump() for s in outline_sections]
    )

    # Estimate figures/tables based on design
    estimated_figures = _estimate_figures(blueprint)
    estimated_tables = _estimate_tables(blueprint)
    references_suggested = _estimate_references(blueprint)

    # Generate title suggestion and submission checklist
    title_suggestion = generate_title_suggestion(blueprint)
    checklist_type = _get_checklist_type(blueprint)
    submission_checklist = get_submission_checklist(
        checklist_type,
        journal_meta_response.name,
    )

    response = OutlineGenerateResponse(
        session_id=request.session_id,
        target_journal=journal_meta_response,
        outline=outline_sections,
        total_word_count=total_word_count,
        estimated_figures=estimated_figures,
        estimated_tables=estimated_tables,
        references_suggested=references_suggested,
        title_suggestion=title_suggestion,
        submission_checklist=submission_checklist,
        checklist_type=checklist_type,
    )

    # Store full structured response as JSON for frontend retrieval
    import json
    from app.models.enums import Phase
    outline_json = json.dumps(response.model_dump(), default=str)

    # Update session — advance phase to phase3
    await supabase_service.update_research_session(
        request.session_id,
        {
            "target_journal_id": request.target_journal_id,
            "manuscript_outline": outline_json,
            "status": SessionStatus.OUTLINE_READY.value,
            "phase": Phase.PHASE3.value,
        }
    )

    return response


def _get_checklist_type(blueprint: ResearchBlueprint) -> str:
    """Map design type to reporting checklist type."""
    from app.models.enums import DesignType
    mapping = {
        DesignType.RCT: "CONSORT",
        DesignType.QUASI_EXPERIMENTAL: "CONSORT",
        DesignType.BEFORE_AFTER: "CONSORT",
        DesignType.DIAGNOSTIC_ACCURACY: "STARD",
        DesignType.SYSTEMATIC_REVIEW: "PRISMA",
        DesignType.META_ANALYSIS: "PRISMA",
        DesignType.SCOPING_REVIEW: "PRISMA",
        DesignType.CASE_REPORT: "CARE",
    }
    return mapping.get(blueprint.design_type, "STROBE")



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
