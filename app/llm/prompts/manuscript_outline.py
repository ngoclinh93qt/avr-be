"""Manuscript outline generation prompts.

This prompt generates a journal-specific manuscript outline.
Only available after Gate PASS (R-12).
"""

from typing import Optional
from app.models.schemas import ResearchBlueprint
from app.rules.design_rules import get_design_display_name


SYSTEM_PROMPT = """Ban la chuyen gia viet bai bao y khoa voi nhieu nam kinh nghiem.

NHIEM VU:
Tao manuscript outline chi tiet, phu hop voi tap chi muc tieu.

YEU CAU:
- Tuan thu author guidelines cua tap chi
- Phu hop voi thiet ke nghien cuu
- Chi tiet, cu the, co the thuc hien ngay

NGON NGU:
- Tieng Viet cho noi dung
- Thuat ngu tieng Anh trong ngoac khi can"""


# Section templates by design type
SECTION_TEMPLATES = {
    "rct": [
        "Title",
        "Abstract",
        "Introduction",
        "Methods/Patients and Methods",
        "- Study design and setting",
        "- Participants (eligibility, recruitment)",
        "- Randomization and blinding",
        "- Intervention",
        "- Outcomes",
        "- Sample size calculation",
        "- Statistical analysis",
        "Results",
        "- Participant flow (CONSORT diagram)",
        "- Baseline characteristics",
        "- Primary outcome",
        "- Secondary outcomes",
        "- Adverse events",
        "Discussion",
        "Conclusion",
        "References",
    ],
    "cohort": [
        "Title",
        "Abstract",
        "Introduction",
        "Methods",
        "- Study design and setting",
        "- Participants",
        "- Variables (exposure, outcome, covariates)",
        "- Data sources",
        "- Bias control",
        "- Sample size",
        "- Statistical analysis",
        "Results",
        "- Participants",
        "- Descriptive data",
        "- Outcome data",
        "- Main results",
        "- Other analyses",
        "Discussion",
        "Conclusion",
        "References",
    ],
    "diagnostic": [
        "Title",
        "Abstract",
        "Introduction",
        "Methods",
        "- Study design",
        "- Participants",
        "- Index test",
        "- Reference standard",
        "- Test execution",
        "- Statistical analysis",
        "Results",
        "- Participants",
        "- Test results",
        "- Diagnostic accuracy (Se, Sp, PPV, NPV)",
        "- ROC analysis",
        "Discussion",
        "Conclusion",
        "References",
    ],
    "systematic_review": [
        "Title",
        "Abstract",
        "Introduction",
        "Methods",
        "- Protocol and registration",
        "- Eligibility criteria",
        "- Information sources",
        "- Search strategy",
        "- Selection process",
        "- Data collection",
        "- Risk of bias assessment",
        "- Synthesis methods",
        "Results",
        "- Study selection (PRISMA flow)",
        "- Study characteristics",
        "- Risk of bias in studies",
        "- Results of individual studies",
        "- Synthesis results",
        "Discussion",
        "Conclusion",
        "References",
    ],
}


def get_manuscript_outline_prompt(
    blueprint: ResearchBlueprint,
    validated_abstract: str,
    journal_metadata: Optional[dict] = None
) -> str:
    """
    Generate prompt for manuscript outline.

    Args:
        blueprint: Research Blueprint
        validated_abstract: Abstract that passed gate
        journal_metadata: Target journal metadata

    Returns:
        Prompt string for LLM
    """
    design_name = get_design_display_name(blueprint.design_type)

    # Get section template
    design_key = _get_design_key(blueprint.design_type.value)
    sections = SECTION_TEMPLATES.get(design_key, SECTION_TEMPLATES["cohort"])

    journal_info = ""
    if journal_metadata:
        journal_info = f"""
TAP CHI MUC TIEU:
- Ten: {journal_metadata.get('name', 'Khong xac dinh')}
- Impact Factor: {journal_metadata.get('impact_factor', 'N/A')}
- Gioi han tu: {journal_metadata.get('word_limits', 'Khong xac dinh')}
- Yeu cau dac biet: {journal_metadata.get('section_requirements', [])}
"""

    prompt = f"""RESEARCH BLUEPRINT:
- Thiet ke: {design_name}
- Dan so: {blueprint.population}
- Can thiep/Phoi nhiem: {blueprint.intervention_or_exposure}
- Ket qua chinh: {blueprint.primary_outcome}
- Co mau: n = {blueprint.sample_size}
- Phuong phap thong ke: {blueprint.statistical_approach or 'Chua xac dinh'}

ABSTRACT DA DUYET:
{validated_abstract[:500]}...
{journal_info}

MAU CAU TRUC:
{chr(10).join(sections)}

---

NHIEM VU:
Tao manuscript outline chi tiet voi cac yeu cau:

1. Moi section can co:
   - So tu de xuat
   - Key points (3-5 diem)
   - Subsections (neu can)
   - Tips viet

2. Phu hop voi:
   - Thiet ke nghien cuu ({design_name})
   - Tap chi muc tieu (neu co)
   - STROBE/CONSORT/PRISMA guidelines

3. Bao gom:
   - So luong hinh/bang de xuat
   - So luong references de xuat
   - Tong so tu de xuat

HAY TAO OUTLINE CHI TIET:"""

    return prompt


def _get_design_key(design_type: str) -> str:
    """Map design type to template key."""
    mappings = {
        "rct": "rct",
        "quasi_experimental": "rct",
        "before_after": "rct",
        "cohort_prospective": "cohort",
        "cohort_retrospective": "cohort",
        "case_control": "cohort",
        "cross_sectional": "cohort",
        "diagnostic_accuracy": "diagnostic",
        "systematic_review": "systematic_review",
        "meta_analysis": "systematic_review",
        "scoping_review": "systematic_review",
    }
    return mappings.get(design_type, "cohort")


def get_default_outline(
    blueprint: ResearchBlueprint,
    journal_metadata: Optional[dict] = None
) -> list[dict]:
    """
    Generate default outline without LLM.

    Args:
        blueprint: Research Blueprint
        journal_metadata: Optional journal metadata

    Returns:
        List of outline sections
    """
    design_key = _get_design_key(blueprint.design_type.value)

    # Default word counts by section
    word_counts = {
        "Title": "15-20 words",
        "Abstract": "250-300 words",
        "Introduction": "400-600 words",
        "Methods": "800-1200 words",
        "Results": "600-1000 words",
        "Discussion": "800-1200 words",
        "Conclusion": "150-250 words",
        "References": "30-50 references",
    }

    # Get sections
    sections = SECTION_TEMPLATES.get(design_key, SECTION_TEMPLATES["cohort"])

    outline = []
    current_section = None

    for item in sections:
        if item.startswith("- "):
            # Subsection
            if current_section:
                current_section["subsections"].append(item[2:])
        else:
            # Main section
            if current_section:
                outline.append(current_section)

            current_section = {
                "section_name": item,
                "word_count_suggested": word_counts.get(item, "See guidelines"),
                "key_points": _get_key_points(item, blueprint),
                "subsections": [],
                "tips": _get_tips(item, blueprint.design_type.value),
            }

    if current_section:
        outline.append(current_section)

    return outline


def _get_key_points(section: str, blueprint: ResearchBlueprint) -> list[str]:
    """Get key points for a section."""
    key_points = {
        "Introduction": [
            "Background and context",
            "Gap in knowledge",
            "Study rationale",
            "Objectives",
        ],
        "Methods": [
            f"Study design: {blueprint.design_type.value}",
            f"Population: {blueprint.population}",
            f"Primary outcome: {blueprint.primary_outcome}",
            "Statistical analysis plan",
        ],
        "Results": [
            "Participant flow",
            "Baseline characteristics",
            "Primary outcome results",
            "Secondary outcomes",
        ],
        "Discussion": [
            "Key findings",
            "Comparison with literature",
            "Strengths and limitations",
            "Implications",
        ],
    }
    return key_points.get(section, [])


def _get_tips(section: str, design_type: str) -> list[str]:
    """Get tips for a section."""
    tips = {
        "Introduction": [
            "Start broad, narrow to specific gap",
            "Cite recent relevant studies",
            "State objectives clearly at the end",
        ],
        "Methods": [
            f"Follow reporting guidelines for {design_type}",
            "Be specific and reproducible",
            "Justify sample size",
        ],
        "Results": [
            "Present data, don't interpret",
            "Use tables for complex data",
            "Report effect sizes with CI",
        ],
        "Discussion": [
            "Start with main finding",
            "Compare don't just cite",
            "Be balanced about limitations",
        ],
    }
    return tips.get(section, [])


def calculate_total_word_count(outline: list[dict]) -> str:
    """Calculate estimated total word count from outline."""
    total_min = 0
    total_max = 0

    for section in outline:
        word_range = section.get("word_count_suggested", "0")
        # Parse "X-Y words" format
        import re
        match = re.search(r"(\d+)-(\d+)", word_range)
        if match:
            total_min += int(match.group(1))
            total_max += int(match.group(2))

    return f"{total_min}-{total_max} words"
