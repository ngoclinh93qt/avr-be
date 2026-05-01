"""Manuscript outline generation prompts — paper-specific, research-driven.

The LLM must output a JSON array so the parser can extract structured content.
Falls back to a generic template only on parse failure.
"""

import re
import json
from typing import Optional
from app.models.schemas import ResearchBlueprint, ExtractedAttributes
from app.rules.design_rules import get_design_display_name


SYSTEM_PROMPT = """You are a senior medical researcher and academic writing mentor with 20+ years of experience publishing in high-impact clinical journals (NEJM, Lancet, JAMA, BMJ, and specialty journals). You have guided hundreds of researchers from study design through manuscript submission.

Your task is to create a manuscript outline that is:
- **Paper-specific**: every bullet point references the actual study population, intervention, outcome, and design — never generic placeholders
- **Actionable**: the researcher should be able to open Word and start writing immediately using your outline
- **Guideline-compliant**: respects CONSORT/STROBE/STARD/PRISMA/CARE as appropriate
- **Journal-aware**: respects word limits, section requirements, and style of the target journal

OUTPUT FORMAT: You must respond with a valid JSON array only — no prose before or after. Each element:
{
  "section_name": "string",
  "word_count_suggested": "e.g. 400-600 words",
  "key_points": ["specific point 1", "specific point 2", ...],
  "subsections": ["sub 1", "sub 2", ...],
  "tips": ["writing tip 1", ...]
}

Rules for key_points:
- Must mention the actual population, intervention/exposure, outcome, or design detail from the blueprint
- 4-6 points per section
- Written as action instructions ("Trình bày X", "Báo cáo Y", "So sánh Z với W")
- Never write "Background", "Gap in knowledge", "Study objective" — always fill in the actual content"""


# ─── Checklist items by guideline ────────────────────────────────────────────

def get_submission_checklist(checklist_type: str, journal_name: str = "") -> list[str]:
    """Generate submission checklist based on reporting guideline type."""
    common = [
        f"Abstract ≤ giới hạn từ của tạp chí, có cấu trúc",
        "Manuscript double-spaced, font 12pt",
        "Title page file riêng (nếu tạp chí dùng blinded review)",
        "Figures và tables có title + legend đầy đủ",
        "References đúng format yêu cầu",
        "Cover letter",
        "Author contributions (CRediT format)",
        "Conflict of interest statement",
        "Ethics approval number",
        "Data availability statement",
    ]

    guideline_items = {
        "STROBE": [
            "STROBE checklist đính kèm (observational studies)",
            "Flow diagram tuyển chọn đối tượng (khuyến khích)",
        ],
        "CONSORT": [
            "CONSORT checklist đính kèm (RCT)",
            "CONSORT flow diagram (bắt buộc)",
            "Trial registration number (ISRCTN / ClinicalTrials.gov)",
        ],
        "STARD": [
            "STARD checklist đính kèm (diagnostic accuracy)",
            "STARD flow diagram",
        ],
        "PRISMA": [
            "PRISMA checklist đính kèm (systematic review/meta-analysis)",
            "PRISMA flow diagram",
            "Protocol registration (PROSPERO)",
        ],
        "CARE": [
            "CARE checklist đính kèm (case report)",
            "Patient consent for publication",
        ],
    }

    specific = guideline_items.get(checklist_type, [])
    return specific + common


# ─── Title suggestion ─────────────────────────────────────────────────────────

def generate_title_suggestion(blueprint: ResearchBlueprint) -> str:
    """Generate a title suggestion based on the blueprint."""
    from app.models.enums import DesignType

    design_suffix_map = {
        DesignType.RCT: "A Randomized Controlled Trial",
        DesignType.COHORT_PROSPECTIVE: "A Prospective Cohort Study",
        DesignType.COHORT_RETROSPECTIVE: "A Retrospective Comparative Study",
        DesignType.CASE_CONTROL: "A Case-Control Study",
        DesignType.CROSS_SECTIONAL: "A Cross-Sectional Study",
        DesignType.DIAGNOSTIC_ACCURACY: "A Diagnostic Accuracy Study",
        DesignType.SYSTEMATIC_REVIEW: "A Systematic Review",
        DesignType.META_ANALYSIS: "A Systematic Review and Meta-Analysis",
        DesignType.CASE_SERIES: "A Case Series",
        DesignType.CASE_REPORT: "A Case Report",
        DesignType.SCOPING_REVIEW: "A Scoping Review",
        DesignType.BEFORE_AFTER: "A Before-After Comparative Study",
        DesignType.QUASI_EXPERIMENTAL: "A Quasi-Experimental Study",
    }

    suffix = design_suffix_map.get(blueprint.design_type, "An Observational Study")
    intervention = blueprint.intervention_or_exposure or ""
    comparator = blueprint.comparator or ""
    population = blueprint.population or ""

    if comparator:
        return f"{intervention} Versus {comparator} in {population}: {suffix}"
    else:
        return f"{intervention} in {population}: {suffix}"


# ─── Prompt builder ───────────────────────────────────────────────────────────

def _format_optional(label: str, value) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        return f"- {label}: {', '.join(str(v) for v in value)}\n"
    return f"- {label}: {value}\n"


def get_manuscript_outline_prompt(
    blueprint: ResearchBlueprint,
    validated_abstract: str,
    journal_metadata: Optional[dict] = None,
    custom_instructions: Optional[str] = None,
    extracted_attrs: Optional[ExtractedAttributes] = None,
) -> str:
    design_name = get_design_display_name(blueprint.design_type)
    reporting_guideline = _get_reporting_guideline(blueprint.design_type.value)

    # ── Journal context ──────────────────────────────────────────────────────
    journal_block = ""
    if journal_metadata:
        wl = journal_metadata.get("word_limits") or {}
        word_limit_str = ""
        if isinstance(wl, dict):
            word_limit_str = " | ".join(f"{k}: {v}" for k, v in wl.items())
        journal_block = f"""
TARGET JOURNAL:
- Name: {journal_metadata.get('name', 'Not specified')}
- Impact Factor: {journal_metadata.get('impact_factor', 'N/A')}
- Word limits: {word_limit_str or 'See author guidelines'}
- Section requirements: {', '.join(journal_metadata.get('section_requirements', [])) or 'Standard IMRaD'}
- Author guidelines: {journal_metadata.get('author_guidelines_url', 'Check journal website')}
"""

    # ── Blueprint — full context ─────────────────────────────────────────────
    dd = blueprint.design_details or {}

    # Build design_details block for RCT/special designs
    design_details_block = ""
    if dd:
        detail_lines = []
        for k, v in dd.items():
            if v:
                detail_lines.append(f"  - {k}: {v}")
        if detail_lines:
            design_details_block = "- Design details:\n" + "\n".join(detail_lines) + "\n"

    secondary_str = ""
    if blueprint.secondary_outcomes:
        secondary_str = "- Secondary outcomes:\n" + "\n".join(
            f"  {i+1}. {o}" for i, o in enumerate(blueprint.secondary_outcomes)
        ) + "\n"

    blueprint_block = f"""RESEARCH BLUEPRINT:
- Study design: {design_name} (reporting guideline: {reporting_guideline})
- Specialty / setting: {blueprint.specialty or 'Not specified'} — {blueprint.setting or 'Not specified'}
- Population: {blueprint.population}
- Sample size: n = {blueprint.sample_size}{(' — ' + blueprint.sample_justification) if blueprint.sample_justification else ''}
- Intervention / exposure: {blueprint.intervention_or_exposure}
{_format_optional('Comparator', blueprint.comparator)}{_format_optional('Timeframe / follow-up', blueprint.timeframe)}{design_details_block}- Primary outcome: {blueprint.primary_outcome}
{secondary_str}{_format_optional('Statistical approach', blueprint.statistical_approach)}{_format_optional('Primary analysis', blueprint.primary_analysis)}{_format_optional('Missing elements / caveats', blueprint.missing_elements if blueprint.missing_elements else None)}"""

    # ── Extracted attributes — detailed per-field data from conversation ────
    attrs_block = _build_attrs_block(extracted_attrs)

    # ── Design-specific section guidance ────────────────────────────────────
    section_guide = _get_design_section_guide(blueprint, extracted_attrs)

    # ── Custom instructions ──────────────────────────────────────────────────
    custom_block = ""
    if custom_instructions and custom_instructions.strip():
        custom_block = f"""

ADDITIONAL INSTRUCTIONS FROM RESEARCHER (high priority — override defaults if needed):
{custom_instructions.strip()}"""

    # ── Abstract ────────────────────────────────────────────────────────────
    abstract_block = ""
    if validated_abstract:
        abstract_block = f"""
VALIDATED ABSTRACT (passed Gate — use this to extract specific data points):
\"\"\"
{validated_abstract}
\"\"\"
"""

    prompt = f"""{blueprint_block}
{attrs_block}{journal_block}{abstract_block}
REPORTING GUIDELINE IN USE: {reporting_guideline}

SECTION-BY-SECTION INSTRUCTIONS:
{section_guide}

---

TASK:
Generate a detailed, paper-specific manuscript outline for this exact study.

REQUIREMENTS:
1. key_points must be SPECIFIC to this study:
   - Name the actual population ({blueprint.population[:50]}...)
   - Name the actual intervention/exposure ({blueprint.intervention_or_exposure[:50]}...)
   - Name the actual primary outcome ({blueprint.primary_outcome[:50]}...)
   - Suggest specific table/figure content (e.g. "Table 1: Baseline characteristics of {blueprint.population[:30]}...")
   - Suggest specific statistical tests appropriate for this design

2. tips must be ACTIONABLE and design-specific:
   - Reference {reporting_guideline} items where relevant
   - Flag common reviewer complaints for {design_name} studies
   - Mention journal-specific requirements if known

3. word_count_suggested must reflect the journal's limits (if provided)

4. Include these main sections (adapt subsections to the design):
{_get_required_sections(blueprint.design_type.value)}

OUTPUT: Valid JSON array only. No explanation, no markdown code fences, no text outside the array.{custom_block}"""

    return prompt


# ─── Extracted attributes block ──────────────────────────────────────────────

def _build_attrs_block(attrs: Optional[ExtractedAttributes]) -> str:
    """Serialize ExtractedAttributes into a prompt section.
    Only non-empty fields are included so the block stays concise.
    """
    if not attrs:
        return ""

    lines = []

    def add(label: str, value):
        if value is None:
            return
        if isinstance(value, list):
            if value:
                lines.append(f"- {label}: {', '.join(str(v) for v in value)}")
        elif isinstance(value, bool):
            lines.append(f"- {label}: {'Yes' if value else 'No'}")
        elif str(value).strip():
            lines.append(f"- {label}: {value}")

    # Population detail
    add("Age range", attrs.age_range)
    add("Inclusion criteria", attrs.inclusion_criteria)
    add("Exclusion criteria", attrs.exclusion_criteria)

    # Intervention / exposure detail
    add("Exposure detail", attrs.exposure)
    add("Comparator detail", attrs.comparator)

    # Outcome detail
    add("Endpoint measurable", attrs.endpoint_measurable)
    add("Secondary endpoints", attrs.secondary_endpoints)

    # RCT specifics
    add("Randomization method", attrs.randomization_method)
    add("Blinding", attrs.blinding)
    add("Allocation concealment", attrs.allocation_concealment)
    add("Measurement timepoints", attrs.timepoints)

    # Cohort / longitudinal
    add("Follow-up duration", attrs.follow_up_duration)
    add("Data source", attrs.data_source)

    # Case-control
    add("Case definition", attrs.case_definition)
    add("Control definition", attrs.control_definition)
    add("Matching criteria", attrs.matching_criteria)
    add("Case presentation", attrs.case_presentation)
    add("Key findings", attrs.key_findings)

    # Diagnostic accuracy
    add("Index test", attrs.index_test)
    add("Reference standard", attrs.reference_standard)
    add("Spectrum of disease", attrs.spectrum_of_disease)

    # Prognostic
    add("Prognostic factors", attrs.prognostic_factors)

    # Systematic review / meta-analysis
    add("Search strategy / terms", attrs.search_strategy)
    add("Databases searched", attrs.databases)
    add("Quality assessment tool", attrs.quality_assessment)
    add("Statistical pooling method", attrs.statistical_method)
    add("Heterogeneity assessment", attrs.heterogeneity_assessment)
    add("Charting form", attrs.charting_form)

    # Qualitative / mixed
    add("Data collection method", attrs.data_collection_method)
    add("Analysis approach", attrs.analysis_approach)
    add("Saturation strategy", attrs.saturation_strategy)
    add("Quantitative component", attrs.quantitative_component)
    add("Qualitative component", attrs.qualitative_component)
    add("Integration approach", attrs.integration_approach)

    # Context flags
    add("Rare disease", attrs.rare_disease_flag)
    add("Multi-centre", attrs.multi_center)

    if not lines:
        return ""

    return "EXTRACTED STUDY DETAILS (from researcher conversation — use these verbatim in key_points):\n" + "\n".join(lines) + "\n\n"


# ─── Design-specific guidance blocks ─────────────────────────────────────────

def _get_design_section_guide(blueprint: ResearchBlueprint, attrs: Optional[ExtractedAttributes] = None) -> str:
    """Return per-design writing instructions injected into the prompt."""
    dd = blueprint.design_details or {}
    design = blueprint.design_type.value

    a = attrs  # shorthand

    pop = blueprint.population
    intv = blueprint.intervention_or_exposure
    comp = blueprint.comparator or (a.comparator if a else None) or "control/standard care"
    outcome = blueprint.primary_outcome
    stat = blueprint.statistical_approach or (a.statistical_method if a else None) or "appropriate statistical tests"
    n = blueprint.sample_size
    setting = blueprint.setting or "clinical setting"

    # Pull richer attrs fields into convenience vars (fall back to dd dict)
    blinding = (a.blinding if a else None) or dd.get("blinding", "specify blinding")
    rand_method = (a.randomization_method if a else None) or dd.get("randomization_method", "describe method")
    alloc = (a.allocation_concealment if a else None) or dd.get("allocation_concealment", "describe")
    follow_up = (a.follow_up_duration if a else None) or blueprint.timeframe or "specify follow-up"
    data_source = (a.data_source if a else None) or dd.get("data_source", "medical records / registry")
    inclusion = (", ".join(a.inclusion_criteria) if a and a.inclusion_criteria else "see eligibility criteria")
    exclusion = (", ".join(a.exclusion_criteria) if a and a.exclusion_criteria else "see exclusion criteria")
    timepoints = (", ".join(a.timepoints) if a and a.timepoints else "baseline and follow-up")
    index_test = (a.index_test if a else None) or intv
    ref_std = (a.reference_standard if a else None) or dd.get("reference_standard", "gold standard")
    spectrum = (a.spectrum_of_disease if a else None) or dd.get("spectrum_of_disease", "range of disease severity")
    case_def = (a.case_definition if a else None) or dd.get("case_definition", f"how {outcome} was defined")
    ctrl_def = (a.control_definition if a else None) or dd.get("control_definition", "source, matching criteria")
    matching = (a.matching_criteria if a else None) or dd.get("matching_criteria", "variables and ratio")
    databases = (", ".join(a.databases) if a and a.databases else dd.get("databases", "PubMed, Embase, Cochrane Central"))
    qa_tool = (a.quality_assessment if a else None) or dd.get("quality_assessment", "Cochrane RoB 2.0 / NOS")
    pool_method = (a.statistical_method if a else None) or dd.get("statistical_method", "random-effects meta-analysis")
    hetero = (a.heterogeneity_assessment if a else None) or dd.get("heterogeneity_assessment", "I², Q-test, τ²")
    secondary = blueprint.secondary_outcomes or (a.secondary_endpoints if a else []) or []
    secondary_str = (", ".join(secondary[:4]) + ("..." if len(secondary) > 4 else "")) if secondary else "specify secondary outcomes"
    multi_centre = (a.multi_center if a else None) or False
    setting_detail = f"{'multi-centre, ' if multi_centre else ''}{setting}"

    guides = {
        "rct": f"""
INTRODUCTION (400-600 words):
  - Para 1: Clinical burden of the condition treated in {pop} — cite epidemiological data on prevalence/incidence
  - Para 2: Current standard of care ({comp}) — why it has gaps or limitations for {outcome}
  - Para 3: Rationale for {intv} — mechanism of action, prior Phase I/II or observational evidence
  - Para 4: Study objective — "We conducted a randomized trial to evaluate {intv} vs {comp} on {outcome} in {pop}"

METHODS (800-1200 words):
  - Study design: RCT, {dd.get('arms', 'parallel-arm')}, {blinding}, allocation 1:1
  - Setting: {setting_detail}; study period (write exact dates); ethics approval body
  - Participants: Inclusion — {inclusion}; Exclusion — {exclusion}
  - Randomization: method = {rand_method}; sequence generation; concealment = {alloc}
  - Interventions: describe {intv} (dose, route, duration, protocol) in full replication detail; describe {comp} equally
  - Outcomes: primary = {outcome} (measurement unit, instrument, timepoint {timepoints}); secondary = {secondary_str}
  - Sample size: n={n} total — state assumed effect size, α, power, dropout rate
  - Statistical: ITT primary analysis, per-protocol sensitivity; {stat}; handle missing data; multiplicity for {len(secondary)} secondary endpoints

RESULTS (600-900 words):
  - Figure 1 (CONSORT): screened → randomized → allocated → {timepoints} follow-up → analyzed
  - Table 1: Baseline characteristics of {n} participants ({intv} arm vs {comp} arm) — demographics, comorbidities, baseline {outcome}
  - Primary outcome: {outcome} — event rate / mean ± SD per arm, absolute difference, RR/OR/HR with 95% CI, p-value
  - Secondary outcomes ({secondary_str}): table or paragraph; note multiplicity adjustment
  - Adverse events: grade ≥3, SAEs, withdrawals due to AE by arm

DISCUSSION (800-1200 words):
  - Para 1 (main finding): "{intv} [improved/did not improve] {outcome} vs {comp} in {pop} (quantify the result)"
  - Para 2-3: Compare with prior RCTs and observational data on {intv} in similar populations
  - Para 4: Mechanism — biological rationale for {intv}'s effect on {outcome}
  - Para 5: Limitations — {blinding} design, follow-up {follow_up}, generalizability of {pop} to other settings
  - Para 6: Implications for clinical guidelines and future research""",

        "cohort_prospective": f"""
INTRODUCTION (400-600 words):
  - Para 1: Epidemiology of {intv} / exposure in {pop} — prevalence, incidence, clinical impact in {setting}
  - Para 2: Evidence gap — association between {intv} and {outcome} not established prospectively in {pop}
  - Para 3: Rationale for prospective cohort — why RCT is infeasible/unethical; advantages of this design
  - Para 4: Aim — "This prospective cohort study aimed to determine the association between {intv} and {outcome} in {pop} over {follow_up}"

METHODS (800-1100 words):
  - Design: prospective cohort, {setting_detail}, recruitment period
  - Participants: {pop}; inclusion — {inclusion}; exclusion — {exclusion}
  - Exposure: {intv} — definition, measurement instrument, timing; handling time-varying exposure
  - Outcome: {outcome} — ascertainment method, follow-up schedule ({timepoints}), outcome adjudication
  - Covariates: list confounders (age, sex, comorbidities, etc.) and how each was measured at baseline
  - Bias: selection bias minimization, loss-to-follow-up handling, information bias
  - Statistical: {stat}; multivariable model covariates; competing risks/censoring; follow-up {follow_up}

RESULTS (500-800 words):
  - Flow: eligible → enrolled → exposed/unexposed → lost to follow-up ({follow_up}) → analyzed
  - Table 1: Baseline characteristics by {intv} group — standardized mean differences for key variables
  - Primary: incidence of {outcome} per 1000 person-years by group; crude and adjusted HR/RR (95% CI)
  - Secondary outcomes ({secondary_str}); sensitivity analyses

DISCUSSION:
  - Main finding: quantify association between {intv} and {outcome} in {pop}
  - Compare with existing cohort/RCT evidence; explain concordance or discordance
  - Potential biases: residual confounding, loss-to-follow-up rate, exposure misclassification in {data_source}
  - Clinical/public health implications; generalizability""",

        "cohort_retrospective": f"""
INTRODUCTION (400-600 words):
  - Clinical context: importance of {outcome} in {pop} receiving {intv}
  - Evidence gap: limited prospective data; real-world evidence needed from {data_source}
  - Objective: retrospective cohort comparing {intv} vs {comp} on {outcome} in {pop}

METHODS (700-1000 words):
  - Data source: {data_source} — period, data quality, validation approach
  - Participants: {pop}; inclusion — {inclusion}; exclusion — {exclusion}; index date definition
  - Exposure: {intv} vs {comp} — how identified in {data_source} (codes, records)
  - Outcome: {outcome} — ICD/procedure codes used, validation, follow-up window {follow_up}
  - Confounding control: {stat} — propensity score matching / IPTW / multivariable regression
  - Sensitivity analyses: alternate outcome definition, different follow-up windows

RESULTS (500-800 words):
  - Cohort attrition table: identified → eligible → matched / weighted
  - Table 1: before and after matching/weighting — SMD for key variables
  - Primary result: {outcome} by {intv} vs {comp} group; adjusted effect estimate with 95% CI
  - Sensitivity analyses

DISCUSSION:
  - Real-world estimate vs RCT data; explain differences (confounding, population, setting)
  - {data_source} limitations: coding accuracy, missing variables, unmeasured confounders
  - Implications for practice guidelines""",

        "case_control": f"""
INTRODUCTION (350-500 words):
  - Burden of {outcome} in {pop} — incidence, severity, clinical importance
  - Known risk factors; gap: role of {intv} as exposure not established in {pop}
  - Rationale for case-control — efficient for rare outcome {outcome}; feasibility
  - Objective: determine association between {intv} and {outcome} in {pop}

METHODS (600-900 words):
  - Case definition: {case_def}; ascertainment source ({data_source})
  - Control definition: {ctrl_def}; sampling, eligibility
  - Matching: {matching} — ratio, variables, procedures
  - Exposure assessment: {intv} — recall period, instrument (recall bias minimization)
  - Covariates: list potential confounders for {intv}→{outcome}; how each was measured
  - Statistical: conditional logistic regression, matched OR with 95% CI; {stat}

RESULTS (400-700 words):
  - Flow: cases identified → eligible → enrolled (n=?); controls matched (n=?)
  - Table 1: {pop} cases vs matched controls — demographics, comorbidities, {intv} exposure rates
  - Crude and adjusted OR for {intv} on {outcome} (95% CI, p)
  - Dose-response analysis if {intv} is quantifiable; interaction analyses

DISCUSSION:
  - Main OR: contextualize against prior case-control and cohort data on {intv} and {outcome}
  - Recall bias (exposure {intv}), selection bias, residual confounding
  - Implications for prevention/screening in {pop}""",

        "cross_sectional": f"""
INTRODUCTION (350-500 words):
  - Prevalence and burden of {outcome} in {pop} at {setting}
  - Unknown: population-level association between {intv} and {outcome} in {pop}
  - Objective: estimate prevalence of {outcome} and its association with {intv} in {pop} (n={n})

METHODS (600-900 words):
  - Study: cross-sectional survey / data analysis; {setting_detail}; sampling method
  - Participants: {pop}; inclusion — {inclusion}; exclusion — {exclusion}; n={n}
  - Measurement of {intv}: instrument, validity, reliability
  - Measurement of {outcome}: instrument, cutoffs, validity
  - Statistical: prevalence with 95% CI; logistic/Poisson regression for {intv}↔{outcome}; {stat}; survey weighting if applicable

RESULTS (400-600 words):
  - Response rate, participant flow
  - Prevalence of {outcome} overall and stratified by {intv} group
  - Table 1: demographic characteristics of {n} participants
  - Crude and adjusted OR/PR for {intv} on {outcome} (95% CI)

DISCUSSION:
  - Prevalence of {outcome} vs regional/national benchmarks
  - Cross-sectional limitations: no temporality, reverse causality for {intv}↔{outcome}
  - Implications for screening and prevention in {pop}""",

        "diagnostic_accuracy": f"""
INTRODUCTION (350-500 words):
  - {outcome} condition in {pop}: prevalence, clinical impact of delayed/inaccurate diagnosis
  - Current reference standard = {ref_std} — limitations (cost, invasiveness, access) in {setting}
  - Index test = {index_test} — proposed advantages; prior pilot/validation data
  - Objective: evaluate diagnostic accuracy of {index_test} vs {ref_std} in {pop} with {spectrum}

METHODS (600-900 words):
  - Design: prospective diagnostic accuracy study, STARD 2015-compliant
  - Setting: {setting_detail}; study period; ethics
  - Participants: {pop}; inclusion — {inclusion}; exclusion — {exclusion}; spectrum of disease = {spectrum}
  - Index test: {index_test} — full procedure, operator training, blinding to reference standard, prespecified cutoff
  - Reference standard: {ref_std} — full procedure, timing relative to {index_test}, blinding to index result
  - Statistical: 2×2 table, Se/Sp/PPV/NPV with 95% CI (Wilson method), AUC; {stat}; subgroup by disease severity

RESULTS (400-600 words):
  - Figure 1 (STARD): enrolled → {index_test} result → {ref_std} result → final classification
  - 2×2 contingency table (TP, FP, FN, TN)
  - Se, Sp, PPV, NPV at prespecified cutoff with 95% CI; AUC
  - Subgroup analyses by {spectrum}

DISCUSSION:
  - How Se={index_test} compares to existing tests for {outcome} in {pop}
  - Clinical consequence of false positives vs false negatives: optimal cutoff trade-off
  - Spectrum bias, verification bias, prevalence effects on PPV/NPV
  - Implementation and cost-effectiveness pathway in {setting}""",

        "systematic_review": f"""
INTRODUCTION (400-600 words):
  - Clinical question: effect/association of {intv} on {outcome} in {pop}
  - Why this systematic review is needed now: prior reviews outdated / missing {pop} / conflicting RCT results
  - Objective: "To systematically review and meta-analyse evidence on {intv} and {outcome} in {pop}"

METHODS (800-1200 words, PRISMA 2020-compliant):
  - Protocol: PROSPERO registration; a priori protocol deviations documented
  - Eligibility (PICO): Population = {pop}; Intervention = {intv}; Comparator = {comp}; Outcome = {outcome}; study designs included
  - Databases: {databases} — full date ranges; grey literature (ClinicalTrials.gov, WHO ICTRP, conference abstracts)
  - Search strategy: Boolean string with MeSH + free-text; append as Supplementary Table S1
  - Selection: two independent reviewers (title/abstract → full-text); disagreement → third reviewer; PRISMA flow
  - Data extraction: standardized form — study characteristics, n, effect estimates, {outcome} data; duplicate extraction
  - Risk of bias: {qa_tool} — two reviewers independently
  - Synthesis: {pool_method}; heterogeneity = {hetero}; subgroup analyses (pre-specified); publication bias: funnel plot + Egger test

RESULTS (600-1000 words):
  - Figure 1 (PRISMA 2020): records from {databases} → deduplicated → screened → full-text → included (n=?)
  - Table 1: characteristics of included studies (author, year, design, {pop}, {intv} dose, follow-up, {outcome})
  - Figure 2 (Forest plot): pooled effect of {intv} on {outcome} — ES with 95% CI, I², weight per study
  - Subgroup analyses; publication bias figures; GRADE evidence summary table
  - Subgroup analyses, publication bias (funnel plot, Egger's test)

DISCUSSION (600-900 words):
  - Main pooled estimate: {intv} on {outcome} in {pop} — clinical context
  - Heterogeneity (I²=?) sources — explain via subgroup (design, population, dose, follow-up)
  - Quality of evidence: GRADE summary — reasons for downgrading (risk of bias, inconsistency, imprecision)
  - Implications for clinical guidelines; future RCT needs""",
    }

    # For designs not explicitly listed, generate a generic evidence-based guide
    guide = guides.get(design)
    if not guide:
        guide = f"""
INTRODUCTION (400-600 words):
  - Clinical context: burden of disease in {pop}; role of {intv}
  - Evidence gap: what is unknown about {outcome} in {pop}
  - Objective: "This study aimed to evaluate {intv} on {outcome} in {pop} (n={n})"

METHODS (700-1000 words):
  - Study design, {setting_detail}, study period
  - Participants: {pop}; inclusion — {inclusion}; exclusion — {exclusion}; n={n}
  - Intervention/exposure: {intv} vs {comp} — definition, measurement
  - Outcome: {outcome} — definition, instrument, timepoints ({timepoints})
  - Statistical: {stat}; handle missing data; sensitivity analyses

RESULTS (500-800 words):
  - Participant flow diagram
  - Table 1: baseline characteristics of {n} participants
  - {outcome}: main result with effect estimate and 95% CI
  - Secondary outcomes ({secondary_str})

DISCUSSION (700-1000 words):
  - Main finding stated quantitatively for {outcome}
  - Comparison with existing literature on {intv} in {pop}
  - Limitations specific to this design
  - Implications for clinical practice"""

    return guide.strip()


def _get_reporting_guideline(design_type: str) -> str:
    mapping = {
        "rct": "CONSORT 2010",
        "quasi_experimental": "CONSORT extension",
        "before_after": "CONSORT extension",
        "cohort_prospective": "STROBE",
        "cohort_retrospective": "STROBE",
        "case_control": "STROBE",
        "cross_sectional": "STROBE",
        "diagnostic_accuracy": "STARD 2015",
        "systematic_review": "PRISMA 2020",
        "meta_analysis": "PRISMA 2020",
        "scoping_review": "PRISMA-ScR",
        "case_report": "CARE",
        "case_series": "CARE / JBI",
    }
    return mapping.get(design_type, "EQUATOR guidelines")


def _get_required_sections(design_type: str) -> str:
    sections = {
        "rct": "  Title, Abstract (structured: Background/Objective/Methods/Results/Conclusion), Introduction, Methods (subsections), Results, Discussion, Conclusion, References, Supplementary (CONSORT checklist, trial protocol if required)",
        "quasi_experimental": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "before_after": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "cohort_prospective": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "cohort_retrospective": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "case_control": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "cross_sectional": "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References",
        "diagnostic_accuracy": "  Title, Abstract (structured: Objective/Methods/Results/Conclusion), Introduction, Methods (STARD-ordered), Results, Discussion, Conclusion, References",
        "systematic_review": "  Title, Abstract (structured), Introduction, Methods (PRISMA subsections), Results, Discussion (with GRADE table), Conclusion, References",
        "meta_analysis": "  Title, Abstract (structured), Introduction, Methods (PRISMA subsections), Results, Discussion (with GRADE table), Conclusion, References",
        "scoping_review": "  Title, Abstract, Introduction, Methods (PRISMA-ScR framework), Results, Discussion, Conclusion, References",
        "case_report": "  Title, Abstract, Introduction, Case Presentation, Discussion, Conclusion, Patient Consent, References",
        "case_series": "  Title, Abstract, Introduction, Methods, Case Presentations, Discussion, Conclusion, References",
    }
    return sections.get(design_type, "  Title, Abstract, Introduction, Methods, Results, Discussion, Conclusion, References")


# ─── LLM response parser ──────────────────────────────────────────────────────

def parse_llm_outline_response(text: str) -> list[dict] | None:
    """
    Extract JSON array from LLM response.

    Returns list of section dicts on success, None on failure.
    """
    if not text:
        return None

    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Try direct parse first
    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and data:
            return _validate_sections(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract JSON array via regex (handles leading/trailing prose)
    match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list) and data:
                return _validate_sections(data)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _validate_sections(data: list) -> list[dict]:
    """Ensure each section has required fields with correct types."""
    valid = []
    for item in data:
        if not isinstance(item, dict):
            continue
        section = {
            "section_name": str(item.get("section_name") or "Section"),
            "word_count_suggested": str(item.get("word_count_suggested") or ""),
            "key_points": [str(p) for p in (item.get("key_points") or [])],
            "subsections": [str(s) for s in (item.get("subsections") or [])],
            "tips": [str(t) for t in (item.get("tips") or [])],
        }
        valid.append(section)
    return valid if valid else None


# ─── Default fallback outline ─────────────────────────────────────────────────

# Section templates by design type (used only as fallback)
_SECTION_TEMPLATES = {
    "rct": [
        ("Title", "15-20 words"),
        ("Abstract", "250-300 words"),
        ("Introduction", "400-600 words"),
        ("Methods", "800-1200 words"),
        ("Results", "600-900 words"),
        ("Discussion", "800-1200 words"),
        ("Conclusion", "150-250 words"),
        ("References", "30-40 references"),
    ],
    "cohort": [
        ("Title", "15-20 words"),
        ("Abstract", "250-300 words"),
        ("Introduction", "400-600 words"),
        ("Methods", "700-1000 words"),
        ("Results", "500-800 words"),
        ("Discussion", "700-1000 words"),
        ("Conclusion", "150-200 words"),
        ("References", "25-40 references"),
    ],
    "diagnostic": [
        ("Title", "15-20 words"),
        ("Abstract", "250-300 words"),
        ("Introduction", "400-500 words"),
        ("Methods", "700-1000 words"),
        ("Results", "400-700 words"),
        ("Discussion", "600-900 words"),
        ("Conclusion", "150-200 words"),
        ("References", "25-35 references"),
    ],
    "systematic_review": [
        ("Title", "15-25 words"),
        ("Abstract", "300-350 words"),
        ("Introduction", "400-600 words"),
        ("Methods", "800-1200 words"),
        ("Results", "600-1000 words"),
        ("Discussion", "700-1000 words"),
        ("Conclusion", "150-250 words"),
        ("References", "40-60 references"),
    ],
    "case_report": [
        ("Title", "15-20 words"),
        ("Abstract", "150-250 words"),
        ("Introduction", "200-350 words"),
        ("Case Presentation", "400-700 words"),
        ("Discussion", "400-700 words"),
        ("Conclusion", "100-150 words"),
        ("References", "10-20 references"),
    ],
}


def _get_design_key_fallback(design_type: str) -> str:
    mapping = {
        "rct": "rct",
        "quasi_experimental": "rct",
        "before_after": "rct",
        "cohort_prospective": "cohort",
        "cohort_retrospective": "cohort",
        "case_control": "cohort",
        "cross_sectional": "cohort",
        "diagnostic_accuracy": "diagnostic",
        "systematic_review": "systematic_review",
        "meta_analysis": "systematic_review",
        "scoping_review": "systematic_review",
        "case_report": "case_report",
        "case_series": "case_report",
    }
    return mapping.get(design_type, "cohort")


def get_default_outline(
    blueprint: ResearchBlueprint,
    journal_metadata: Optional[dict] = None,
    extracted_attrs: Optional[ExtractedAttributes] = None,
) -> list[dict]:
    """
    Fallback outline — used only when LLM call fails.
    Injects blueprint-specific content into key_points where possible.
    """
    design_key = _get_design_key_fallback(blueprint.design_type.value)
    sections = _SECTION_TEMPLATES.get(design_key, _SECTION_TEMPLATES["cohort"])
    reporting = _get_reporting_guideline(blueprint.design_type.value)

    a = extracted_attrs
    pop = blueprint.population
    intv = blueprint.intervention_or_exposure
    comp = blueprint.comparator or (a.comparator if a else None) or "nhóm chứng"
    outcome = blueprint.primary_outcome
    stat = blueprint.statistical_approach or (a.statistical_method if a else None) or "phương pháp thống kê phù hợp"
    n = blueprint.sample_size
    setting = blueprint.setting or "cơ sở nghiên cứu"
    follow_up = (a.follow_up_duration if a else None) or blueprint.timeframe or "theo dõi"
    incl = (", ".join(a.inclusion_criteria) if a and a.inclusion_criteria else "mô tả tiêu chí nhận")
    excl = (", ".join(a.exclusion_criteria) if a and a.exclusion_criteria else "mô tả tiêu chí loại")
    timepoints = (", ".join(a.timepoints) if a and a.timepoints else "baseline và follow-up")
    secondary = blueprint.secondary_outcomes or (a.secondary_endpoints if a else []) or []
    secondary_str = (", ".join(secondary[:3]) + ("..." if len(secondary) > 3 else "")) if secondary else "kết cục phụ"

    key_points_map = {
        "Introduction": [
            f"Đoạn 1: Nêu gánh nặng lâm sàng liên quan đến {pop} — dẫn dữ liệu dịch tễ",
            f"Đoạn 2: Khoảng trống bằng chứng — tác động của {intv} lên {outcome} chưa được xác định rõ trong {pop}",
            f"Đoạn 3: Lý do chọn thiết kế {get_design_display_name(blueprint.design_type)} cho câu hỏi này",
            f"Đoạn 4 (câu mục tiêu): 'Nghiên cứu này nhằm đánh giá {intv} so với {comp} về {outcome} ở {pop}'",
        ],
        "Methods": [
            f"Thiết kế: {get_design_display_name(blueprint.design_type)}, địa điểm: {setting}",
            f"Đối tượng: {pop} (n={n}); tiêu chí nhận — {incl}; tiêu chí loại — {excl}",
            f"Can thiệp/Phơi nhiễm: {intv}; so sánh với: {comp}; mô tả đủ chi tiết để tái lập",
            f"Kết cục chính: {outcome} — công cụ đo, đơn vị, thời điểm ({timepoints})",
            f"Kết cục phụ: {secondary_str}",
            f"Phân tích thống kê: {stat}; xử lý missing data; follow-up {follow_up}",
        ],
        "Results": [
            f"Sơ đồ tuyển chọn (theo {reporting}): đã sàng lọc → đủ điều kiện → tuyển → phân tích",
            f"Bảng 1: Đặc điểm nền của {n} đối tượng ({pop}) theo nhóm {intv} và {comp}",
            f"Kết cục chính: {outcome} — báo cáo trị số tuyệt đối, hiệu số, 95% CI, p-value",
            f"Kết cục phụ ({secondary_str}): bảng hoặc đoạn văn",
        ],
        "Discussion": [
            f"Đoạn 1: Phát hiện chính — '{intv} [cải thiện/không cải thiện] {outcome} so với {comp} ở {pop}' (định lượng rõ)",
            f"Đoạn 2-3: So sánh với các nghiên cứu trước về {intv} trên {outcome} trong quần thể tương tự",
            f"Đoạn 4: Giải thích cơ chế sinh học/lâm sàng cho kết quả quan sát được",
            f"Đoạn 5: Hạn chế đặc thù của thiết kế {get_design_display_name(blueprint.design_type)}",
            f"Đoạn 6: Ý nghĩa lâm sàng và hướng nghiên cứu tiếp theo",
        ],
    }

    tips_map = {
        "Introduction": [
            f"Kết thúc bằng câu mục tiêu rõ ràng: 'We aimed to evaluate {intv} on {outcome} in {pop}'",
            "Không review toàn bộ lịch sử — chỉ nêu gap cụ thể dẫn đến nghiên cứu này",
            "Mỗi claim phải có citation; tránh over-claim",
        ],
        "Methods": [
            f"Tuân thủ {reporting}: kiểm tra từng mục trong checklist",
            "Đủ chi tiết để reproduce — mô tả protocol, không phải kết quả",
            f"Nêu rõ cỡ mẫu n={n} và lý do tính cỡ mẫu",
        ],
        "Results": [
            "Trình bày data, không interpret — giữ interpretation cho Discussion",
            "Luôn báo cáo effect size + 95% CI, không chỉ p-value",
            "Dùng bảng cho data phức tạp, hình cho trend/survival",
        ],
        "Discussion": [
            "Bắt đầu bằng câu tóm tắt main finding — không lặp lại Results",
            "So sánh định lượng với ít nhất 2-3 nghiên cứu tương tự",
            "Limitations: trung thực và cụ thể — reviewer biết bạn biết = credibility",
        ],
        "Conclusion": [
            f"1-2 câu: kết quả {outcome} của {intv} và ý nghĩa thực tế",
            "Không đưa thêm thông tin mới — chỉ kết luận từ kết quả đã trình bày",
        ],
    }

    outline = []
    for section_name, word_count in sections:
        outline.append({
            "section_name": section_name,
            "word_count_suggested": word_count,
            "key_points": key_points_map.get(section_name, []),
            "subsections": _get_default_subsections(section_name, blueprint.design_type.value),
            "tips": tips_map.get(section_name, []),
        })

    return outline


def _get_default_subsections(section_name: str, design_type: str) -> list[str]:
    subs = {
        "Methods": {
            "rct": ["Study design and setting", "Participants", "Randomization and blinding", "Interventions", "Outcomes", "Sample size", "Statistical analysis"],
            "cohort": ["Study design and setting", "Participants", "Variables", "Data sources", "Bias", "Sample size", "Statistical analysis"],
            "diagnostic": ["Study design", "Participants", "Index test", "Reference standard", "Analysis"],
            "systematic_review": ["Protocol and registration", "Eligibility criteria", "Search strategy", "Selection process", "Data extraction", "Risk of bias", "Synthesis"],
        },
        "Results": {
            "rct": ["Participant flow", "Baseline characteristics", "Primary outcome", "Secondary outcomes", "Adverse events"],
            "cohort": ["Participants", "Descriptive data", "Main results", "Sensitivity analyses"],
            "diagnostic": ["Participants", "Test results", "Diagnostic accuracy", "ROC analysis"],
            "systematic_review": ["Study selection", "Study characteristics", "Risk of bias", "Synthesis results"],
        },
    }

    key = _get_design_key_fallback(design_type)
    return subs.get(section_name, {}).get(key, [])


def calculate_total_word_count(outline: list[dict]) -> str:
    """Calculate estimated total word count from outline."""
    total_min = 0
    total_max = 0

    for section in outline:
        word_range = section.get("word_count_suggested", "0")
        match = re.search(r"(\d+)-(\d+)", word_range)
        if match:
            total_min += int(match.group(1))
            total_max += int(match.group(2))

    if total_min == 0:
        return "~3,000-5,000 words"
    return f"{total_min:,}-{total_max:,} words"
