"""Tier 0 Constraints: Data Integrity.

These are fundamental data integrity checks that must pass
before any other validation can proceed.

Codes: D-01, D-02, D-03
"""

from typing import Optional
from app.models.schemas import Violation
from app.models.enums import ViolationSeverity


def check_tier0_violations(
    abstract: str,
    blueprint: Optional[dict] = None
) -> list[Violation]:
    """
    Check Tier 0 (Data Integrity) violations.

    Args:
        abstract: The submitted abstract text
        blueprint: Optional blueprint dictionary

    Returns:
        List of Violation objects
    """
    violations = []

    # D-01: Abstract is empty or too short
    if not abstract or len(abstract.strip()) < 50:
        violations.append(Violation(
            code="D-01",
            tier=0,
            severity=ViolationSeverity.BLOCK,
            message_vi="Abstract qua ngan hoac rong",
            path_vi=(
                "Abstract can co it nhat 50 ky tu. "
                "Hay viet lai abstract day du hon voi cac thanh phan: "
                "Muc tieu, Phuong phap, Ket qua (du kien), Ket luan."
            ),
            context={"length": len(abstract.strip()) if abstract else 0}
        ))

    # D-02: Abstract is too long
    if abstract and len(abstract.strip()) > 5000:
        violations.append(Violation(
            code="D-02",
            tier=0,
            severity=ViolationSeverity.WARN,
            message_vi="Abstract qua dai (> 5000 ky tu)",
            path_vi=(
                "Abstract thuong nen gioi han duoi 500 tu (~3000 ky tu). "
                "Abstract hien tai qua dai, hay rut gon cac phan khong can thiet."
            ),
            context={"length": len(abstract.strip())}
        ))

    # D-03: No meaningful content (placeholder detection)
    placeholder_patterns = [
        "[insert", "[placeholder", "[to be", "[tbd]",
        "lorem ipsum", "xxx", "___",
        "[dien vao", "[them vao", "[can bo sung"
    ]
    abstract_lower = abstract.lower() if abstract else ""
    found_placeholders = [p for p in placeholder_patterns if p in abstract_lower]

    if found_placeholders:
        violations.append(Violation(
            code="D-03",
            tier=0,
            severity=ViolationSeverity.BLOCK,
            message_vi="Abstract chua noi dung placeholder",
            path_vi=(
                "Phat hien cac placeholder trong abstract. "
                "Hay thay the tat ca cac phan [xxx], [insert], [TBD] "
                "bang noi dung thuc te."
            ),
            context={"placeholders": found_placeholders}
        ))

    # Additional D-0x checks for blueprint if provided
    if blueprint:
        # D-04: Blueprint has no population
        if not blueprint.get("population"):
            violations.append(Violation(
                code="D-04",
                tier=0,
                severity=ViolationSeverity.BLOCK,
                message_vi="Thieu dan so nghien cuu trong blueprint",
                path_vi=(
                    "Blueprint can co phan Population (dan so nghien cuu). "
                    "Hay xac dinh ro: ai se duoc nghien cuu? "
                    "(vi du: benh nhi 5-15 tuoi, benh nhan dai thao duong type 2)"
                ),
                context={}
            ))

        # D-05: Blueprint has no primary outcome
        if not blueprint.get("primary_outcome"):
            violations.append(Violation(
                code="D-05",
                tier=0,
                severity=ViolationSeverity.BLOCK,
                message_vi="Thieu ket qua chinh trong blueprint",
                path_vi=(
                    "Blueprint can co Primary Outcome (ket qua chinh). "
                    "Hay xac dinh ro: ket qua chinh se do luong la gi? "
                    "(vi du: ty le tu vong 30 ngay, thoi gian song them)"
                ),
                context={}
            ))

    return violations


def has_blocking_tier0(violations: list[Violation]) -> bool:
    """Check if there are any blocking Tier 0 violations."""
    return any(
        v.tier == 0 and v.severity == ViolationSeverity.BLOCK
        for v in violations
    )
