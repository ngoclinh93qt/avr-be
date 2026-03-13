"""Tier 2 Constraints: Attribute Consistency.

These check for internal consistency of research attributes
and detect logical conflicts.

Codes: A-01 to A-04
"""

import re
from typing import Optional
from app.models.schemas import Violation, ResearchBlueprint, ExtractedAttributes
from app.models.enums import ViolationSeverity, DesignType


def check_tier2_violations(
    abstract: str,
    blueprint: Optional[ResearchBlueprint] = None,
    attributes: Optional[ExtractedAttributes] = None
) -> list[Violation]:
    """
    Check Tier 2 (Attribute Consistency) violations.

    Args:
        abstract: The submitted abstract text
        blueprint: Optional ResearchBlueprint object
        attributes: Optional ExtractedAttributes object

    Returns:
        List of Violation objects
    """
    violations = []

    # Convert to dicts for easier access
    bp_dict = blueprint.model_dump() if blueprint else {}
    attr_dict = attributes.model_dump() if attributes else {}

    # A-01: Design type conflicts with stated elements
    violations.extend(_check_design_consistency(abstract, bp_dict, attr_dict))

    # A-02: Sample size consistency
    violations.extend(_check_sample_consistency(abstract, bp_dict, attr_dict))

    # A-03: Endpoint consistency
    violations.extend(_check_endpoint_consistency(abstract, bp_dict, attr_dict))

    # A-04: Time/duration consistency
    violations.extend(_check_time_consistency(abstract, bp_dict, attr_dict))

    return violations


def _check_design_consistency(
    abstract: str,
    blueprint: dict,
    attributes: dict
) -> list[Violation]:
    """Check design type is consistent with methodology described."""
    violations = []
    abstract_lower = abstract.lower()

    design_type = attributes.get("design_type") or blueprint.get("design_type")

    if design_type == DesignType.RCT:
        # RCT should mention randomization
        if not re.search(r"(random|ngau nhien)", abstract_lower):
            violations.append(Violation(
                code="A-01",
                tier=2,
                severity=ViolationSeverity.MAJOR,
                message_vi="RCT nhung khong mo ta randomization",
                path_vi=(
                    "Abstract chi ra RCT nhung khong de cap den phuong phap ngau nhien hoa. "
                    "Hay them mo ta:\n"
                    "- Phuong phap ngau nhien hoa (simple, block, stratified)\n"
                    "- Phuong phap che giau phan bo (allocation concealment)"
                ),
                context={"design_type": "RCT"}
            ))

        # RCT should have at least 2 groups
        group_patterns = [
            r"(nhom|group|arm)\s*(1|2|a|b|can thiep|doi chung|control|intervention)",
            r"(chia|divided|allocated)\s*(thanh|into)\s*\d+\s*(nhom|group|arm)",
        ]
        has_groups = any(re.search(p, abstract_lower) for p in group_patterns)

        if not has_groups and not re.search(r"(vs\.?|versus|so voi|compared)", abstract_lower):
            violations.append(Violation(
                code="A-01",
                tier=2,
                severity=ViolationSeverity.WARN,
                message_vi="RCT nhung khong ro cac nhom",
                path_vi=(
                    "RCT can mo ta ro cac nhom:\n"
                    "- Nhom can thiep va nhom doi chung\n"
                    "- So luong benh nhan moi nhom"
                ),
                context={"design_type": "RCT"}
            ))

    if design_type == DesignType.CASE_CONTROL:
        # Case-control should mention cases and controls
        if not re.search(r"(case|ca benh|nhom benh)", abstract_lower):
            violations.append(Violation(
                code="A-01",
                tier=2,
                severity=ViolationSeverity.MAJOR,
                message_vi="Nghien cuu benh-chung nhung khong dinh nghia ca benh",
                path_vi=(
                    "Nghien cuu case-control can dinh nghia ro:\n"
                    "- The nao la ca benh (case)?\n"
                    "- The nao la nhom chung (control)?\n"
                    "- Tieu chi ghep cap (neu co)"
                ),
                context={"design_type": "case_control"}
            ))

    if design_type in [DesignType.COHORT_PROSPECTIVE, DesignType.COHORT_RETROSPECTIVE]:
        # Cohort should mention exposure
        if not re.search(r"(exposure|phoi nhiem|yeu to|factor|risk)", abstract_lower):
            violations.append(Violation(
                code="A-01",
                tier=2,
                severity=ViolationSeverity.WARN,
                message_vi="Nghien cuu cohort nhung khong ro yeu to phoi nhiem",
                path_vi=(
                    "Nghien cuu cohort can xac dinh:\n"
                    "- Yeu to phoi nhiem/nguy co la gi?\n"
                    "- Cach phan nhom theo phoi nhiem"
                ),
                context={"design_type": str(design_type)}
            ))

    return violations


def _check_sample_consistency(
    abstract: str,
    blueprint: dict,
    attributes: dict
) -> list[Violation]:
    """Check sample size is consistent across mentions."""
    violations = []

    # Extract all numbers that look like sample sizes
    sample_patterns = [
        r"n\s*=\s*(\d+)",
        r"(\d+)\s*(benh nhan|patient|ca|case|doi tuong|subject|participant)",
        r"(recruited|thu tuyen|tuyen)\s*(\d+)",
        r"(total of|tong cong)\s*(\d+)",
    ]

    abstract_lower = abstract.lower()
    found_sizes = []

    for pattern in sample_patterns:
        matches = re.findall(pattern, abstract_lower)
        for match in matches:
            # Extract the number from match
            if isinstance(match, tuple):
                for m in match:
                    if m.isdigit():
                        found_sizes.append(int(m))
            elif match.isdigit():
                found_sizes.append(int(match))

    # Check for blueprint sample size
    bp_sample = blueprint.get("sample_size")
    attr_sample = attributes.get("sample_size")

    if bp_sample and attr_sample and bp_sample != attr_sample:
        violations.append(Violation(
            code="A-02",
            tier=2,
            severity=ViolationSeverity.WARN,
            message_vi="Co mau khong nhat quan giua blueprint va abstract",
            path_vi=(
                f"Blueprint ghi n={bp_sample} nhung abstract de cap n={attr_sample}. "
                "Hay thong nhat co mau."
            ),
            context={"blueprint_n": bp_sample, "abstract_n": attr_sample}
        ))

    # Check if multiple different sample sizes mentioned (not including subgroups)
    if len(set(found_sizes)) > 3:
        violations.append(Violation(
            code="A-02",
            tier=2,
            severity=ViolationSeverity.WARN,
            message_vi="Nhieu con so co mau khac nhau",
            path_vi=(
                f"Phat hien {len(set(found_sizes))} con so co mau khac nhau trong abstract. "
                "Hay dam bao:\n"
                "- Tong so benh nhan ro rang\n"
                "- So luong moi nhom (neu co) cong lai bang tong"
            ),
            context={"sizes_found": list(set(found_sizes))}
        ))

    return violations


def _check_endpoint_consistency(
    abstract: str,
    blueprint: dict,
    attributes: dict
) -> list[Violation]:
    """Check endpoint consistency."""
    violations = []

    primary_outcome = blueprint.get("primary_outcome")
    abstract_lower = abstract.lower()

    # If blueprint has primary outcome, check if it's mentioned in abstract
    if primary_outcome:
        primary_lower = primary_outcome.lower()
        # Simple keyword check
        key_terms = primary_lower.split()
        key_terms = [t for t in key_terms if len(t) > 3]

        if key_terms:
            found = any(term in abstract_lower for term in key_terms)
            if not found:
                violations.append(Violation(
                    code="A-03",
                    tier=2,
                    severity=ViolationSeverity.WARN,
                    message_vi="Ket qua chinh trong blueprint khong thay trong abstract",
                    path_vi=(
                        f"Blueprint ghi ket qua chinh la: '{primary_outcome}' "
                        "nhung khong tim thay trong abstract. "
                        "Hay dam bao abstract de cap ro ket qua chinh."
                    ),
                    context={"primary_outcome": primary_outcome}
                ))

    # Check for conflicting endpoints
    endpoint_conflicts = [
        (r"primary outcome", r"secondary outcome"),
        (r"ket qua chinh", r"ket qua phu"),
    ]

    for primary_pattern, secondary_pattern in endpoint_conflicts:
        # Look for same term used as both primary and secondary
        primary_matches = re.findall(f"{primary_pattern}[^.]*", abstract_lower)
        secondary_matches = re.findall(f"{secondary_pattern}[^.]*", abstract_lower)

        if primary_matches and secondary_matches:
            # Check if same endpoint mentioned in both
            for pm in primary_matches:
                for sm in secondary_matches:
                    # Extract the actual endpoint
                    pm_endpoint = pm.replace(primary_pattern, "").strip()
                    sm_endpoint = sm.replace(secondary_pattern, "").strip()

                    if pm_endpoint and sm_endpoint and pm_endpoint == sm_endpoint:
                        violations.append(Violation(
                            code="A-03",
                            tier=2,
                            severity=ViolationSeverity.MAJOR,
                            message_vi="Cung mot ket qua duoc ghi la ca chinh va phu",
                            path_vi=(
                                f"'{pm_endpoint}' duoc de cap la ca primary va secondary. "
                                "Moi ket qua chi co the la chinh HOAC phu, khong phai ca hai."
                            ),
                            context={"conflicting_endpoint": pm_endpoint}
                        ))

    return violations


def _check_time_consistency(
    abstract: str,
    blueprint: dict,
    attributes: dict
) -> list[Violation]:
    """Check time/duration consistency."""
    violations = []
    abstract_lower = abstract.lower()

    # Extract time mentions
    time_patterns = [
        r"(\d+)\s*(ngay|day)",
        r"(\d+)\s*(tuan|week)",
        r"(\d+)\s*(thang|month)",
        r"(\d+)\s*(nam|year)",
    ]

    time_mentions = []
    for pattern in time_patterns:
        matches = re.findall(pattern, abstract_lower)
        for match in matches:
            time_mentions.append(f"{match[0]} {match[1]}")

    # Check for follow-up consistency with design
    design_type = attributes.get("design_type") or blueprint.get("design_type")

    if design_type == DesignType.COHORT_PROSPECTIVE:
        # Prospective cohort should have follow-up
        follow_up_patterns = [
            r"(theo doi|follow-?up|followed)",
            r"(trong|over|during)\s*\d+\s*(thang|month|nam|year)",
        ]
        has_followup = any(re.search(p, abstract_lower) for p in follow_up_patterns)

        if not has_followup:
            violations.append(Violation(
                code="A-04",
                tier=2,
                severity=ViolationSeverity.WARN,
                message_vi="Nghien cuu cohort tien cu nhung khong ro thoi gian theo doi",
                path_vi=(
                    "Nghien cuu cohort prospective can neu ro:\n"
                    "- Thoi gian theo doi bao lau?\n"
                    "- Cac moc thoi diem danh gia"
                ),
                context={"design_type": "cohort_prospective"}
            ))

    # Check for unrealistic timeframes
    for mention in time_mentions:
        parts = mention.split()
        if len(parts) == 2:
            try:
                value = int(parts[0])
                unit = parts[1]

                # Flag suspiciously short RCT
                if design_type == DesignType.RCT:
                    if "day" in unit or "ngay" in unit:
                        if value < 7:
                            violations.append(Violation(
                                code="A-04",
                                tier=2,
                                severity=ViolationSeverity.WARN,
                                message_vi=f"RCT voi thoi gian qua ngan ({value} ngay)",
                                path_vi=(
                                    "RCT voi thoi gian < 7 ngay thuong khong du "
                                    "de danh gia hieu qua. Hay xem xet:\n"
                                    "- Co ket qua ngan han phu hop?\n"
                                    "- Can theo doi dai hon?"
                                ),
                                context={"duration": mention}
                            ))
            except ValueError:
                pass

    return violations
