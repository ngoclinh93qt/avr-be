"""Blueprint builder for Research Formation System.

This module builds a structured ResearchBlueprint from
extracted attributes.
"""

from typing import Optional

from app.models.schemas import ExtractedAttributes, ResearchBlueprint
from app.models.enums import DesignType
from app.rules.design_rules import (
    infer_design_structural,
    get_required_elements,
    get_design_display_name
)


def build_blueprint(
    attributes: ExtractedAttributes,
    design_type: Optional[DesignType] = None
) -> ResearchBlueprint:
    """
    Build a ResearchBlueprint from extracted attributes.

    Args:
        attributes: Extracted attributes from conversation
        design_type: Explicitly specified design type (if any)

    Returns:
        ResearchBlueprint object
    """
    attr_dict = attributes.model_dump()

    # Determine design type
    if design_type:
        final_design = design_type
    elif attributes.design_type:
        final_design = attributes.design_type
    else:
        final_design = DesignType.UNKNOWN

    # Get structural requirements for this design
    structural = infer_design_structural(final_design)

    # Build design details
    design_details = _build_design_details(attr_dict, final_design, structural)

    # Determine intervention or exposure
    intervention_or_exposure = attr_dict.get("intervention") or attr_dict.get("exposure") or ""

    # Build secondary outcomes list
    secondary_outcomes = attr_dict.get("secondary_endpoints") or []
    if isinstance(secondary_outcomes, str):
        secondary_outcomes = [secondary_outcomes]

    # Check for missing elements
    required = get_required_elements(final_design)
    missing = []
    for elem in required:
        if elem not in attr_dict or not attr_dict.get(elem):
            missing.append(elem)

    # Build warnings
    warnings = _generate_warnings(attr_dict, final_design)

    # Determine statistical approach based on design
    stat_approach = _suggest_statistical_approach(final_design, attr_dict)

    blueprint = ResearchBlueprint(
        # Core PICO(T)
        population=attr_dict.get("population") or "",
        intervention_or_exposure=intervention_or_exposure,
        comparator=attr_dict.get("comparator"),
        primary_outcome=attr_dict.get("primary_endpoint") or "",
        secondary_outcomes=secondary_outcomes,
        timeframe=attr_dict.get("duration"),

        # Design
        design_type=final_design,
        design_details=design_details,

        # Sample
        sample_size=attr_dict.get("sample_size") or 0,
        sample_justification=_generate_sample_justification(attr_dict),

        # Methods
        statistical_approach=stat_approach,
        primary_analysis=_suggest_primary_analysis(final_design),

        # Metadata
        specialty=attr_dict.get("specialty"),
        setting=attr_dict.get("setting"),

        # Completeness
        missing_elements=missing,
        warnings=warnings,
    )

    return blueprint


def _build_design_details(
    attrs: dict,
    design_type: DesignType,
    structural: dict
) -> dict:
    """Build design-specific details."""
    details = {}

    if design_type == DesignType.RCT:
        details["type"] = "Randomized Controlled Trial"
        details["randomization"] = attrs.get("randomization_method", "Chua xac dinh")
        details["blinding"] = attrs.get("blinding", "Chua xac dinh")
        details["allocation"] = attrs.get("allocation_concealment", "Chua xac dinh")

        if structural.get("needs_arms"):
            details["arms"] = structural.get("min_arms", 2)

    elif design_type in [DesignType.COHORT_PROSPECTIVE, DesignType.COHORT_RETROSPECTIVE]:
        details["type"] = "Cohort Study"
        details["direction"] = structural.get("direction", "")
        details["follow_up"] = attrs.get("follow_up_duration", attrs.get("duration", ""))

    elif design_type == DesignType.CASE_CONTROL:
        details["type"] = "Case-Control Study"
        details["matching"] = attrs.get("matching_criteria", "Chua xac dinh")
        details["case_definition"] = attrs.get("case_definition", "")
        details["control_definition"] = attrs.get("control_definition", "")

    elif design_type == DesignType.CROSS_SECTIONAL:
        details["type"] = "Cross-Sectional Study"
        details["timepoint"] = "Single timepoint"

    elif design_type == DesignType.DIAGNOSTIC_ACCURACY:
        details["type"] = "Diagnostic Accuracy Study"
        details["index_test"] = attrs.get("intervention", "")
        details["reference_standard"] = attrs.get("reference_standard", "Chua xac dinh")

    elif design_type in [DesignType.SYSTEMATIC_REVIEW, DesignType.META_ANALYSIS]:
        details["type"] = design_type.value.replace("_", " ").title()
        details["databases"] = attrs.get("databases", [])
        details["search_strategy"] = attrs.get("search_strategy", "")

    elif design_type == DesignType.CASE_SERIES:
        details["type"] = "Case Series"
        details["consecutive"] = True

    elif design_type == DesignType.CASE_REPORT:
        details["type"] = "Case Report"

    else:
        details["type"] = get_design_display_name(design_type)

    return details


def _generate_warnings(attrs: dict, design_type: DesignType) -> list[str]:
    """Generate warnings based on attributes and design."""
    warnings = []

    # Sample size warnings
    sample = attrs.get("sample_size")
    if sample:
        if design_type == DesignType.RCT and sample < 50:
            warnings.append(f"Co mau RCT nho (n={sample}). Can power analysis.")
        elif design_type in [DesignType.COHORT_PROSPECTIVE, DesignType.COHORT_RETROSPECTIVE]:
            if sample < 100:
                warnings.append(f"Co mau cohort nho (n={sample}).")

    # Endpoint warnings
    if not attrs.get("endpoint_measurable"):
        warnings.append("Primary endpoint co the chua du cu the/do luong duoc.")

    # Design-specific warnings
    if design_type == DesignType.RCT:
        if not attrs.get("comparator"):
            warnings.append("RCT can xac dinh nhom doi chung.")
        if not attrs.get("blinding"):
            warnings.append("RCT can xac dinh phuong phap lam mu.")

    if design_type == DesignType.CASE_CONTROL:
        if not attrs.get("matching_criteria"):
            warnings.append("Case-control can xac dinh tieu chi ghep cap.")

    # Rare disease flag
    if attrs.get("rare_disease_flag") and not attrs.get("rare_disease_confirmed"):
        warnings.append("Phat hien benh hiem - can xac nhan de dieu chinh danh gia co mau.")

    return warnings


def _generate_sample_justification(attrs: dict) -> Optional[str]:
    """Generate sample size justification text."""
    sample = attrs.get("sample_size")
    if not sample:
        return None

    # Check if power calculation mentioned
    if attrs.get("power_calculation"):
        return f"Tinh toan co mau dua tren power analysis: n={sample}"

    # Rare disease
    if attrs.get("rare_disease_confirmed"):
        return f"Benh hiem gap: n={sample} la hop ly do han che ve dan so benh."

    return f"Co mau du kien: n={sample}. Can bo sung power analysis."


def _suggest_statistical_approach(design_type: DesignType, attrs: dict) -> str:
    """Suggest statistical approach based on design."""
    approaches = {
        DesignType.RCT: (
            "- Intention-to-treat analysis (primary)\n"
            "- Per-protocol analysis (secondary)\n"
            "- Chi-square/Fisher cho bien phan loai\n"
            "- T-test/Mann-Whitney cho bien lien tuc"
        ),
        DesignType.COHORT_PROSPECTIVE: (
            "- Kaplan-Meier cho thoi gian den su kien\n"
            "- Cox regression cho hazard ratio\n"
            "- Multivariate analysis dieu chinh confounders"
        ),
        DesignType.COHORT_RETROSPECTIVE: (
            "- Logistic regression cho OR\n"
            "- Multivariate analysis\n"
            "- Propensity score matching (neu can)"
        ),
        DesignType.CASE_CONTROL: (
            "- Conditional logistic regression\n"
            "- Odds ratio voi 95% CI\n"
            "- Stratified analysis"
        ),
        DesignType.CROSS_SECTIONAL: (
            "- Mo ta (ty le, trung binh, trung vi)\n"
            "- Chi-square cho lien quan\n"
            "- Logistic regression cho OR"
        ),
        DesignType.DIAGNOSTIC_ACCURACY: (
            "- Sensitivity, Specificity\n"
            "- PPV, NPV\n"
            "- ROC-AUC\n"
            "- Likelihood ratios"
        ),
        DesignType.META_ANALYSIS: (
            "- Random/fixed effects model\n"
            "- Heterogeneity (I2)\n"
            "- Publication bias assessment\n"
            "- Subgroup/sensitivity analysis"
        ),
    }

    return approaches.get(design_type, "Can xac dinh dua tren thiet ke cu the")


def _suggest_primary_analysis(design_type: DesignType) -> str:
    """Suggest primary analysis method."""
    analyses = {
        DesignType.RCT: "ITT analysis with chi-square or t-test",
        DesignType.COHORT_PROSPECTIVE: "Cox proportional hazards regression",
        DesignType.COHORT_RETROSPECTIVE: "Multivariate logistic regression",
        DesignType.CASE_CONTROL: "Conditional logistic regression",
        DesignType.CROSS_SECTIONAL: "Prevalence estimation with 95% CI",
        DesignType.DIAGNOSTIC_ACCURACY: "2x2 table analysis for Se/Sp",
        DesignType.META_ANALYSIS: "Random effects meta-analysis",
    }

    return analyses.get(design_type, "To be determined")


def blueprint_to_display(blueprint: ResearchBlueprint) -> dict:
    """Convert blueprint to display-friendly format."""
    return {
        "PICO(T)": {
            "Population (P)": blueprint.population,
            "Intervention/Exposure (I)": blueprint.intervention_or_exposure,
            "Comparator (C)": blueprint.comparator or "N/A",
            "Outcome (O)": blueprint.primary_outcome,
            "Timeframe (T)": blueprint.timeframe or "N/A",
        },
        "Thiet ke": {
            "Loai": get_design_display_name(blueprint.design_type),
            "Chi tiet": blueprint.design_details,
        },
        "Co mau": {
            "So luong": blueprint.sample_size,
            "Ly do": blueprint.sample_justification or "Chua xac dinh",
        },
        "Phuong phap thong ke": blueprint.statistical_approach,
        "Ket qua phu": blueprint.secondary_outcomes or [],
        "Canh bao": blueprint.warnings,
        "Can bo sung": blueprint.missing_elements,
    }


def validate_blueprint(blueprint: ResearchBlueprint) -> tuple[bool, list[str]]:
    """
    Validate a blueprint for completeness.

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    if not blueprint.population:
        issues.append("Thieu Population")

    if not blueprint.primary_outcome:
        issues.append("Thieu Primary Outcome")

    if blueprint.design_type == DesignType.UNKNOWN:
        issues.append("Chua xac dinh Design Type")

    if blueprint.sample_size == 0:
        # OK for some designs
        if blueprint.design_type not in [
            DesignType.SYSTEMATIC_REVIEW,
            DesignType.META_ANALYSIS,
            DesignType.SCOPING_REVIEW,
            DesignType.QUALITATIVE,
        ]:
            issues.append("Chua xac dinh Sample Size")

    return len(issues) == 0, issues
