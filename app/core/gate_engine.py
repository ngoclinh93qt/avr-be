"""Gate Engine for Research Formation System.

This module orchestrates the Tier 0-4 constraint checks and
calculates the Integrity Score (IS). All decisions are deterministic.

Key Rules:
- R-01: Rule layer runs BEFORE LLM
- R-03: Gate decision 100% deterministic
- R-09: IS bonus capped at 10 with MAJOR
- R-11: Re-run full check each submission
"""

from typing import Optional
from dataclasses import dataclass

from app.models.schemas import (
    Violation, ResearchBlueprint, ExtractedAttributes
)
from app.models.enums import ViolationSeverity, GateResult, DesignType
from app.rules.constraint_tier0 import check_tier0_violations
from app.rules.constraint_tier1 import check_tier1_violations
from app.rules.constraint_tier2 import check_tier2_violations
from app.rules.constraint_tier3 import check_tier3_violations
from app.rules.constraint_tier4 import check_tier4_violations


# Deduction values by severity
DEDUCTIONS = {
    ViolationSeverity.BLOCK: 100,  # Fatal, fails gate
    ViolationSeverity.MAJOR: 30,   # Significant issue
    ViolationSeverity.WARN: 10,    # Minor issue
}

# Base score
BASE_SCORE = 100

# Maximum score when MAJOR violations exist (R-09)
MAX_SCORE_WITH_MAJOR = 10


@dataclass
class GateCheckResult:
    """Result of gate check."""
    violations: list[Violation]
    integrity_score: float
    gate_result: GateResult
    has_block: bool
    has_major: bool
    tier_summary: dict[int, int]  # tier -> count of violations


def run_gate(
    abstract: str,
    blueprint: Optional[ResearchBlueprint] = None,
    attributes: Optional[ExtractedAttributes] = None,
    rare_disease_confirmed: bool = False
) -> GateCheckResult:
    """
    Run the full gate check on an abstract.

    This function implements R-11: Re-run full check each submission.
    No caching of violations.

    Args:
        abstract: The submitted abstract text
        blueprint: Optional ResearchBlueprint
        attributes: Optional ExtractedAttributes
        rare_disease_confirmed: Whether user confirmed rare disease (R-10)

    Returns:
        GateCheckResult with all violations and final decision
    """
    all_violations = []
    tier_summary = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

    # Get design type if available
    design_type = None
    if attributes and attributes.design_type:
        design_type = attributes.design_type
    elif blueprint and blueprint.design_type:
        design_type = blueprint.design_type

    # Tier 0: Data Integrity
    t0_violations = check_tier0_violations(
        abstract,
        blueprint.model_dump() if blueprint else None
    )
    all_violations.extend(t0_violations)
    tier_summary[0] = len(t0_violations)

    # If Tier 0 has BLOCK, stop here
    has_tier0_block = any(
        v.severity == ViolationSeverity.BLOCK for v in t0_violations
    )

    if not has_tier0_block:
        # Tier 1: Structural Completeness
        t1_violations = check_tier1_violations(
            abstract, blueprint, design_type
        )
        all_violations.extend(t1_violations)
        tier_summary[1] = len(t1_violations)

        # Tier 2: Attribute Consistency
        t2_violations = check_tier2_violations(
            abstract, blueprint, attributes
        )
        all_violations.extend(t2_violations)
        tier_summary[2] = len(t2_violations)

        # Tier 3: Scope Validity
        t3_violations = check_tier3_violations(
            abstract, blueprint, attributes, rare_disease_confirmed
        )
        all_violations.extend(t3_violations)
        tier_summary[3] = len(t3_violations)

        # Tier 4: Statistical Completeness
        t4_violations = check_tier4_violations(
            abstract, blueprint, attributes
        )
        all_violations.extend(t4_violations)
        tier_summary[4] = len(t4_violations)

    # Calculate integrity score
    integrity_score = calculate_integrity_score(all_violations)

    # Determine gate result
    gate_result = determine_gate_result(all_violations, integrity_score)

    # Check flags
    has_block = any(v.severity == ViolationSeverity.BLOCK for v in all_violations)
    has_major = any(v.severity == ViolationSeverity.MAJOR for v in all_violations)

    return GateCheckResult(
        violations=all_violations,
        integrity_score=integrity_score,
        gate_result=gate_result,
        has_block=has_block,
        has_major=has_major,
        tier_summary=tier_summary,
    )


def calculate_integrity_score(violations: list[Violation]) -> float:
    """
    Calculate Integrity Score from violations.

    Implements R-09: IS bonus capped at 10 with MAJOR.

    Args:
        violations: List of violations

    Returns:
        Integrity Score (0-100)
    """
    if not violations:
        return BASE_SCORE

    # Check for blocking violations
    has_block = any(v.severity == ViolationSeverity.BLOCK for v in violations)
    if has_block:
        return 0.0

    # Check for major violations
    has_major = any(v.severity == ViolationSeverity.MAJOR for v in violations)

    # Calculate total deduction
    total_deduction = 0.0
    for v in violations:
        total_deduction += DEDUCTIONS.get(v.severity, 0)

    score = max(0, BASE_SCORE - total_deduction)

    # Apply R-09: cap at 10 if any MAJOR
    if has_major and score > MAX_SCORE_WITH_MAJOR:
        score = MAX_SCORE_WITH_MAJOR

    return round(score, 1)


def determine_gate_result(
    violations: list[Violation],
    integrity_score: float
) -> GateResult:
    """
    Determine gate result from violations and score.

    This is 100% deterministic (R-03).

    Decision logic:
    - REJECT: Any BLOCK violation OR IS < 50
    - PASS: IS >= 80 AND no BLOCK/MAJOR violations
    - REVISE: Everything else

    Args:
        violations: List of violations
        integrity_score: Calculated integrity score

    Returns:
        GateResult enum value
    """
    has_block = any(v.severity == ViolationSeverity.BLOCK for v in violations)
    has_major = any(v.severity == ViolationSeverity.MAJOR for v in violations)

    # REJECT conditions
    if has_block:
        return GateResult.REJECT
    if integrity_score < 50:
        return GateResult.REJECT

    # PASS conditions
    if integrity_score >= 80 and not has_major:
        return GateResult.PASS

    # Everything else is REVISE
    return GateResult.REVISE


def can_proceed_to_outline(gate_result: GateResult) -> bool:
    """
    Check if session can proceed to Phase 3 (Outline).

    Implements R-12: Outline only after Gate pass.

    Args:
        gate_result: Result from gate check

    Returns:
        True if can proceed
    """
    return gate_result == GateResult.PASS


def format_violations_for_display(violations: list[Violation]) -> list[dict]:
    """Format violations for frontend display."""
    result = []

    # Group by severity
    by_severity = {
        ViolationSeverity.BLOCK: [],
        ViolationSeverity.MAJOR: [],
        ViolationSeverity.WARN: [],
    }

    for v in violations:
        by_severity[v.severity].append(v)

    # Format each group
    for severity in [ViolationSeverity.BLOCK, ViolationSeverity.MAJOR, ViolationSeverity.WARN]:
        for v in by_severity[severity]:
            result.append({
                "code": v.code,
                "severity": severity.value,
                "tier": v.tier,
                "message": v.message_vi,
                "path": v.path_vi,
                "context": v.context,
            })

    return result


def get_gate_result_message(result: GateResult, score: float) -> str:
    """Get Vietnamese message for gate result."""
    messages = {
        GateResult.PASS: (
            f"PASS (IS = {score})\n"
            "Abstract dat yeu cau. Co the chuyen sang Phase 3 (Manuscript Outline)."
        ),
        GateResult.REVISE: (
            f"REVISE (IS = {score})\n"
            "Abstract can chinh sua. Xem cac violation ben duoi va sua lai."
        ),
        GateResult.REJECT: (
            f"REJECT (IS = {score})\n"
            "Abstract co van de nghiem trong. Can sua cac loi BLOCK truoc khi tiep tuc."
        ),
    }
    return messages.get(result, f"Result: {result.value} (IS = {score})")


def get_improvement_priority(violations: list[Violation]) -> list[dict]:
    """
    Get prioritized list of improvements needed.

    Returns violations sorted by priority for fixing.
    """
    # Priority order: BLOCK > MAJOR > WARN, then by tier (lower first)
    priority_map = {
        ViolationSeverity.BLOCK: 0,
        ViolationSeverity.MAJOR: 1,
        ViolationSeverity.WARN: 2,
    }

    sorted_violations = sorted(
        violations,
        key=lambda v: (priority_map.get(v.severity, 3), v.tier)
    )

    return [
        {
            "priority": i + 1,
            "code": v.code,
            "message": v.message_vi,
            "path": v.path_vi,
        }
        for i, v in enumerate(sorted_violations)
    ]
