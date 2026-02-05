from app.core.llm_router import llm_router
from app.core.vietglish_processor import vietglish_processor
from app.db.repositories.journal_repo import journal_repo
from app.skills.manuscript_strategist.prompts import *
import json


async def generate_roadmap(abstract: str, journal_name: str) -> dict:
    """Generate section roadmap"""
    journal = await journal_repo.get_by_name(journal_name)
    prompt = SECTION_ROADMAP_PROMPT.format(
        abstract=abstract,
        journal_name=journal_name,
        word_limit=journal.get("word_limit", 5000),
        structure=journal.get("structure", "IMRAD"),
        citation_style=journal.get("citation_style", "Vancouver")
    )
    return await llm_router.call(prompt, json_output=True)


async def fix_vietglish(text: str) -> dict:
    """Fix Viet-glish errors"""
    # Rule-based first
    rule_errors = vietglish_processor.analyze(text)
    
    # LLM comprehensive fix
    prompt = VIETGLISH_FIXER_PROMPT.format(text=text)
    result = await llm_router.call(prompt, json_output=True)
    result["rule_based_errors"] = rule_errors
    return result


async def calibrate_tone(
    text: str,
    journal_name: str,
    field: str = "Medicine"
) -> dict:
    """Adjust academic tone"""
    prompt = TONE_CALIBRATOR_PROMPT.format(
        text=text,
        journal_name=journal_name,
        field=field
    )
    return await llm_router.call(prompt, json_output=True)


async def plan_citations(
    abstract: str,
    journal_name: str,
    section: str
) -> dict:
    """Plan citation strategy"""
    prompt = CITATION_STRATEGIST_PROMPT.format(
        abstract=abstract,
        journal_name=journal_name,
        section=section
    )
    return await llm_router.call(prompt, json_output=True)


async def simulate_reviewer(
    section: str,
    content: str,
    journal_name: str
) -> dict:
    """Simulate peer review"""
    prompt = REVIEWER_SIMULATOR_PROMPT.format(
        journal_name=journal_name,
        section=section,
        content=content
    )
    return await llm_router.call(prompt, json_output=True)


async def generate_template(study_type: str) -> dict:
    """Generate reporting template"""
    prompt = TEMPLATE_GENERATOR_PROMPT.format(study_type=study_type)
    return await llm_router.call(prompt, json_output=True)
