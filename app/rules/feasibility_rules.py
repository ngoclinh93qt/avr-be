"""Feasibility rules for checking research viability.

This module implements BLOCK and WARN rules that detect
fundamental feasibility issues before further processing.
"""

import re
from typing import Optional
from dataclasses import dataclass

from app.models.enums import DesignType, ViolationSeverity


@dataclass
class FeasibilityIssue:
    """A feasibility issue detected by rules."""
    code: str
    severity: ViolationSeverity
    message_vi: str
    path_vi: str
    context: dict = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCK Rules - Fatal issues that prevent proceeding
# ═══════════════════════════════════════════════════════════════════════════════

BLOCK_RULES = {
    "F-B01": {
        "name": "sample_too_small_rct",
        "description": "RCT with n < 20 total",
        "check": lambda attrs: (
            attrs.get("design_type") == DesignType.RCT and
            attrs.get("sample_size") is not None and
            attrs.get("sample_size") < 20
        ),
        "message_vi": "Co mau qua nho cho RCT (n < 20)",
        "path_vi": (
            "Thu nghiem lam sang ngau nhien can toi thieu 20 benh nhan "
            "(thuc te thuong can 50-100+). Hay xem xet:\n"
            "- Tang co mau\n"
            "- Chuyen sang thiet ke pilot study\n"
            "- Chon thiet ke khac (case series, cohort)"
        )
    },
    "F-B02": {
        "name": "no_comparator_rct",
        "description": "RCT without comparator group",
        "check": lambda attrs: (
            attrs.get("design_type") == DesignType.RCT and
            not attrs.get("comparator")
        ),
        "message_vi": "RCT thieu nhom chung/doi chung",
        "path_vi": (
            "Thu nghiem lam sang ngau nhien bat buoc phai co nhom doi chung. "
            "Hay xac dinh:\n"
            "- Nhom chung la gi? (placebo, dieu tri chuan, khong dieu tri)\n"
            "- Neu khong co nhom chung, hay doi sang thiet ke before-after"
        )
    },
    "F-B03": {
        "name": "diagnostic_no_reference",
        "description": "Diagnostic study without reference standard",
        "check": lambda attrs: (
            attrs.get("design_type") == DesignType.DIAGNOSTIC_ACCURACY and
            not attrs.get("reference_standard")
        ),
        "message_vi": "Nghien cuu chan doan thieu tieu chuan vang",
        "path_vi": (
            "Nghien cuu do chinh xac chan doan bat buoc phai co tieu chuan vang "
            "(reference standard). Hay xac dinh:\n"
            "- Test tham chieu la gi? (sinh thiet, follow-up, panel chuyen gia)\n"
            "- Moi benh nhan co duoc lam test tham chieu khong?"
        )
    },
    "F-B04": {
        "name": "meta_no_search_strategy",
        "description": "Meta-analysis/SR without search strategy",
        "check": lambda attrs: (
            attrs.get("design_type") in [
                DesignType.SYSTEMATIC_REVIEW,
                DesignType.META_ANALYSIS
            ] and
            not attrs.get("search_strategy") and
            not attrs.get("databases")
        ),
        "message_vi": "Tong quan he thong thieu chien luoc tim kiem",
        "path_vi": (
            "Tong quan he thong/phan tich gop bat buoc phai co:\n"
            "- Cac co so du lieu se tim (PubMed, Embase, Cochrane...)\n"
            "- Tu khoa tim kiem\n"
            "- Tieu chi lua chon va loai tru"
        )
    },
    "F-B05": {
        "name": "zero_sample",
        "description": "Sample size is zero or not specified for quantitative study",
        "check": lambda attrs: (
            attrs.get("design_type") not in [
                DesignType.QUALITATIVE,
                DesignType.SYSTEMATIC_REVIEW,
                DesignType.META_ANALYSIS,
                DesignType.SCOPING_REVIEW,
                DesignType.CASE_REPORT
            ] and
            attrs.get("sample_size") is not None and
            attrs.get("sample_size") == 0
        ),
        "message_vi": "Co mau bang 0",
        "path_vi": "Co mau khong the bang 0. Hay xac dinh so luong benh nhan du kien."
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# WARN Rules - Issues that need attention but don't block
# ═══════════════════════════════════════════════════════════════════════════════

WARN_RULES = {
    "F-W01": {
        "name": "small_sample_warning",
        "description": "Sample size may be underpowered",
        "check": lambda attrs: (
            attrs.get("sample_size") is not None and
            attrs.get("sample_size") < 30 and
            attrs.get("design_type") not in [
                DesignType.CASE_REPORT,
                DesignType.CASE_SERIES,
                DesignType.QUALITATIVE
            ]
        ),
        "message_vi": "Co mau co the qua nho (n < 30)",
        "path_vi": (
            "Voi n < 30, nghien cuu co the thieu power thong ke. Hay xem xet:\n"
            "- Tinh toan co mau dua tren power analysis\n"
            "- Giai thich ly do chon co mau nay (rare disease, pilot)"
        )
    },
    "F-W02": {
        "name": "rare_disease_flag",
        "description": "Rare disease mentioned, may need confirmation",
        "check": lambda attrs: attrs.get("rare_disease_flag") is True,
        "message_vi": "Phat hien benh hiem (co mau nho co the chap nhan)",
        "path_vi": (
            "Neu day la benh hiem (rare disease), co mau nho co the duoc chap nhan. "
            "Hay xac nhan day la benh hiem de dieu chinh danh gia."
        )
    },
    "F-W03": {
        "name": "retrospective_bias_warning",
        "description": "Retrospective design has inherent biases",
        "check": lambda attrs: attrs.get("design_type") == DesignType.COHORT_RETROSPECTIVE,
        "message_vi": "Thiet ke hoi cu co sai lech co huu",
        "path_vi": (
            "Nghien cuu hoi cu co cac han che can luu y:\n"
            "- Selection bias\n"
            "- Information bias\n"
            "- Missing data\n"
            "Hay neu ro cach kiem soat cac sai lech nay trong phuong phap."
        )
    },
    "F-W04": {
        "name": "single_center_generalizability",
        "description": "Single-center study may have limited generalizability",
        "check": lambda attrs: (
            attrs.get("multi_center") is False and
            attrs.get("sample_size") is not None and
            attrs.get("sample_size") >= 100
        ),
        "message_vi": "Nghien cuu don trung tam voi co mau lon",
        "path_vi": (
            "Nghien cuu don trung tam voi n >= 100 co the han che tinh khai quat hoa. "
            "Hay xem xet:\n"
            "- Neu ro dac diem dan so tai trung tam\n"
            "- Thao luan ve external validity"
        )
    },
    "F-W05": {
        "name": "missing_blinding_rct",
        "description": "RCT without specified blinding",
        "check": lambda attrs: (
            attrs.get("design_type") == DesignType.RCT and
            not attrs.get("blinding")
        ),
        "message_vi": "RCT chua xac dinh phuong phap lam mu",
        "path_vi": (
            "RCT can neu ro:\n"
            "- Co lam mu khong? (open-label, single-blind, double-blind)\n"
            "- Ai bi lam mu? (benh nhan, bac si, nguoi danh gia)"
        )
    },
    "F-W06": {
        "name": "no_followup_cohort",
        "description": "Cohort study without follow-up duration",
        "check": lambda attrs: (
            attrs.get("design_type") in [
                DesignType.COHORT_PROSPECTIVE,
                DesignType.COHORT_RETROSPECTIVE
            ] and
            not attrs.get("follow_up_duration") and
            not attrs.get("duration")
        ),
        "message_vi": "Nghien cuu cohort thieu thoi gian theo doi",
        "path_vi": (
            "Nghien cuu thuan tap can xac dinh:\n"
            "- Thoi gian theo doi la bao lau?\n"
            "- Cac moc thoi gian danh gia"
        )
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# Rare Disease Detection
# ═══════════════════════════════════════════════════════════════════════════════

RARE_DISEASE_KEYWORDS = [
    # Vietnamese
    r"benh hiem", r"hiem gap", r"it gap", r"hoi chung hiem",
    r"benh mo coi", r"orphan",
    # English
    r"rare disease", r"rare condition", r"orphan disease",
    r"ultra-?rare", r"extremely rare",
    # Specific examples often considered rare
    r"wilson", r"fabry", r"gaucher", r"pompe",
    r"huntington", r"cystic fibrosis",
    r"muscular dystrophy", r"loai duc co",
]


def detect_rare_disease(text: str) -> bool:
    """Detect if text mentions rare disease."""
    text_lower = text.lower()
    for pattern in RARE_DISEASE_KEYWORDS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Feasibility Check Function
# ═══════════════════════════════════════════════════════════════════════════════

def check_feasibility(attributes: dict) -> list[FeasibilityIssue]:
    """
    Check all feasibility rules against extracted attributes.

    Args:
        attributes: Extracted attributes dictionary

    Returns:
        List of FeasibilityIssue objects
    """
    issues = []

    # Check BLOCK rules first
    for code, rule in BLOCK_RULES.items():
        try:
            if rule["check"](attributes):
                issues.append(FeasibilityIssue(
                    code=code,
                    severity=ViolationSeverity.BLOCK,
                    message_vi=rule["message_vi"],
                    path_vi=rule["path_vi"],
                    context={"rule_name": rule["name"]}
                ))
        except Exception:
            # Rule check failed, skip
            pass

    # Check WARN rules
    for code, rule in WARN_RULES.items():
        try:
            if rule["check"](attributes):
                issues.append(FeasibilityIssue(
                    code=code,
                    severity=ViolationSeverity.WARN,
                    message_vi=rule["message_vi"],
                    path_vi=rule["path_vi"],
                    context={"rule_name": rule["name"]}
                ))
        except Exception:
            # Rule check failed, skip
            pass

    return issues


def has_blocking_issues(issues: list[FeasibilityIssue]) -> bool:
    """Check if any issues are blocking."""
    return any(issue.severity == ViolationSeverity.BLOCK for issue in issues)
