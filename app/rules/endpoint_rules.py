"""Endpoint rules for detecting measurable vs vague endpoints.

This module provides deterministic detection of whether research endpoints
are properly specified and measurable.
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Measurable Endpoint Signals
# ═══════════════════════════════════════════════════════════════════════════════

MEASURABLE_ENDPOINT_SIGNALS: list[str] = [
    # Quantitative measures
    r"\d+\s*(days?|weeks?|months?|years?|ngay|tuan|thang|nam)",
    r"\d+\s*(mg|ml|mm|cm|kg|%|percent|phan tram)",
    r"(score|diem|thang diem)\s*[\w\-]+",

    # Validated scales
    r"vas\b", r"nrs\b", r"sf-?\d+", r"eq-?5d",
    r"apgar", r"glasgow", r"nihss", r"moca", r"mmse",
    r"phq-?\d+", r"gad-?\d+", r"hads", r"bdi",

    # Lab values
    r"(crp|esr|wbc|hb|hba1c|ldl|hdl|triglyceride)",
    r"(creatinine|bilirubin|albumin|protein)",
    r"(glucose|insulin|cortisol)",

    # Imaging measurements
    r"(diameter|kich thuoc|chieu dai|chieu rong)",
    r"(volume|the tich)",
    r"hounsfield", r"signal intensity",

    # Time-to-event
    r"(survival|song con|tu vong)",
    r"(recurrence|tai phat)",
    r"(time to|thoi gian den)",
    r"(event-free|disease-free|progression-free)",

    # Rates
    r"(rate|ty le)\s*(of|cua)?",
    r"(incidence|prevalence|ty le hien mac|ty le moi mac)",
    r"(success rate|ty le thanh cong)",
    r"(complication rate|ty le bien chung)",
    r"(mortality|tu vong)",
    r"(morbidity|benh suat)",

    # Specific metrics
    r"(length of stay|thoi gian nam vien)",
    r"(hospital days|ngay nam vien)",
    r"(operative time|thoi gian phau thuat)",
    r"(blood loss|mat mau)",

    # Statistical terms suggesting measurement
    r"(mean|median|trung binh|trung vi)",
    r"(standard deviation|do lech chuan)",
    r"(confidence interval|khoang tin cay)",
    r"(p[\s-]?value|gia tri p)",
    r"(odds ratio|hazard ratio|risk ratio)",
    r"(sensitivity|specificity|do nhay|do dac hieu)",
    r"(auc|roc)",
]

# ═══════════════════════════════════════════════════════════════════════════════
# Vague Endpoint Patterns
# ═══════════════════════════════════════════════════════════════════════════════

VAGUE_ENDPOINT_PATTERNS: list[str] = [
    # Vague Vietnamese
    r"(ket qua tot|ket qua xau|ket qua kha)",
    r"(hieu qua|hieu qua tot)",
    r"(an toan|do an toan)",
    r"(cai thien|cai thien trieu chung)",
    r"(danh gia|danh gia hieu qua)",
    r"(xem xet|khao sat)",
    r"(tim hieu|nghien cuu)",
    r"(nhan xet|so sanh)",

    # Vague English
    r"\b(good|better|worse|improved|improvement)\b",
    r"\b(effective|effectiveness|efficacy)\b(?!\s*(rate|ratio|score))",
    r"\b(safe|safety)\b(?!\s*(profile|outcome|event))",
    r"\b(outcome|outcomes)\b(?!\s*(measure|score|assessment))",
    r"\b(assess|evaluate|examine|investigate)\b",
    r"\b(determine|compare)\b(?!\s*(the\s+)?(rate|ratio|difference))",

    # Generic terms without specification
    r"^(clinical outcome|ket qua lam sang)$",
    r"^(patient outcome|ket qua benh nhan)$",
    r"^(treatment outcome|ket qua dieu tri)$",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint Detection Functions
# ═══════════════════════════════════════════════════════════════════════════════

def is_endpoint_measurable(endpoint_text: str) -> tuple[bool, list[str], list[str]]:
    """
    Check if an endpoint is measurable using rule-based detection.

    Args:
        endpoint_text: The endpoint description

    Returns:
        Tuple of (is_measurable, measurable_signals_found, vague_patterns_found)
    """
    text_lower = endpoint_text.lower().strip()

    # Find measurable signals
    measurable_found = []
    for pattern in MEASURABLE_ENDPOINT_SIGNALS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            measurable_found.append(pattern)

    # Find vague patterns
    vague_found = []
    for pattern in VAGUE_ENDPOINT_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            vague_found.append(pattern)

    # Decision: measurable if has signals AND few/no vague patterns
    # Or if has many measurable signals
    is_measurable = (
        len(measurable_found) > 0 and len(vague_found) <= 1
    ) or len(measurable_found) >= 3

    return is_measurable, measurable_found, vague_found


def extract_endpoints(text: str) -> dict[str, list[str]]:
    """
    Extract potential endpoints from text.

    Args:
        text: User input or abstract text

    Returns:
        Dictionary with 'primary' and 'secondary' endpoint candidates
    """
    text_lower = text.lower()

    # Patterns for primary endpoint markers
    primary_markers = [
        r"(primary|main|principal|chinh|chu yeu)\s*(endpoint|outcome|ket qua|chi tieu)",
        r"(endpoint|outcome|ket qua|chi tieu)\s*(primary|main|chinh)",
        r"(muc tieu chinh|chi tieu chinh|ket qua chinh)",
    ]

    # Patterns for secondary endpoint markers
    secondary_markers = [
        r"(secondary|additional|phu|bo sung)\s*(endpoint|outcome|ket qua|chi tieu)",
        r"(endpoint|outcome|ket qua|chi tieu)\s*(secondary|phu)",
        r"(muc tieu phu|chi tieu phu|ket qua phu)",
    ]

    endpoints = {
        "primary": [],
        "secondary": []
    }

    # Simple extraction based on context
    sentences = re.split(r'[.;]', text)

    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if not sentence_lower:
            continue

        # Check for primary markers
        is_primary = any(
            re.search(pattern, sentence_lower)
            for pattern in primary_markers
        )

        # Check for secondary markers
        is_secondary = any(
            re.search(pattern, sentence_lower)
            for pattern in secondary_markers
        )

        # Extract the endpoint part
        endpoint_text = sentence.strip()

        if is_primary:
            endpoints["primary"].append(endpoint_text)
        elif is_secondary:
            endpoints["secondary"].append(endpoint_text)

    return endpoints


def validate_endpoint_pair(
    primary: Optional[str],
    secondary: Optional[list[str]]
) -> dict:
    """
    Validate primary and secondary endpoints.

    Args:
        primary: Primary endpoint text
        secondary: List of secondary endpoint texts

    Returns:
        Validation result with issues and suggestions
    """
    result = {
        "valid": True,
        "issues": [],
        "suggestions": []
    }

    # Check primary endpoint
    if not primary or not primary.strip():
        result["valid"] = False
        result["issues"].append("Thieu chi tieu ket qua chinh")
        result["suggestions"].append(
            "Hay xac dinh chi tieu chinh ro rang, co the do luong duoc "
            "(vi du: ty le song sau 30 ngay, thoi gian nam vien, diem VAS)"
        )
    else:
        is_measurable, signals, vague = is_endpoint_measurable(primary)
        if not is_measurable:
            result["valid"] = False
            if vague:
                result["issues"].append(
                    f"Chi tieu chinh mo ho: '{primary}'"
                )
                result["suggestions"].append(
                    "Hay cu the hoa chi tieu voi don vi do luong hoac thang diem "
                    "(vi du: 'cai thien trieu chung' -> 'giam diem VAS >= 2 diem')"
                )

    # Check secondary endpoints (optional but if present, should be measurable)
    if secondary:
        for i, sec in enumerate(secondary):
            is_measurable, signals, vague = is_endpoint_measurable(sec)
            if not is_measurable and vague:
                result["issues"].append(
                    f"Chi tieu phu {i+1} mo ho: '{sec}'"
                )

    return result


def suggest_endpoint_improvement(endpoint_text: str) -> Optional[str]:
    """
    Suggest how to improve a vague endpoint.

    Args:
        endpoint_text: The vague endpoint text

    Returns:
        Improvement suggestion or None if already good
    """
    is_measurable, _, vague = is_endpoint_measurable(endpoint_text)

    if is_measurable:
        return None

    text_lower = endpoint_text.lower()

    # Specific suggestions based on vague patterns
    if re.search(r"(hieu qua|effective)", text_lower):
        return (
            f"'{endpoint_text}' qua mo ho. "
            "Hay xac dinh cu the: Hieu qua duoc do bang chi so nao? "
            "Vi du: ty le dap ung, thoi gian den su kien, diem thang diem..."
        )

    if re.search(r"(an toan|safe)", text_lower):
        return (
            f"'{endpoint_text}' can cu the hoa. "
            "Hay liet ke cac bien co bat loi cu the se theo doi "
            "(vi du: ty le bien chung, ty le tac dung phu cap 3-4)"
        )

    if re.search(r"(cai thien|improv)", text_lower):
        return (
            f"'{endpoint_text}' can dinh luong. "
            "Muc cai thien bao nhieu la co y nghia? "
            "Vi du: giam >= 50% diem dau, tang >= 10 diem chat luong cuoc song"
        )

    if re.search(r"(ket qua|outcome)", text_lower):
        return (
            f"'{endpoint_text}' qua chung chung. "
            "Ket qua cu the la gi? Vi du: tu vong, tai phat, thoi gian nam vien..."
        )

    # Generic suggestion
    return (
        f"'{endpoint_text}' can ro rang hon. "
        "Hay them: (1) don vi do luong, (2) thoi diem danh gia, "
        "(3) nguong xac dinh thanh cong/that bai"
    )
