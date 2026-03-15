"""Design rules for research type inference.

This module provides keyword-based heuristics to infer research design type
and structural requirements without LLM involvement.
"""

import re
import unicodedata
import logging
from typing import Optional

from app.models.enums import DesignType

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Strip Vietnamese diacritics and lowercase for keyword matching."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Design Rules Dictionary
# ═══════════════════════════════════════════════════════════════════════════════

DESIGN_RULES: dict[DesignType, dict] = {
    # Interventional Studies
    DesignType.RCT: {
        "keywords": [
            "randomized", "randomised", "rct", "random allocation",
            "ngau nhien", "phan bo ngau nhien", "thu nghiem lam sang",
            "clinical trial", "randomization", "placebo-controlled"
        ],
        "required_elements": [
            "population", "intervention", "comparator", "primary_endpoint",
            "sample_size", "randomization_method", "blinding"
        ],
        "structural": {
            "needs_arms": True,
            "needs_blinding": True,
            "needs_allocation": True,
            "min_arms": 2
        }
    },
    DesignType.QUASI_EXPERIMENTAL: {
        "keywords": [
            "quasi-experimental", "quasi experimental", "non-randomized intervention",
            "can thiet khong ngau nhien", "nghien cuu can thiep"
        ],
        "required_elements": [
            "population", "intervention", "comparator", "primary_endpoint",
            "sample_size"
        ],
        "structural": {
            "needs_arms": True,
            "needs_blinding": False,
            "min_arms": 2
        }
    },
    DesignType.BEFORE_AFTER: {
        "keywords": [
            "before-after", "before and after", "pre-post", "pre post",
            "truoc-sau", "truoc sau", "so sanh truoc va sau"
        ],
        "required_elements": [
            "population", "intervention", "primary_endpoint", "sample_size",
            "timepoints"
        ],
        "structural": {
            "needs_arms": False,
            "needs_timepoints": True
        }
    },

    # Observational Studies
    DesignType.COHORT_PROSPECTIVE: {
        "keywords": [
            "prospective cohort", "cohort study followed", "follow-up study",
            "theo doi tien cu", "nghien cuu thuan tap tien cu"
        ],
        "required_elements": [
            "population", "exposure", "primary_endpoint", "sample_size",
            "follow_up_duration"
        ],
        "structural": {
            "needs_followup": True,
            "direction": "prospective"
        }
    },
    DesignType.COHORT_RETROSPECTIVE: {
        "keywords": [
            "retrospective cohort", "historical cohort", "chart review cohort",
            "hoi cuu", "nghien cuu thuan tap hoi cuu", "ho so benh an",
            # Also match without the doubled vowel in case of variant spellings
            "hoi cu", "nghien cuu thuan tap hoi cu",
        ],
        "required_elements": [
            "population", "exposure", "primary_endpoint", "sample_size",
            "data_source"
        ],
        "structural": {
            "direction": "retrospective"
        }
    },
    DesignType.CASE_CONTROL: {
        "keywords": [
            "case-control", "case control", "cases and controls",
            "benh-chung", "benh chung", "nhom benh va nhom chung"
        ],
        "required_elements": [
            "case_definition", "control_definition", "exposure",
            "matching_criteria", "sample_size"
        ],
        "structural": {
            "needs_matching": True,
            "needs_case_control_ratio": True
        }
    },
    DesignType.CROSS_SECTIONAL: {
        "keywords": [
            "cross-sectional", "cross sectional", "prevalence study",
            "survey", "descriptive study",
            "cat ngang", "nghien cuu cat ngang", "ty le hien mac"
        ],
        "required_elements": [
            "population", "primary_endpoint", "sample_size"
        ],
        "structural": {
            "single_timepoint": True
        }
    },
    DesignType.CASE_SERIES: {
        "keywords": [
            "case series", "series of cases", "consecutive cases",
            "loat ca", "chuoi ca benh", "bao cao loat ca"
        ],
        "required_elements": [
            "case_definition", "sample_size", "primary_endpoint"
        ],
        "structural": {
            "min_cases": 3
        }
    },
    DesignType.CASE_REPORT: {
        "keywords": [
            "case report", "single case", "case presentation",
            "bao cao ca benh", "trinh bay ca benh", "ca lam sang"
        ],
        "required_elements": [
            "case_presentation", "key_findings"
        ],
        "structural": {
            "single_case": True
        }
    },

    # Diagnostic/Prognostic
    DesignType.DIAGNOSTIC_ACCURACY: {
        "keywords": [
            "diagnostic accuracy", "sensitivity specificity",
            "roc curve", "auc", "diagnostic test",
            "do chinh xac chan doan", "do nhay", "do dac hieu"
        ],
        "required_elements": [
            "index_test", "reference_standard", "population",
            "sample_size", "spectrum_of_disease"
        ],
        "structural": {
            "needs_reference_standard": True,
            "needs_blinding_to_reference": True
        }
    },
    DesignType.PROGNOSTIC: {
        "keywords": [
            "prognostic", "prognosis", "predictors of outcome",
            "survival analysis", "cox regression",
            "tien luong", "yeu to tien luong"
        ],
        "required_elements": [
            "population", "prognostic_factors", "outcome",
            "follow_up_duration", "sample_size"
        ],
        "structural": {
            "needs_followup": True,
            "needs_event_count": True
        }
    },

    # Synthesis Studies
    DesignType.SYSTEMATIC_REVIEW: {
        "keywords": [
            "systematic review", "prisma", "systematic search",
            "tong quan he thong", "tim kiem he thong"
        ],
        "required_elements": [
            "search_strategy", "databases", "inclusion_criteria",
            "exclusion_criteria", "quality_assessment"
        ],
        "structural": {
            "needs_protocol": True,
            "needs_search_strategy": True
        }
    },
    DesignType.META_ANALYSIS: {
        "keywords": [
            "meta-analysis", "meta analysis", "pooled analysis",
            "phan tich gop", "phan tich tong hop"
        ],
        "required_elements": [
            "search_strategy", "databases", "inclusion_criteria",
            "statistical_method", "heterogeneity_assessment"
        ],
        "structural": {
            "needs_protocol": True,
            "needs_statistical_pooling": True
        }
    },
    DesignType.SCOPING_REVIEW: {
        "keywords": [
            "scoping review", "scoping study", "mapping review",
            "tong quan pham vi"
        ],
        "required_elements": [
            "search_strategy", "databases", "inclusion_criteria",
            "charting_form"
        ],
        "structural": {
            "needs_protocol": True
        }
    },

    # Qualitative
    DesignType.QUALITATIVE: {
        "keywords": [
            "qualitative", "interview", "focus group", "thematic analysis",
            "grounded theory", "phenomenology",
            "nghien cuu dinh tinh", "phong van", "nhom tap trung"
        ],
        "required_elements": [
            "population", "data_collection_method", "analysis_approach",
            "saturation_strategy"
        ],
        "structural": {
            "qualitative_approach": True
        }
    },
    DesignType.MIXED_METHODS: {
        "keywords": [
            "mixed methods", "mixed-methods", "quan-qual",
            "ket hop dinh luong dinh tinh"
        ],
        "required_elements": [
            "quantitative_component", "qualitative_component",
            "integration_approach"
        ],
        "structural": {
            "needs_integration": True
        }
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# Design Inference Functions
# ═══════════════════════════════════════════════════════════════════════════════

def infer_design_type(text: str) -> DesignType:
    """
    Infer research design type from text using keyword matching.

    This is a deterministic, rule-based function - no LLM involved.
    Matches against Vietnamese and English keywords.

    Args:
        text: User input or abstract text

    Returns:
        DesignType enum value, defaults to UNKNOWN if no match
    """
    # Normalize to strip Vietnamese diacritics before matching
    text_norm = _normalize(text)

    logger.info("[DESIGN] Input normalized: %r", text_norm[:200])

    # Score each design type
    scores: dict[DesignType, int] = {}

    for design_type, rules in DESIGN_RULES.items():
        score = 0
        for keyword in rules["keywords"]:
            # Exact phrase match gets highest score
            if keyword in text_norm:
                score += 2
            else:
                # Partial word match only for words with ≥ 7 characters.
                # Vietnamese common words like "nghien", "thuan", "truoc"
                # are only 5-6 chars but match coincidentally across phrases.
                meaningful_words = [w for w in keyword.split() if len(w) >= 7]
                if meaningful_words and any(w in text_norm for w in meaningful_words):
                    score += 1
        if score > 0:
            scores[design_type] = score
            logger.debug("[DESIGN] %s score=%d", design_type.value, score)

    if not scores:
        logger.info("[DESIGN] No design type matched — returning UNKNOWN")
        return DesignType.UNKNOWN

    best = max(scores, key=scores.get)
    logger.info("[DESIGN] Inferred: %s (score=%d, all=%s)", best.value, scores[best], scores)
    return best



def infer_design_structural(design_type: DesignType) -> dict:
    """
    Get structural requirements for a design type.

    Args:
        design_type: The inferred design type

    Returns:
        Dictionary of structural requirements
    """
    if design_type in DESIGN_RULES:
        return DESIGN_RULES[design_type].get("structural", {})
    return {}


def get_required_elements(design_type: DesignType) -> list[str]:
    """
    Get required elements for a design type.

    Args:
        design_type: The inferred design type

    Returns:
        List of required element names
    """
    if design_type in DESIGN_RULES:
        return DESIGN_RULES[design_type].get("required_elements", [])
    return ["population", "primary_endpoint", "sample_size"]  # Minimum defaults


def check_design_completeness(
    design_type: DesignType,
    attributes: dict
) -> tuple[bool, list[str]]:
    """
    Check if all required elements for a design type are present.

    Args:
        design_type: The research design type
        attributes: Extracted attributes dictionary

    Returns:
        Tuple of (is_complete, missing_elements)
    """
    required = get_required_elements(design_type)
    missing = []

    for element in required:
        if element not in attributes or attributes[element] is None:
            missing.append(element)
        elif isinstance(attributes[element], str) and not attributes[element].strip():
            missing.append(element)

    return len(missing) == 0, missing


def get_design_display_name(design_type: DesignType) -> str:
    """Get Vietnamese display name for design type."""
    display_names = {
        DesignType.RCT: "Thu nghiem lam sang ngau nhien co doi chung (RCT)",
        DesignType.QUASI_EXPERIMENTAL: "Nghien cuu can thiep khong ngau nhien",
        DesignType.BEFORE_AFTER: "Nghien cuu truoc-sau",
        DesignType.COHORT_PROSPECTIVE: "Nghien cuu thuan tap tien cu",
        DesignType.COHORT_RETROSPECTIVE: "Nghien cuu thuan tap hoi cu",
        DesignType.CASE_CONTROL: "Nghien cuu benh-chung",
        DesignType.CROSS_SECTIONAL: "Nghien cuu cat ngang",
        DesignType.CASE_SERIES: "Bao cao loat ca",
        DesignType.CASE_REPORT: "Bao cao ca benh",
        DesignType.DIAGNOSTIC_ACCURACY: "Nghien cuu do chinh xac chan doan",
        DesignType.PROGNOSTIC: "Nghien cuu tien luong",
        DesignType.SYSTEMATIC_REVIEW: "Tong quan he thong",
        DesignType.META_ANALYSIS: "Phan tich gop",
        DesignType.SCOPING_REVIEW: "Tong quan pham vi",
        DesignType.QUALITATIVE: "Nghien cuu dinh tinh",
        DesignType.MIXED_METHODS: "Nghien cuu ket hop",
        DesignType.UNKNOWN: "Chua xac dinh",
    }
    return display_names.get(design_type, str(design_type.value))
