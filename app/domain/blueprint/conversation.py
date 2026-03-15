"""Conversation state machine for Research Formation System.

This module implements the deterministic state machine that controls
conversation flow. State transitions are rule-based, not LLM-driven (R-02).
"""

from typing import Optional
from dataclasses import dataclass, field

from app.models.enums import ConversationState, DesignType
from app.models.schemas import ExtractedAttributes, ResearchBlueprint
from app.rules.design_rules import get_required_elements, check_design_completeness
from app.rules.feasibility_rules import check_feasibility, has_blocking_issues


# Minimum required elements for any study
MINIMUM_REQUIRED = [
    "population",
    "primary_endpoint",
]

# Maximum clarifying turns before forcing completion
MAX_CLARIFYING_TURNS = 10


@dataclass
class CompletenessResult:
    """Result of completeness evaluation."""
    is_complete: bool = False
    missing_elements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    completeness_score: float = 0.0
    next_state: ConversationState = ConversationState.CLARIFYING


def evaluate_completeness(
    attributes: ExtractedAttributes,
    design_type: Optional[DesignType] = None,
    clarifying_turns: int = 0
) -> CompletenessResult:
    """
    Evaluate completeness of extracted attributes.

    This is a deterministic function - no LLM involvement.
    State transitions are based purely on rules.

    Args:
        attributes: Extracted attributes from conversation
        design_type: Inferred design type (if known)
        clarifying_turns: Number of clarifying turns so far

    Returns:
        CompletenessResult with state recommendation
    """
    result = CompletenessResult()
    attr_dict = attributes.model_dump()

    # Get required elements based on design
    if design_type and design_type != DesignType.UNKNOWN:
        required = get_required_elements(design_type)
    else:
        required = MINIMUM_REQUIRED.copy()
        # Add sample_size for quantitative studies
        if design_type not in [DesignType.QUALITATIVE, DesignType.CASE_REPORT]:
            required.append("sample_size")

    # Check each required element
    for element in required:
        value = attr_dict.get(element)
        if value is None or (isinstance(value, str) and not value.strip()):
            result.missing_elements.append(element)

    # Calculate completeness score
    total_required = len(required)
    found = total_required - len(result.missing_elements)
    result.completeness_score = (found / total_required * 100) if total_required > 0 else 0

    # Check for feasibility issues
    feasibility_issues = check_feasibility(attr_dict)
    blocking = [i for i in feasibility_issues if has_blocking_issues([i])]

    if blocking:
        result.blocking_issues = [i.message_vi for i in blocking]

    # Add warnings for non-blocking issues
    for issue in feasibility_issues:
        if issue not in blocking:
            result.warnings.append(issue.message_vi)

    # Determine next state
    if result.blocking_issues:
        result.next_state = ConversationState.BLOCKED
        result.is_complete = False
    elif not result.missing_elements:
        result.next_state = ConversationState.COMPLETE
        result.is_complete = True
    elif clarifying_turns >= MAX_CLARIFYING_TURNS:
        # Force completion after max turns
        result.next_state = ConversationState.COMPLETE
        result.is_complete = True
        result.warnings.append(
            f"Dat gioi han {MAX_CLARIFYING_TURNS} luot hoi. "
            "Chuyen sang tao blueprint voi thong tin hien co."
        )
    else:
        result.next_state = ConversationState.CLARIFYING
        result.is_complete = False

    return result


def get_missing_element_questions(
    missing_elements: list[str],
    design_type: Optional[DesignType] = None
) -> list[dict]:
    """
    Generate questions for missing elements.

    Args:
        missing_elements: List of missing element names
        design_type: Inferred design type

    Returns:
        List of question dictionaries with priority
    """
    # Question templates by element
    questions = {
        "population": {
            "question": "Dan so nghien cuu la ai? (vi du: benh nhi 5-15 tuoi bi viem ruot thua)",
            "priority": 1,
            "element": "population"
        },
        "sample_size": {
            "question": "Co mau du kien la bao nhieu benh nhan?",
            "priority": 2,
            "element": "sample_size"
        },
        "primary_endpoint": {
            "question": "Ket qua chinh (primary endpoint) muon do la gi? (vi du: ty le tu vong 30 ngay, thoi gian nam vien)",
            "priority": 3,
            "element": "primary_endpoint"
        },
        "intervention": {
            "question": "Can thiep/phuong phap dieu tri la gi?",
            "priority": 4,
            "element": "intervention"
        },
        "comparator": {
            "question": "Nhom doi chung/so sanh la gi? (vi du: placebo, dieu tri chuan)",
            "priority": 5,
            "element": "comparator"
        },
        "exposure": {
            "question": "Yeu to phoi nhiem/nguy co can danh gia la gi?",
            "priority": 4,
            "element": "exposure"
        },
        "follow_up_duration": {
            "question": "Thoi gian theo doi du kien la bao lau?",
            "priority": 6,
            "element": "follow_up_duration"
        },
        "reference_standard": {
            "question": "Tieu chuan vang (gold standard) de so sanh la gi?",
            "priority": 3,
            "element": "reference_standard"
        },
        "search_strategy": {
            "question": "Chien luoc tim kiem (databases, keywords) la gi?",
            "priority": 2,
            "element": "search_strategy"
        },
        "databases": {
            "question": "Se tim kiem tren nhung co so du lieu nao? (PubMed, Embase, Cochrane...)",
            "priority": 3,
            "element": "databases"
        },
        "case_definition": {
            "question": "Dinh nghia ca benh (case) la gi?",
            "priority": 2,
            "element": "case_definition"
        },
        "control_definition": {
            "question": "Dinh nghia nhom chung (control) la gi?",
            "priority": 3,
            "element": "control_definition"
        },
        "matching_criteria": {
            "question": "Tieu chi ghep cap (matching) la gi? (tuoi, gioi, benh nen...)",
            "priority": 4,
            "element": "matching_criteria"
        },
        "inclusion_criteria": {
            "question": "Tieu chi lua chon (inclusion) la gi?",
            "priority": 3,
            "element": "inclusion_criteria"
        },
        "exclusion_criteria": {
            "question": "Tieu chi loai tru (exclusion) la gi?",
            "priority": 4,
            "element": "exclusion_criteria"
        },
        "randomization_method": {
            "question": "Phuong phap ngau nhien hoa la gi? (simple, block, stratified)",
            "priority": 5,
            "element": "randomization_method"
        },
        "blinding": {
            "question": "Nghien cuu co lam mu khong? (open-label, single-blind, double-blind)",
            "priority": 6,
            "element": "blinding"
        },
    }

    result = []
    for element in missing_elements:
        if element in questions:
            result.append(questions[element])
        else:
            # Generic question for unknown elements
            result.append({
                "question": f"Hay mo ta {element.replace('_', ' ')}",
                "priority": 10,
                "element": element
            })

    # Sort by priority
    result.sort(key=lambda x: x["priority"])

    return result


def should_ask_clarification(
    completeness: CompletenessResult,
    clarifying_turns: int
) -> bool:
    """
    Determine if we should ask clarifying questions.

    Args:
        completeness: Result from evaluate_completeness
        clarifying_turns: Number of turns so far

    Returns:
        True if should ask more questions
    """
    if completeness.is_complete:
        return False
    if completeness.next_state == ConversationState.BLOCKED:
        return False
    if clarifying_turns >= MAX_CLARIFYING_TURNS:
        return False
    if len(completeness.missing_elements) == 0:
        return False
    return True


def get_clarification_intro(
    missing_count: int,
    clarifying_turns: int
) -> str:
    """
    Get appropriate intro message for clarification.

    Args:
        missing_count: Number of missing elements
        clarifying_turns: Number of turns so far

    Returns:
        Intro message in Vietnamese
    """
    if clarifying_turns == 0:
        if missing_count <= 2:
            return "Cam on ban da chia se y tuong. Chi can them mot vai thong tin nua:"
        else:
            return "Cam on ban da chia se y tuong. De xay dung Research Blueprint, toi can bo sung mot so thong tin:"
    elif clarifying_turns < 3:
        return "Cam on. Toi can them:"
    elif clarifying_turns < 6:
        remaining = MAX_CLARIFYING_TURNS - clarifying_turns
        return f"Gan xong roi. Con {remaining} cau hoi nua:"
    else:
        return f"Cau hoi cuoi:"


def format_blocking_message(
    blocking_issues: list[str]
) -> str:
    """
    Format blocking issues into a message.

    Args:
        blocking_issues: List of blocking issue messages

    Returns:
        Formatted Vietnamese message
    """
    if not blocking_issues:
        return ""

    intro = "Phat hien van de can giai quyet truoc khi tiep tuc:\n\n"
    issues = "\n".join(f"- {issue}" for issue in blocking_issues)
    outro = "\n\nHay dieu chinh de cuoc va gui lai."

    return intro + issues + outro


def can_generate_blueprint(
    attributes: ExtractedAttributes
) -> tuple[bool, list[str]]:
    """
    Check if we have enough information to generate a blueprint.

    Args:
        attributes: Extracted attributes

    Returns:
        Tuple of (can_generate, reasons_why_not)
    """
    attr_dict = attributes.model_dump()
    reasons = []

    # Absolute minimums
    if not attr_dict.get("population"):
        reasons.append("Thieu dan so nghien cuu (population)")

    if not attr_dict.get("primary_endpoint"):
        reasons.append("Thieu ket qua chinh (primary endpoint)")

    # Need either intervention or exposure
    if not attr_dict.get("intervention") and not attr_dict.get("exposure"):
        # Unless it's a descriptive study
        design = attr_dict.get("design_type")
        if design not in [
            DesignType.CROSS_SECTIONAL,
            DesignType.CASE_SERIES,
            DesignType.CASE_REPORT
        ]:
            reasons.append("Thieu can thiep hoac yeu to phoi nhiem")

    return len(reasons) == 0, reasons


def can_generate_abstract(
    blueprint: Optional[ResearchBlueprint]
) -> tuple[bool, list[str]]:
    """
    Check if we can generate an abstract from blueprint.

    Args:
        blueprint: Research blueprint

    Returns:
        Tuple of (can_generate, reasons_why_not)
    """
    if not blueprint:
        return False, ["Chua co blueprint"]

    reasons = []
    bp_dict = blueprint.model_dump()

    if not bp_dict.get("population"):
        reasons.append("Blueprint thieu population")

    if not bp_dict.get("primary_outcome"):
        reasons.append("Blueprint thieu primary outcome")

    if not bp_dict.get("design_type"):
        reasons.append("Blueprint thieu design type")

    return len(reasons) == 0, reasons
