"""Tier 1 Constraints: Structural Completeness.

These check that all required structural elements are present
based on the research design type.

Codes: S-01 to S-05
"""

import re
from typing import Optional
from app.models.schemas import Violation, ResearchBlueprint
from app.models.enums import ViolationSeverity, DesignType


# Required sections by design type
REQUIRED_SECTIONS = {
    DesignType.RCT: [
        "objective", "population", "intervention", "comparator",
        "primary_outcome", "randomization", "sample_size"
    ],
    DesignType.COHORT_PROSPECTIVE: [
        "objective", "population", "exposure", "primary_outcome",
        "follow_up", "sample_size"
    ],
    DesignType.COHORT_RETROSPECTIVE: [
        "objective", "population", "exposure", "primary_outcome",
        "data_source", "sample_size"
    ],
    DesignType.CASE_CONTROL: [
        "objective", "case_definition", "control_definition",
        "exposure", "matching", "sample_size"
    ],
    DesignType.CROSS_SECTIONAL: [
        "objective", "population", "primary_outcome", "sample_size"
    ],
    DesignType.DIAGNOSTIC_ACCURACY: [
        "objective", "population", "index_test", "reference_standard",
        "sample_size"
    ],
    DesignType.SYSTEMATIC_REVIEW: [
        "objective", "search_strategy", "databases",
        "inclusion_criteria", "quality_assessment"
    ],
    DesignType.META_ANALYSIS: [
        "objective", "search_strategy", "databases",
        "inclusion_criteria", "statistical_method"
    ],
}

# Section Vietnamese names for error messages
SECTION_NAMES_VI = {
    "objective": "Muc tieu nghien cuu",
    "population": "Dan so nghien cuu",
    "intervention": "Can thiep",
    "comparator": "Nhom doi chung",
    "primary_outcome": "Ket qua chinh",
    "secondary_outcome": "Ket qua phu",
    "randomization": "Phuong phap ngau nhien hoa",
    "sample_size": "Co mau",
    "exposure": "Yeu to phoi nhiem",
    "follow_up": "Thoi gian theo doi",
    "data_source": "Nguon du lieu",
    "case_definition": "Dinh nghia ca benh",
    "control_definition": "Dinh nghia nhom chung",
    "matching": "Tieu chi ghep cap",
    "index_test": "Test chan doan can danh gia",
    "reference_standard": "Tieu chuan vang",
    "search_strategy": "Chien luoc tim kiem",
    "databases": "Co so du lieu",
    "inclusion_criteria": "Tieu chi lua chon",
    "quality_assessment": "Danh gia chat luong",
    "statistical_method": "Phuong phap thong ke gop",
}


def check_tier1_violations(
    abstract: str,
    blueprint: Optional[ResearchBlueprint] = None,
    design_type: Optional[DesignType] = None
) -> list[Violation]:
    """
    Check Tier 1 (Structural Completeness) violations.

    Args:
        abstract: The submitted abstract text
        blueprint: Optional ResearchBlueprint object
        design_type: Research design type

    Returns:
        List of Violation objects
    """
    violations = []

    if not design_type:
        design_type = DesignType.UNKNOWN

    # S-01: Missing required sections based on design
    if design_type in REQUIRED_SECTIONS:
        required = REQUIRED_SECTIONS[design_type]
        missing = _check_missing_sections(abstract, blueprint, required)

        if missing:
            violations.append(Violation(
                code="S-01",
                tier=1,
                severity=ViolationSeverity.MAJOR if len(missing) <= 2 else ViolationSeverity.BLOCK,
                message_vi=f"Thieu {len(missing)} thanh phan bat buoc cho {design_type.value}",
                path_vi=(
                    f"Cac thanh phan can bo sung:\n" +
                    "\n".join(f"- {SECTION_NAMES_VI.get(m, m)}" for m in missing)
                ),
                context={"missing": missing, "design_type": design_type.value}
            ))

    # S-02: No clear objective/aim
    if not _has_objective(abstract):
        violations.append(Violation(
            code="S-02",
            tier=1,
            severity=ViolationSeverity.MAJOR,
            message_vi="Thieu muc tieu nghien cuu ro rang",
            path_vi=(
                "Abstract can co cau muc tieu ro rang. Nen bat dau bang:\n"
                "- 'Muc tieu: ...' hoac 'Objective: ...'\n"
                "- 'Nghien cuu nay nham...' hoac 'This study aims to...'"
            ),
            context={}
        ))

    # S-03: No methods section
    if not _has_methods(abstract):
        violations.append(Violation(
            code="S-03",
            tier=1,
            severity=ViolationSeverity.MAJOR,
            message_vi="Thieu phan phuong phap",
            path_vi=(
                "Abstract can mo ta phuong phap nghien cuu:\n"
                "- Thiet ke nghien cuu (RCT, cohort, cross-sectional...)\n"
                "- Dan so va co mau\n"
                "- Cach thu thap va phan tich du lieu"
            ),
            context={}
        ))

    # S-04: No results section (for estimated abstracts, should be placeholder)
    if not _has_results_section(abstract):
        violations.append(Violation(
            code="S-04",
            tier=1,
            severity=ViolationSeverity.WARN,
            message_vi="Thieu phan ket qua",
            path_vi=(
                "Abstract can co phan Ket qua. Voi abstract du kien, "
                "hay ghi '[PLACEHOLDER - Ket qua se duoc dien sau khi co du lieu]'"
            ),
            context={}
        ))

    # S-05: No conclusion
    if not _has_conclusion(abstract):
        violations.append(Violation(
            code="S-05",
            tier=1,
            severity=ViolationSeverity.WARN,
            message_vi="Thieu phan ket luan",
            path_vi=(
                "Abstract can co phan Ket luan. Voi abstract du kien, "
                "hay ghi ket luan du kien dua tren gia thuyet nghien cuu."
            ),
            context={}
        ))

    return violations


def _check_missing_sections(
    abstract: str,
    blueprint: Optional[ResearchBlueprint],
    required: list[str]
) -> list[str]:
    """Check which required sections are missing."""
    missing = []
    abstract_lower = abstract.lower() if abstract else ""

    # Map of section -> keywords to detect
    section_keywords = {
        "objective": ["muc tieu", "objective", "aim", "nham", "purpose"],
        "population": ["benh nhan", "patient", "doi tuong", "subject", "participant"],
        "intervention": ["can thiep", "intervention", "treatment", "dieu tri"],
        "comparator": ["doi chung", "control", "placebo", "comparator", "so sanh voi"],
        "primary_outcome": ["ket qua chinh", "primary outcome", "primary endpoint"],
        "randomization": ["ngau nhien", "random", "allocation"],
        "sample_size": [r"n\s*=\s*\d+", r"\d+\s*(benh nhan|patient|ca|case)"],
        "exposure": ["phoi nhiem", "exposure", "risk factor", "yeu to nguy co"],
        "follow_up": ["theo doi", "follow-?up", "thang", "nam"],
        "data_source": ["ho so", "record", "database", "du lieu"],
        "case_definition": ["dinh nghia ca", "case definition"],
        "control_definition": ["dinh nghia chung", "control definition"],
        "matching": ["ghep cap", "match"],
        "index_test": ["test", "xet nghiem", "chan doan"],
        "reference_standard": ["tieu chuan vang", "reference", "gold standard"],
        "search_strategy": ["tim kiem", "search", "query"],
        "databases": ["pubmed", "embase", "cochrane", "co so du lieu"],
        "inclusion_criteria": ["tieu chi", "criteria", "eligible"],
        "quality_assessment": ["chat luong", "quality", "risk of bias"],
        "statistical_method": ["thong ke", "meta", "pooled", "gop"],
    }

    for section in required:
        keywords = section_keywords.get(section, [section])
        found = False

        for keyword in keywords:
            if re.search(keyword, abstract_lower, re.IGNORECASE):
                found = True
                break

        # Also check blueprint if available
        if blueprint and not found:
            blueprint_dict = blueprint.model_dump() if hasattr(blueprint, 'model_dump') else blueprint
            if section in blueprint_dict and blueprint_dict[section]:
                found = True

        if not found:
            missing.append(section)

    return missing


def _has_objective(abstract: str) -> bool:
    """Check if abstract has a clear objective."""
    patterns = [
        r"(muc tieu|objective|aim|purpose|goal)",
        r"(nghien cuu nay nham|this study aims)",
        r"(de xac dinh|to determine|to evaluate|to assess)",
        r"(chung toi|we) (nghien cuu|studied|investigated|examined)",
    ]
    abstract_lower = abstract.lower()
    return any(re.search(p, abstract_lower) for p in patterns)


def _has_methods(abstract: str) -> bool:
    """Check if abstract has methods section."""
    patterns = [
        r"(phuong phap|method|material)",
        r"(thiet ke|design|study design)",
        r"(thu thap|collected|recruited)",
        r"(phan tich|analyzed|analysis)",
        r"(nghien cuu (cat ngang|thuan tap|hoi cu))",
        r"(rct|randomized|cohort|cross-?sectional|case-?control)",
    ]
    abstract_lower = abstract.lower()
    return any(re.search(p, abstract_lower) for p in patterns)


def _has_results_section(abstract: str) -> bool:
    """Check if abstract has results section or placeholder."""
    patterns = [
        r"(ket qua|result)",
        r"\[placeholder",
        r"(chung toi|we) (tim thay|found|observed)",
        r"(cho thay|showed|demonstrated)",
        r"(p\s*[<>=]\s*0\.\d+)",
        r"(\d+%|\d+\.\d+%)",
    ]
    abstract_lower = abstract.lower()
    return any(re.search(p, abstract_lower) for p in patterns)


def _has_conclusion(abstract: str) -> bool:
    """Check if abstract has conclusion."""
    patterns = [
        r"(ket luan|conclusion)",
        r"(tom lai|in summary|in conclusion)",
        r"(nghien cuu nay cho thay|this study (shows|suggests|demonstrates))",
        r"(chung toi ket luan|we conclude)",
    ]
    abstract_lower = abstract.lower()
    return any(re.search(p, abstract_lower) for p in patterns)
