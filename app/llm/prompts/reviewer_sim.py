"""Reviewer simulation prompts.

This prompt simulates a journal reviewer providing feedback.
Implements R-07: Reviewer sim doesn't see abstract (only violations + gate_result).
"""

from typing import Optional
from app.models.schemas import Violation
from app.models.enums import GateResult


SYSTEM_PROMPT = """Ban la reviewer khoa hoc giau kinh nghiem tai mot tap chi y khoa uy tin.

VAI TRO:
- Cung cap feedback mang tinh xay dung
- Chi ra cac van de va goi y cach sua
- Giu giong chuyen nghiep, ho tro nguoi viet

PHONG CACH:
- Than thien nhung nghiem tuc
- Cu the, co vi du minh hoa
- Uu tien nhung van de quan trong nhat

LUU Y QUAN TRONG (R-07):
- Ban KHONG duoc nhin thay noi dung abstract
- Ban chi nhan duoc danh sach violations va ket qua gate
- Feedback dua tren violations, KHONG phan tich abstract truc tiep"""


def get_reviewer_simulation_prompt(
    violations: list[Violation],
    gate_result: GateResult,
    integrity_score: float,
    gate_run_count: int = 1
) -> str:
    """
    Generate prompt for reviewer simulation.

    Args:
        violations: List of violations from gate check
        gate_result: Gate decision
        integrity_score: Integrity Score
        gate_run_count: Number of times gate has been run

    Returns:
        Prompt string for LLM
    """
    # Format violations by severity
    violations_text = _format_violations(violations)

    # Generate context based on run count
    context = ""
    if gate_run_count > 1:
        context = f"Day la lan chay gate thu {gate_run_count}. Tac gia dang co gang sua lai."

    prompt = f"""KET QUA DANH GIA:
- Gate Result: {gate_result.value}
- Integrity Score: {integrity_score}/100
- So luong violations: {len(violations)}
{f"- {context}" if context else ""}

DANH SACH VIOLATIONS:
{violations_text if violations_text else "Khong co violation nao."}

---

NHIEM VU:
Viet feedback nhu mot reviewer cho tac gia. Feedback can:

1. TOM TAT: 2-3 cau danh gia tong quan

2. VAN DE CHINH (neu co): Liet ke 2-3 van de quan trong nhat can sua

3. GOI Y CU THE: Cho moi van de chinh, goi y cach sua

4. DIEM TICH CUC (neu co): Neu co gi tot, hay khen

5. KET LUAN: Khuyen nghi tiep theo (sua lai, bo sung, submit...)

LUU Y:
- KHONG de cap den abstract cu the (ban khong nhin thay)
- Chi dua tren violations duoc cung cap
- Giu giong than thien, ho tro
- Viet bang tieng Viet

HAY VIET FEEDBACK:"""

    return prompt


def _format_violations(violations: list[Violation]) -> str:
    """Format violations for prompt."""
    if not violations:
        return ""

    # Group by severity
    by_severity = {"BLOCK": [], "MAJOR": [], "WARN": []}

    for v in violations:
        severity = v.severity.value
        by_severity[severity].append(v)

    lines = []

    # BLOCK first
    if by_severity["BLOCK"]:
        lines.append("=== LOI NGHIEM TRONG (BLOCK) ===")
        for v in by_severity["BLOCK"]:
            lines.append(f"[{v.code}] {v.message_vi}")
            lines.append(f"   Huong dan: {v.path_vi[:200]}...")
        lines.append("")

    # MAJOR next
    if by_severity["MAJOR"]:
        lines.append("=== VAN DE LON (MAJOR) ===")
        for v in by_severity["MAJOR"]:
            lines.append(f"[{v.code}] {v.message_vi}")
            lines.append(f"   Huong dan: {v.path_vi[:200]}...")
        lines.append("")

    # WARN last
    if by_severity["WARN"]:
        lines.append("=== CANH BAO (WARN) ===")
        for v in by_severity["WARN"]:
            lines.append(f"[{v.code}] {v.message_vi}")
        lines.append("")

    return "\n".join(lines)


def format_reviewer_response(
    llm_response: str,
    gate_result: GateResult,
    integrity_score: float
) -> dict:
    """
    Format reviewer simulation response.

    Args:
        llm_response: Raw LLM response
        gate_result: Gate result
        integrity_score: Integrity Score

    Returns:
        Formatted response dict
    """
    # Determine recommendation based on gate result
    recommendations = {
        GateResult.PASS: "Submit",
        GateResult.REVISE: "Revise and resubmit",
        GateResult.REJECT: "Major revision required",
    }

    return {
        "feedback": llm_response.strip(),
        "gate_result": gate_result.value,
        "integrity_score": integrity_score,
        "recommendation": recommendations.get(gate_result, "Review"),
    }


def get_quick_feedback(
    violations: list[Violation],
    gate_result: GateResult
) -> str:
    """
    Generate quick feedback without LLM (for when LLM is unavailable).

    Args:
        violations: List of violations
        gate_result: Gate result

    Returns:
        Quick feedback text
    """
    if gate_result == GateResult.PASS:
        return (
            "Abstract dat yeu cau va co the tien hanh cac buoc tiep theo. "
            "Hay xem xet mot so canh bao nho (neu co) de hoan thien hon."
        )

    if gate_result == GateResult.REJECT:
        block_violations = [v for v in violations if v.severity.value == "BLOCK"]
        if block_violations:
            issues = "; ".join(v.message_vi for v in block_violations[:3])
            return (
                f"Abstract co cac van de nghiem trong can giai quyet: {issues}. "
                "Hay sua cac loi nay truoc khi submit lai."
            )

    # REVISE
    major_violations = [v for v in violations if v.severity.value == "MAJOR"]
    if major_violations:
        issues = "; ".join(v.message_vi for v in major_violations[:3])
        return (
            f"Abstract can chinh sua mot so van de: {issues}. "
            "Hay xem chi tiet cac violations va sua theo huong dan."
        )

    return (
        "Abstract can duoc chinh sua. "
        "Hay xem danh sach violations va sua theo huong dan."
    )
