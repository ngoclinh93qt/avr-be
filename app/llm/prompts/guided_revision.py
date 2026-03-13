"""Guided revision prompts.

This prompt provides detailed guidance for fixing specific violations.
"""

from typing import Optional
from app.models.schemas import Violation


SYSTEM_PROMPT = """Ban la chuyen gia huong dan viet bai bao khoa hoc y khoa.

NHIEM VU:
- Giai thich chi tiet ve mot violation cu the
- Cung cap vi du minh hoa
- Goi y cach viet lai phan bi loi

PHONG CACH:
- Cu the, de hieu
- Cho vi du thuc te
- Than thien, khong phan xet"""


# Pre-defined guidance for common violations
VIOLATION_GUIDANCE = {
    "D-01": {
        "explanation": (
            "Abstract qua ngan khong du de the hien day du noi dung nghien cuu. "
            "Abstract chuan can co 4 phan: Muc tieu, Phuong phap, Ket qua, Ket luan."
        ),
        "example": (
            "Muc tieu: Danh gia hieu qua phau thuat noi soi cat ruot thua o tre em.\n"
            "Phuong phap: Nghien cuu thuan tap hoi cu tren 120 benh nhi (5-15 tuoi) "
            "duoc phau thuat noi soi cat ruot thua tai Benh vien Nhi Dong 1 "
            "tu 01/2020 den 12/2023. Ket qua chinh: ty le bien chung sau mo.\n"
            "Ket qua: [PLACEHOLDER]\n"
            "Ket luan: Phau thuat noi soi du kien an toan va hieu qua..."
        ),
    },
    "S-01": {
        "explanation": (
            "Abstract thieu mot so thanh phan bat buoc cho thiet ke nghien cuu da chon. "
            "Moi thiet ke co nhung yeu cau rieng."
        ),
        "example": None,  # Dynamic based on design
    },
    "S-02": {
        "explanation": (
            "Muc tieu nghien cuu chua ro rang. Muc tieu tot can tra loi duoc: "
            "Nghien cuu gi? Tren ai? De lam gi?"
        ),
        "example": (
            "CHUA TOT: 'Nghien cuu ve viem ruot thua o tre em'\n"
            "TOT HON: 'Danh gia hieu qua phau thuat noi soi so voi mo ho "
            "trong dieu tri viem ruot thua cap o tre 5-15 tuoi'"
        ),
    },
    "A-01": {
        "explanation": (
            "Co su khong nhat quan giua thiet ke nghien cuu da tuyen bo "
            "va phuong phap mo ta. Vi du: tuyen bo RCT nhung khong mo ta randomization."
        ),
        "example": (
            "NEU LA RCT, can them:\n"
            "- 'Benh nhan duoc phan bo ngau nhien (block randomization) "
            "vao nhom can thiep hoac nhom chung'\n"
            "- 'Nghien cuu duoc lam mu don (single-blind) voi nguoi danh gia'"
        ),
    },
    "A-02": {
        "explanation": (
            "Co mau duoc de cap khong nhat quan o cac phan khac nhau, "
            "hoac co nhieu con so khac nhau gay nham lan."
        ),
        "example": (
            "TRANH: 'Thu tuyen 100 benh nhan... 45 benh nhan nhom A... 60 benh nhan nhom B'\n"
            "NEN: 'Thu tuyen 100 benh nhan, phan bo ngau nhien thanh "
            "nhom A (n=50) va nhom B (n=50)'"
        ),
    },
    "Sp-01": {
        "explanation": (
            "Co mau co the khong du de dat power thong ke can thiet. "
            "Can co power analysis de chung minh co mau hop ly."
        ),
        "example": (
            "Them vao phuong phap:\n"
            "'Co mau duoc tinh toan dua tren: alpha=0.05, power=80%, "
            "su khac biet du kien 20% giua hai nhom, cho thay can toi thieu "
            "n=45 moi nhom (tong n=90).'"
        ),
    },
    "St-01": {
        "explanation": (
            "Phuong phap thong ke chua duoc mo ta. Reviewer can biet "
            "ban se dung test gi de phan tich du lieu."
        ),
        "example": (
            "Them vao phuong phap:\n"
            "'So sanh ty le dung chi-square test hoac Fisher exact test. "
            "So sanh gia tri trung binh dung t-test hoac Mann-Whitney U. "
            "Phan tich da bien dung logistic regression. "
            "Gia tri p < 0.05 duoc xem la co y nghia thong ke. "
            "Xu ly du lieu bang SPSS 26.0.'"
        ),
    },
}


def get_guided_revision_prompt(
    violation: Violation,
    section_text: Optional[str] = None
) -> str:
    """
    Generate prompt for guided revision.

    Args:
        violation: The violation to explain
        section_text: Optional relevant section from abstract

    Returns:
        Prompt string for LLM
    """
    # Check for pre-defined guidance
    predefined = VIOLATION_GUIDANCE.get(violation.code)

    prompt = f"""VIOLATION CAN GIAI THICH:
- Code: {violation.code}
- Tier: {violation.tier}
- Severity: {violation.severity.value}
- Message: {violation.message_vi}
- Path: {violation.path_vi}
{f"- Context: {violation.context}" if violation.context else ""}

{f"PHAN VAN BAN LIEN QUAN:{chr(10)}{section_text}" if section_text else ""}

---

NHIEM VU:
Hay giai thich chi tiet ve violation nay va huong dan cach sua:

1. GIAI THICH: Tai sao day la van de? (2-3 cau)

2. VI DU: Cho vi du minh hoa (phan chua tot vs phan da sua)

3. CACH SUA: Huong dan cu the cach viet lai (3-5 buoc)

{f"THAM KHAO:{chr(10)}{predefined['explanation']}" if predefined else ""}

HAY TRA LOI:"""

    return prompt


def get_quick_guidance(violation: Violation) -> dict:
    """
    Get quick guidance without LLM.

    Args:
        violation: The violation

    Returns:
        Guidance dict with explanation, example, suggestion
    """
    predefined = VIOLATION_GUIDANCE.get(violation.code)

    if predefined:
        return {
            "code": violation.code,
            "explanation": predefined["explanation"],
            "example": predefined.get("example"),
            "suggested_rewrite": None,
            "path": violation.path_vi,
        }

    # Generic guidance based on tier
    tier_guidance = {
        0: "Van de ve toan ven du lieu. Kiem tra lai cac thong tin co ban.",
        1: "Thieu thanh phan bat buoc. Hay bo sung theo huong dan.",
        2: "Khong nhat quan. Kiem tra lai va dam bao thong tin dong bo.",
        3: "Van de ve pham vi. Xem xet lai co mau hoac pham vi nghien cuu.",
        4: "Thieu chi tiet thong ke. Bo sung phuong phap phan tich.",
    }

    return {
        "code": violation.code,
        "explanation": tier_guidance.get(violation.tier, violation.message_vi),
        "example": None,
        "suggested_rewrite": None,
        "path": violation.path_vi,
    }


def format_revision_response(
    llm_response: str,
    violation: Violation
) -> dict:
    """
    Format guided revision response.

    Args:
        llm_response: LLM response
        violation: Original violation

    Returns:
        Formatted response dict
    """
    return {
        "code": violation.code,
        "violation": {
            "code": violation.code,
            "tier": violation.tier,
            "severity": violation.severity.value,
            "message": violation.message_vi,
            "path": violation.path_vi,
        },
        "explanation": llm_response.strip(),
        "example": None,  # Could be parsed from response
        "suggested_rewrite": None,  # Could be parsed from response
    }
