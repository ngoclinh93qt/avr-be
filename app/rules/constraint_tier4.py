"""Tier 4 Constraints: Statistical Completeness.

These check for statistical and analytical completeness,
including methods, power, and analysis plan.

Codes: St-01 to St-04
"""

import re
from typing import Optional
from app.models.schemas import Violation, ResearchBlueprint, ExtractedAttributes
from app.models.enums import ViolationSeverity, DesignType


# Statistical methods expected by design type
EXPECTED_METHODS = {
    DesignType.RCT: [
        "intention-to-treat",
        "per-protocol",
        "chi-square",
        "t-test",
        "anova",
        "mann-whitney",
        "wilcoxon",
        "fisher",
        "regression",
    ],
    DesignType.COHORT_PROSPECTIVE: [
        "cox",
        "kaplan-meier",
        "hazard ratio",
        "survival",
        "regression",
        "incidence",
    ],
    DesignType.COHORT_RETROSPECTIVE: [
        "odds ratio",
        "regression",
        "chi-square",
        "t-test",
        "multivariate",
    ],
    DesignType.CASE_CONTROL: [
        "odds ratio",
        "logistic regression",
        "conditional logistic",
        "matching",
        "chi-square",
    ],
    DesignType.CROSS_SECTIONAL: [
        "prevalence",
        "chi-square",
        "correlation",
        "regression",
    ],
    DesignType.DIAGNOSTIC_ACCURACY: [
        "sensitivity",
        "specificity",
        "ppv",
        "npv",
        "roc",
        "auc",
        "likelihood ratio",
    ],
    DesignType.META_ANALYSIS: [
        "heterogeneity",
        "i-squared",
        "i2",
        "random effects",
        "fixed effects",
        "forest plot",
        "funnel plot",
        "publication bias",
    ],
}


def check_tier4_violations(
    abstract: str,
    blueprint: Optional[ResearchBlueprint] = None,
    attributes: Optional[ExtractedAttributes] = None
) -> list[Violation]:
    """
    Check Tier 4 (Statistical Completeness) violations.

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

    design_type = attr_dict.get("design_type") or bp_dict.get("design_type")

    # St-01: Statistical methods mentioned
    violations.extend(_check_statistical_methods(abstract, design_type))

    # St-02: Power/sample size calculation
    violations.extend(_check_power_calculation(abstract, design_type))

    # St-03: Analysis plan clarity
    violations.extend(_check_analysis_plan(abstract, design_type, bp_dict))

    # St-04: Missing important statistical details
    violations.extend(_check_statistical_details(abstract, design_type))

    return violations


def _check_statistical_methods(
    abstract: str,
    design_type: Optional[DesignType]
) -> list[Violation]:
    """Check if appropriate statistical methods are mentioned."""
    violations = []
    abstract_lower = abstract.lower()

    # Designs that don't need statistical methods
    exempt_designs = [
        DesignType.CASE_REPORT,
        DesignType.CASE_SERIES,
        DesignType.QUALITATIVE,
        DesignType.SCOPING_REVIEW,
    ]

    if design_type in exempt_designs:
        return violations

    # General statistical patterns
    stat_patterns = [
        r"(chi-?square|ki binh phuong)",
        r"(t-?test|student)",
        r"(anova|phan tich phuong sai)",
        r"(regression|hoi quy)",
        r"(correlation|tuong quan)",
        r"(mann-?whitney|wilcoxon)",
        r"(fisher)",
        r"(odds ratio|or\s*=)",
        r"(hazard ratio|hr\s*=)",
        r"(risk ratio|rr\s*=)",
        r"(kaplan-?meier|km)",
        r"(cox|proportional hazard)",
        r"(logistic)",
        r"(linear)",
        r"(multivariate|da bien)",
        r"(univariate|don bien)",
        r"(spss|stata|r\s+software|sas)",
        r"(p\s*[<>=]\s*0\.\d+)",
        r"(95%?\s*ci|confidence interval|khoang tin cay)",
    ]

    has_stats = any(re.search(p, abstract_lower) for p in stat_patterns)

    if not has_stats:
        violations.append(Violation(
            code="St-01",
            tier=4,
            severity=ViolationSeverity.WARN,
            message_vi="Khong de cap phuong phap thong ke",
            path_vi=(
                "Abstract can mo ta phuong phap thong ke se su dung:\n"
                "- Loai test thong ke (t-test, chi-square, regression...)\n"
                "- Phan mem thong ke\n"
                "- Muc y nghia (alpha = 0.05)"
            ),
            context={}
        ))

    # Check for design-specific methods
    if design_type and design_type in EXPECTED_METHODS:
        expected = EXPECTED_METHODS[design_type]
        found = [m for m in expected if re.search(m, abstract_lower, re.IGNORECASE)]

        if not found and design_type not in exempt_designs:
            violations.append(Violation(
                code="St-01",
                tier=4,
                severity=ViolationSeverity.WARN,
                message_vi=f"Thieu phuong phap thong ke dac trung cho {design_type.value}",
                path_vi=(
                    f"Voi thiet ke {design_type.value}, thuong can cac phuong phap:\n" +
                    "\n".join(f"- {m}" for m in expected[:5])
                ),
                context={
                    "design_type": design_type.value,
                    "expected_methods": expected[:5]
                }
            ))

    return violations


def _check_power_calculation(
    abstract: str,
    design_type: Optional[DesignType]
) -> list[Violation]:
    """Check for power/sample size calculation."""
    violations = []
    abstract_lower = abstract.lower()

    # Designs that need power calculation
    needs_power = [
        DesignType.RCT,
        DesignType.QUASI_EXPERIMENTAL,
        DesignType.COHORT_PROSPECTIVE,
        DesignType.DIAGNOSTIC_ACCURACY,
    ]

    if design_type not in needs_power:
        return violations

    power_patterns = [
        r"(power|luc thong ke)\s*(analysis|calculation|>?=?\s*0?\.\d+|>?=?\s*\d+%)",
        r"(sample size|co mau)\s*(calculation|tinh toan|was calculated|duoc tinh)",
        r"(alpha|beta)\s*=?\s*0\.\d+",
        r"(effect size|kich thuoc hieu ung)",
        r"(g\*?power|gpower|ps\s+software)",
        r"(minimum\s+sample|co mau toi thieu)",
        r"(detectable\s+difference|phat hien duoc)",
    ]

    has_power = any(re.search(p, abstract_lower) for p in power_patterns)

    if not has_power:
        violations.append(Violation(
            code="St-02",
            tier=4,
            severity=ViolationSeverity.WARN,
            message_vi="Khong de cap tinh toan co mau/power",
            path_vi=(
                f"Voi thiet ke {design_type.value}, can mo ta:\n"
                "- Power analysis (power >= 80%)\n"
                "- Effect size du kien\n"
                "- Alpha (thuong = 0.05)\n"
                "- Cong thuc hoac phan mem tinh toan"
            ),
            context={"design_type": design_type.value if design_type else None}
        ))

    return violations


def _check_analysis_plan(
    abstract: str,
    design_type: Optional[DesignType],
    blueprint: dict
) -> list[Violation]:
    """Check clarity of analysis plan."""
    violations = []
    abstract_lower = abstract.lower()

    # Check for ITT vs per-protocol in RCTs
    if design_type == DesignType.RCT:
        itt_patterns = [
            r"(intention-?to-?treat|itt)",
            r"(per-?protocol|pp)",
            r"(as-?treated)",
            r"(modified itt|mitt)",
        ]

        has_analysis_type = any(re.search(p, abstract_lower) for p in itt_patterns)

        if not has_analysis_type:
            violations.append(Violation(
                code="St-03",
                tier=4,
                severity=ViolationSeverity.WARN,
                message_vi="RCT khong ro intention-to-treat hay per-protocol",
                path_vi=(
                    "RCT can neu ro cach phan tich:\n"
                    "- Intention-to-treat (ITT): phan tich theo nhom duoc phan bo\n"
                    "- Per-protocol (PP): chi phan tich nhung nguoi tuan thu\n"
                    "- ITT thuong la phan tich chinh"
                ),
                context={}
            ))

    # Check for handling missing data
    missing_data_patterns = [
        r"(missing data|du lieu thieu)",
        r"(imputation|multiple imputation|thay the)",
        r"(complete case|case complete)",
        r"(drop-?out|mat theo doi|loss to follow)",
        r"(sensitivity analysis|phan tich do nhay)",
    ]

    has_missing_strategy = any(re.search(p, abstract_lower) for p in missing_data_patterns)

    # Only flag for designs prone to missing data
    prone_to_missing = [
        DesignType.RCT,
        DesignType.COHORT_PROSPECTIVE,
        DesignType.BEFORE_AFTER,
    ]

    if design_type in prone_to_missing and not has_missing_strategy:
        violations.append(Violation(
            code="St-03",
            tier=4,
            severity=ViolationSeverity.WARN,
            message_vi="Khong de cap cach xu ly du lieu thieu",
            path_vi=(
                "Voi thiet ke co theo doi, can mo ta:\n"
                "- Ty le du kien mat theo doi\n"
                "- Cach xu ly missing data (imputation, complete case)\n"
                "- Sensitivity analysis"
            ),
            context={}
        ))

    return violations


def _check_statistical_details(
    abstract: str,
    design_type: Optional[DesignType]
) -> list[Violation]:
    """Check for important statistical details."""
    violations = []
    abstract_lower = abstract.lower()

    # Check for diagnostic accuracy specifics
    if design_type == DesignType.DIAGNOSTIC_ACCURACY:
        diag_patterns = [
            r"(sensitivity|do nhay)",
            r"(specificity|do dac hieu)",
            r"(ppv|positive predictive|gia tri du doan duong)",
            r"(npv|negative predictive|gia tri du doan am)",
            r"(roc|auc)",
            r"(likelihood ratio|ty so kha nang)",
        ]

        found = [p for p in diag_patterns if re.search(p, abstract_lower)]

        if len(found) < 2:
            violations.append(Violation(
                code="St-04",
                tier=4,
                severity=ViolationSeverity.WARN,
                message_vi="Nghien cuu chan doan thieu chi so chinh xac",
                path_vi=(
                    "Nghien cuu diagnostic accuracy can bao cao:\n"
                    "- Sensitivity va Specificity\n"
                    "- PPV va NPV\n"
                    "- AUC-ROC (neu co)\n"
                    "- Likelihood ratios (neu phu hop)"
                ),
                context={"found_metrics": found}
            ))

    # Check for meta-analysis specifics
    if design_type == DesignType.META_ANALYSIS:
        meta_patterns = [
            r"(heterogeneity|i-?squared|i2|khac biet)",
            r"(random effects|fixed effects)",
            r"(publication bias|sai lech xuat ban)",
            r"(forest plot)",
            r"(sensitivity analysis|phan tich do nhay)",
        ]

        found = [p for p in meta_patterns if re.search(p, abstract_lower)]

        if len(found) < 2:
            violations.append(Violation(
                code="St-04",
                tier=4,
                severity=ViolationSeverity.WARN,
                message_vi="Meta-analysis thieu cac yeu to quan trong",
                path_vi=(
                    "Meta-analysis can bao cao:\n"
                    "- Heterogeneity (I2)\n"
                    "- Model (random vs fixed effects)\n"
                    "- Publication bias assessment\n"
                    "- Sensitivity/subgroup analyses"
                ),
                context={"found_elements": found}
            ))

    # Check for survival analysis specifics
    if design_type in [DesignType.COHORT_PROSPECTIVE, DesignType.PROGNOSTIC]:
        has_survival_outcome = re.search(
            r"(survival|mortality|death|tu vong|song con|time-to-event)",
            abstract_lower
        )

        if has_survival_outcome:
            survival_patterns = [
                r"(kaplan-?meier|km)",
                r"(cox|proportional hazard)",
                r"(hazard ratio|hr)",
                r"(median survival|median follow)",
                r"(censoring|censored)",
            ]

            found = [p for p in survival_patterns if re.search(p, abstract_lower)]

            if not found:
                violations.append(Violation(
                    code="St-04",
                    tier=4,
                    severity=ViolationSeverity.WARN,
                    message_vi="Ket qua survival nhung thieu phuong phap phan tich",
                    path_vi=(
                        "Voi ket qua survival/time-to-event, can mo ta:\n"
                        "- Phuong phap (Kaplan-Meier, Cox regression)\n"
                        "- Hazard ratio voi 95% CI\n"
                        "- Cach xu ly censoring"
                    ),
                    context={}
                ))

    return violations
