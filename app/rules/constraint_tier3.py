"""Tier 3 Constraints: Scope Validity.

These check for methodological scope issues like
sample size justification, study scope, and feasibility.

Codes: Sp-01 to Sp-03
"""

import re
from typing import Optional
from app.models.schemas import Violation, ResearchBlueprint, ExtractedAttributes
from app.models.enums import ViolationSeverity, DesignType


# Minimum sample sizes by design type (conservative estimates)
MIN_SAMPLE_SIZES = {
    DesignType.RCT: 20,  # Per arm, so 40 total minimum
    DesignType.QUASI_EXPERIMENTAL: 15,
    DesignType.BEFORE_AFTER: 20,
    DesignType.COHORT_PROSPECTIVE: 30,
    DesignType.COHORT_RETROSPECTIVE: 50,
    DesignType.CASE_CONTROL: 30,  # Cases + controls
    DesignType.CROSS_SECTIONAL: 50,
    DesignType.DIAGNOSTIC_ACCURACY: 50,
    DesignType.PROGNOSTIC: 100,  # Need sufficient events
    DesignType.CASE_SERIES: 3,
    DesignType.CASE_REPORT: 1,
}


def check_tier3_violations(
    abstract: str,
    blueprint: Optional[ResearchBlueprint] = None,
    attributes: Optional[ExtractedAttributes] = None,
    rare_disease_confirmed: bool = False
) -> list[Violation]:
    """
    Check Tier 3 (Scope Validity) violations.

    Args:
        abstract: The submitted abstract text
        blueprint: Optional ResearchBlueprint object
        attributes: Optional ExtractedAttributes object
        rare_disease_confirmed: Whether user confirmed rare disease

    Returns:
        List of Violation objects
    """
    violations = []

    # Convert to dicts for easier access
    bp_dict = blueprint.model_dump() if blueprint else {}
    attr_dict = attributes.model_dump() if attributes else {}

    design_type = attr_dict.get("design_type") or bp_dict.get("design_type")
    sample_size = attr_dict.get("sample_size") or bp_dict.get("sample_size")

    # Sp-01: Sample size justification
    violations.extend(_check_sample_justification(
        abstract, design_type, sample_size, rare_disease_confirmed
    ))

    # Sp-02: Study scope appropriateness
    violations.extend(_check_scope_appropriateness(
        abstract, bp_dict, attr_dict, design_type
    ))

    # Sp-03: Generalizability concerns
    violations.extend(_check_generalizability(
        abstract, bp_dict, attr_dict, design_type, sample_size
    ))

    return violations


def _check_sample_justification(
    abstract: str,
    design_type: Optional[DesignType],
    sample_size: Optional[int],
    rare_disease_confirmed: bool
) -> list[Violation]:
    """Check if sample size is justified for the design."""
    violations = []
    abstract_lower = abstract.lower()

    if not sample_size or not design_type:
        return violations

    # Get minimum for this design
    min_size = MIN_SAMPLE_SIZES.get(design_type, 30)

    # Rare disease exception (R-10)
    if rare_disease_confirmed:
        # Lower threshold for rare diseases
        min_size = max(5, min_size // 5)

    if sample_size < min_size:
        # Check if sample size calculation is mentioned
        has_power_calc = re.search(
            r"(power|power analysis|sample size calculation|tinh co mau|power >=?\s*0\.\d)",
            abstract_lower
        )

        if has_power_calc:
            # Has justification, just warn
            violations.append(Violation(
                code="Sp-01",
                tier=3,
                severity=ViolationSeverity.WARN,
                message_vi=f"Co mau (n={sample_size}) nho hon khuyen nghi cho {design_type.value}",
                path_vi=(
                    f"Co mau n={sample_size} nho hon nguong toi thieu (n={min_size}). "
                    "Tuy nhien, co de cap den tinh toan co mau. "
                    "Hay dam bao ket qua power analysis duoc mo ta ro."
                ),
                context={
                    "sample_size": sample_size,
                    "minimum": min_size,
                    "design_type": design_type.value
                }
            ))
        else:
            # No justification
            severity = ViolationSeverity.WARN if sample_size >= min_size * 0.5 else ViolationSeverity.MAJOR

            violations.append(Violation(
                code="Sp-01",
                tier=3,
                severity=severity,
                message_vi=f"Co mau (n={sample_size}) co the khong du cho {design_type.value}",
                path_vi=(
                    f"Co mau n={sample_size} nho hon nguong khuyen nghi (n={min_size}). "
                    "Hay:\n"
                    "1. Thuc hien power analysis de xac dinh co mau can thiet\n"
                    "2. Neu day la benh hiem, hay xac nhan de duoc dieu chinh\n"
                    "3. Xem xet chuyen sang pilot study neu co mau han che"
                ),
                context={
                    "sample_size": sample_size,
                    "minimum": min_size,
                    "design_type": design_type.value
                }
            ))

    return violations


def _check_scope_appropriateness(
    abstract: str,
    blueprint: dict,
    attributes: dict,
    design_type: Optional[DesignType]
) -> list[Violation]:
    """Check if study scope is appropriate."""
    violations = []
    abstract_lower = abstract.lower()

    # Check for overly broad scope
    broad_scope_patterns = [
        r"(all patients|tat ca benh nhan)",
        r"(every|moi|toan bo)",
        r"(comprehensive|toan dien)",
        r"(all aspects|moi khia canh)",
    ]

    has_broad_scope = any(re.search(p, abstract_lower) for p in broad_scope_patterns)

    # Check for too many endpoints
    endpoint_count = 0
    endpoint_patterns = [
        r"(primary|chinh)",
        r"(secondary|phu)",
        r"(tertiary|ba)",
        r"(endpoint|outcome|ket qua)",
    ]

    for pattern in endpoint_patterns:
        endpoint_count += len(re.findall(pattern, abstract_lower))

    if endpoint_count > 10:
        violations.append(Violation(
            code="Sp-02",
            tier=3,
            severity=ViolationSeverity.WARN,
            message_vi="Qua nhieu endpoints/outcomes",
            path_vi=(
                f"Phat hien {endpoint_count}+ endpoints/outcomes. "
                "Nghien cuu tap trung thuong chi co:\n"
                "- 1 primary endpoint\n"
                "- 2-3 secondary endpoints\n"
                "Qua nhieu endpoints gay van de multiple comparison va lam loang ket qua."
            ),
            context={"endpoint_mentions": endpoint_count}
        ))

    if has_broad_scope and design_type not in [
        DesignType.SYSTEMATIC_REVIEW,
        DesignType.META_ANALYSIS,
        DesignType.SCOPING_REVIEW
    ]:
        violations.append(Violation(
            code="Sp-02",
            tier=3,
            severity=ViolationSeverity.WARN,
            message_vi="Pham vi nghien cuu co the qua rong",
            path_vi=(
                "Abstract de cap den pham vi rong (tat ca, moi, toan bo...). "
                "Hay xem xet:\n"
                "- Thu hep tieu chi lua chon\n"
                "- Tap trung vao nhom dan so cu the hon\n"
                "- Gioi han o ket qua chinh"
            ),
            context={}
        ))

    return violations


def _check_generalizability(
    abstract: str,
    blueprint: dict,
    attributes: dict,
    design_type: Optional[DesignType],
    sample_size: Optional[int]
) -> list[Violation]:
    """Check for generalizability concerns."""
    violations = []
    abstract_lower = abstract.lower()

    # Check for single-center with large claims
    is_single_center = not re.search(
        r"(multi-?center|da trung tam|nhieu trung tam|multiple site)",
        abstract_lower
    )

    has_large_claims = re.search(
        r"(generaliz|khai quat|population-wide|all patients should|moi benh nhan nen)",
        abstract_lower
    )

    if is_single_center and has_large_claims:
        violations.append(Violation(
            code="Sp-03",
            tier=3,
            severity=ViolationSeverity.WARN,
            message_vi="Nghien cuu don trung tam voi ket luan khai quat rong",
            path_vi=(
                "Nghien cuu don trung tam co han che ve tinh khai quat hoa. "
                "Hay:\n"
                "- Tranh dua ra ket luan ap dung cho toan bo dan so\n"
                "- Neu ro day la ket qua tu 1 trung tam\n"
                "- Thao luan ve external validity trong Limitations"
            ),
            context={}
        ))

    # Check for very specific population with broad conclusions
    specific_population_patterns = [
        r"(chi|only|exclusively)\s*(benh nhan|patient|doi tuong)",
        r"(tu|from)\s*\d{4}\s*(den|to)\s*\d{4}",  # Time-limited
        r"(tai|at)\s*(benh vien|hospital|trung tam)",  # Single institution
    ]

    is_specific = any(re.search(p, abstract_lower) for p in specific_population_patterns)

    if is_specific and has_large_claims and sample_size and sample_size < 500:
        violations.append(Violation(
            code="Sp-03",
            tier=3,
            severity=ViolationSeverity.WARN,
            message_vi="Dan so dac thu voi ket luan khai quat",
            path_vi=(
                "Nghien cuu tren dan so dac thu (gioi han thoi gian, don co so, tieu chi hep) "
                f"voi co mau n={sample_size}. Hay can trong voi cac ket luan khai quat. "
                "Thay vi 'tat ca benh nhan nen...', hay ghi 'trong dan so nghien cuu nay...'."
            ),
            context={"sample_size": sample_size}
        ))

    # Check for selection bias risks
    if design_type == DesignType.COHORT_RETROSPECTIVE:
        selection_bias_patterns = [
            r"(consecutive|lien tiep)",
            r"(random sample|mau ngau nhien)",
            r"(all eligible|tat ca du tieu chuan)",
        ]

        has_selection_control = any(
            re.search(p, abstract_lower) for p in selection_bias_patterns
        )

        if not has_selection_control:
            violations.append(Violation(
                code="Sp-03",
                tier=3,
                severity=ViolationSeverity.WARN,
                message_vi="Nghien cuu hoi cu khong ro cach chon mau",
                path_vi=(
                    "Nghien cuu hoi cu can mo ta cach chon mau de tranh selection bias:\n"
                    "- Lay consecutive cases?\n"
                    "- Random sampling?\n"
                    "- All eligible patients?"
                ),
                context={"design_type": "cohort_retrospective"}
            ))

    return violations
