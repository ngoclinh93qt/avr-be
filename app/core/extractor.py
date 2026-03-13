"""Attribute extraction from user input.

This module extracts research attributes from user messages
using rule-based parsing and pattern matching.
"""

import re
from typing import Optional, Any

from app.models.schemas import ExtractedAttributes
from app.models.enums import DesignType
from app.rules.design_rules import infer_design_type
from app.rules.endpoint_rules import is_endpoint_measurable, extract_endpoints
from app.rules.feasibility_rules import detect_rare_disease


# Number extraction patterns
NUMBER_PATTERNS = [
    r"n\s*=\s*(\d+)",
    r"(\d+)\s*(benh nhan|patient|ca|case|doi tuong|subject|participant|nguoi)",
    r"(co mau|sample size|sample)\s*[:=]?\s*(\d+)",
    r"(\d+)\s*(nguoi|tre|tre em|benh nhi|benh nhan)",
    r"(tuyen|recruited|enrolled)\s*(\d+)",
]

# Age range patterns
AGE_PATTERNS = [
    r"(\d+)\s*(-|den|to)\s*(\d+)\s*(tuoi|year|yo|y\.?o\.?)",
    r"(tre em|children|pediatric|nhi)",
    r"(nguoi lon|adult)",
    r"(nguoi gia|elderly|geriatric)",
    r"(so sinh|newborn|neonatal)",
]

# Time/duration patterns
DURATION_PATTERNS = [
    r"(\d+)\s*(ngay|day)",
    r"(\d+)\s*(tuan|week)",
    r"(\d+)\s*(thang|month)",
    r"(\d+)\s*(nam|year)",
    r"(tu|from)\s*(\d{1,2})/(\d{4})\s*(den|to)\s*(\d{1,2})/(\d{4})",
]

# Setting patterns
SETTING_PATTERNS = [
    r"(benh vien|hospital)\s*([\w\s]+)",
    r"(khoa|department)\s*([\w\s]+)",
    r"(trung tam|center)\s*([\w\s]+)",
    r"(tai|at)\s*(benh vien|hospital|khoa|department)",
]


def extract_attributes(
    text: str,
    existing: Optional[ExtractedAttributes] = None
) -> ExtractedAttributes:
    """
    Extract research attributes from text.

    This is the main extraction function that combines multiple
    rule-based extractors.

    Args:
        text: User input text
        existing: Existing attributes to merge with

    Returns:
        ExtractedAttributes with extracted values
    """
    if existing:
        attrs = existing.model_copy()
    else:
        attrs = ExtractedAttributes()

    text_lower = text.lower()

    # Extract design type
    design = infer_design_type(text)
    if design != DesignType.UNKNOWN:
        attrs.design_type = design

    # Extract sample size
    sample_size = _extract_sample_size(text_lower)
    if sample_size:
        attrs.sample_size = sample_size

    # Extract population
    population = _extract_population(text)
    if population:
        attrs.population = population

    # Extract age range
    age_range = _extract_age_range(text_lower)
    if age_range:
        attrs.age_range = age_range

    # Extract intervention
    intervention = _extract_intervention(text)
    if intervention:
        attrs.intervention = intervention

    # Extract comparator
    comparator = _extract_comparator(text)
    if comparator:
        attrs.comparator = comparator

    # Extract endpoints
    endpoints = _extract_all_endpoints(text)
    if endpoints.get("primary"):
        attrs.primary_endpoint = endpoints["primary"]
        # Check if measurable
        is_measurable, _, _ = is_endpoint_measurable(endpoints["primary"])
        attrs.endpoint_measurable = is_measurable
    if endpoints.get("secondary"):
        attrs.secondary_endpoints = endpoints["secondary"]

    # Extract setting
    setting = _extract_setting(text)
    if setting:
        attrs.setting = setting

    # Extract duration (general)
    duration = _extract_duration(text)
    if duration:
        attrs.duration = duration

    # ── RCT / Interventional ──────────────────────────────────────────────
    randomization_method = _extract_randomization_method(text_lower)
    if randomization_method:
        attrs.randomization_method = randomization_method

    blinding = _extract_blinding(text_lower)
    if blinding:
        attrs.blinding = blinding

    allocation = _extract_allocation_concealment(text_lower)
    if allocation:
        attrs.allocation_concealment = allocation

    # ── Cohort / Longitudinal ─────────────────────────────────────────────
    follow_up = _extract_follow_up_duration(text_lower)
    if follow_up:
        attrs.follow_up_duration = follow_up

    data_source = _extract_data_source(text_lower)
    if data_source:
        attrs.data_source = data_source

    # ── Case-control / Case studies ───────────────────────────────────────
    case_def = _extract_case_definition(text_lower)
    if case_def:
        attrs.case_definition = case_def

    matching = _extract_matching_criteria(text_lower)
    if matching:
        attrs.matching_criteria = matching

    # ── Diagnostic accuracy ───────────────────────────────────────────────
    index_test = _extract_index_test(text_lower)
    if index_test:
        attrs.index_test = index_test

    ref_standard = _extract_reference_standard(text_lower)
    if ref_standard:
        attrs.reference_standard = ref_standard

    # ── Review / Synthesis ────────────────────────────────────────────────
    databases = _extract_databases(text_lower)
    if databases:
        attrs.databases = databases

    search_strategy = _extract_search_strategy(text_lower)
    if search_strategy:
        attrs.search_strategy = search_strategy

    # ── Qualitative ───────────────────────────────────────────────────────
    data_collection = _extract_data_collection_method(text_lower)
    if data_collection:
        attrs.data_collection_method = data_collection

    analysis_approach = _extract_analysis_approach(text_lower)
    if analysis_approach:
        attrs.analysis_approach = analysis_approach

    # Check for rare disease
    if detect_rare_disease(text):
        attrs.rare_disease_flag = True

    # Check for multi-center
    attrs.multi_center = _is_multicenter(text_lower)

    return attrs


def _extract_sample_size(text: str) -> Optional[int]:
    """Extract sample size from text."""
    for pattern in NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Find the number in the match
            for group in match.groups():
                if group and group.isdigit():
                    return int(group)
    return None


def _extract_population(text: str) -> Optional[str]:
    """Extract population description from text."""
    # Look for population markers
    population_patterns = [
        r"(benh nhan|patient|doi tuong|subject)\s*(la|la nhung|:)?\s*([^,.;]+)",
        r"(tre em|children|benh nhi)\s*([^,.;]+)",
        r"(nguoi lon|adult)\s*([^,.;]+)",
        r"(benh nhan|patient)\s*(bi|with|co|mac)\s*([^,.;]+)",
        r"(dan so|population)\s*(la|:)?\s*([^,.;]+)",
    ]

    for pattern in population_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the full match and clean it
            population = match.group(0).strip()
            if len(population) > 10:  # Meaningful content
                return population

    return None


def _extract_age_range(text: str) -> Optional[str]:
    """Extract age range from text."""
    # Explicit age range
    match = re.search(
        r"(\d+)\s*(-|den|to)\s*(\d+)\s*(tuoi|year|yo|y\.?o\.?)",
        text, re.IGNORECASE
    )
    if match:
        return f"{match.group(1)}-{match.group(3)} tuoi"

    # Age categories
    if re.search(r"(tre em|children|pediatric|nhi)", text, re.IGNORECASE):
        return "Nhi khoa"
    if re.search(r"(so sinh|newborn|neonatal)", text, re.IGNORECASE):
        return "So sinh"
    if re.search(r"(nguoi lon|adult)", text, re.IGNORECASE):
        return "Nguoi lon"
    if re.search(r"(nguoi gia|elderly|geriatric)", text, re.IGNORECASE):
        return "Nguoi cao tuoi"

    return None


def _extract_intervention(text: str) -> Optional[str]:
    """Extract intervention from text."""
    intervention_patterns = [
        r"(can thiep|intervention)\s*(la|:)?\s*([^,.;]+)",
        r"(dieu tri|treatment|therapy)\s*(bang|voi|by|with|:)?\s*([^,.;]+)",
        r"(su dung|using|use)\s*([^,.;]+)",
        r"(phau thuat|surgery|procedure)\s*([^,.;]+)",
        r"(thuoc|drug|medication)\s*([^,.;]+)",
        r"(noi soi|endoscop|laparoscop)\s*([^,.;]+)",
    ]

    for pattern in intervention_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get last group which should be the intervention
            groups = [g for g in match.groups() if g]
            if groups:
                intervention = groups[-1].strip()
                if len(intervention) > 3:
                    return intervention

    return None


def _extract_comparator(text: str) -> Optional[str]:
    """Extract comparator/control from text."""
    comparator_patterns = [
        r"(doi chung|control|comparator)\s*(la|:)?\s*([^,.;]+)",
        r"(so sanh voi|compared to|versus|vs\.?)\s*([^,.;]+)",
        r"(nhom|group)\s*(doi chung|control)\s*(la|:)?\s*([^,.;]+)",
        r"(placebo|giac duoc)",
        r"(dieu tri|treatment)\s*(chuan|standard|thong thuong|conventional)",
    ]

    for pattern in comparator_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = [g for g in match.groups() if g]
            if groups:
                comparator = groups[-1].strip()
                if len(comparator) > 2:
                    return comparator

    return None


def _extract_all_endpoints(text: str) -> dict:
    """Extract all endpoints from text."""
    result = {"primary": None, "secondary": []}

    # Primary endpoint patterns
    primary_patterns = [
        r"(ket qua|outcome|endpoint)\s*(chinh|primary)\s*(la|:)?\s*([^,.;]+)",
        r"(primary|chinh)\s*(outcome|endpoint|ket qua)\s*(la|:)?\s*([^,.;]+)",
        r"(muc tieu|objective)\s*(chinh|primary)\s*(la|:)?\s*([^,.;]+)",
        r"(do|measure|danh gia)\s*([^,.;]+)\s*(la ket qua chinh)",
    ]

    for pattern in primary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = [g for g in match.groups() if g and len(g) > 3]
            if groups:
                result["primary"] = groups[-1].strip()
                break

    # If no explicit primary, look for outcome mentions
    if not result["primary"]:
        outcome_patterns = [
            r"(ty le|rate)\s*([^,.;]+)",
            r"(thoi gian|time|duration)\s*([^,.;]+)",
            r"(so|number)\s*([^,.;]+)",
            r"(diem|score)\s*([^,.;]+)",
        ]

        for pattern in outcome_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["primary"] = match.group(0).strip()
                break

    # Secondary endpoint patterns
    secondary_patterns = [
        r"(ket qua|outcome|endpoint)\s*(phu|secondary)\s*(la|:)?\s*([^,.;]+)",
        r"(secondary|phu)\s*(outcome|endpoint|ket qua)\s*(la|:)?\s*([^,.;]+)",
    ]

    for pattern in secondary_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = [g for g in match if g and len(g) > 3]
            if groups:
                result["secondary"].append(groups[-1].strip())

    return result


def _extract_setting(text: str) -> Optional[str]:
    """Extract study setting from text."""
    for pattern in SETTING_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _extract_duration(text: str) -> Optional[str]:
    """Extract study duration from text."""
    for pattern in DURATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _is_multicenter(text: str) -> bool:
    """Check if study is multi-center."""
    multicenter_patterns = [
        r"(multi-?center|da trung tam|nhieu trung tam|multiple (site|center|hospital))",
        r"(\d+)\s*(benh vien|hospital|trung tam|center)",
    ]

    for pattern in multicenter_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# New Extractors for Extended Fields
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_randomization_method(text: str) -> Optional[str]:
    """Extract randomization method (RCT)."""
    patterns = [
        r"(block[- ]randomi[sz]|phan lo|randomization block)[^,.;]{0,50}",
        r"(stratified[- ]randomi[sz]|phan tang)[^,.;]{0,50}",
        r"(simple[- ]randomi[sz]|ngau nhien don gian)[^,.;]{0,30}",
        r"(permuted block|cluster randomi[sz]|randomi[sz]ation)[^,.;]{0,30}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_blinding(text: str) -> Optional[str]:
    """Extract blinding method (RCT)."""
    patterns = [
        r"double[- ]blind", r"single[- ]blind", r"open[- ]label", r"unblinded",
        r"lam mu doi", r"lam mu don", r"mo nhan", r"triple[- ]blind",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _extract_allocation_concealment(text: str) -> Optional[str]:
    """Extract allocation concealment method."""
    patterns = [
        r"(allocation concealment|che giau phan lo|phong bi|sealed envelope)[^,.;]{0,50}",
        r"(central randomi[sz]ation|phan bo trung tam)[^,.;]{0,30}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_follow_up_duration(text: str) -> Optional[str]:
    """Extract follow-up duration for cohort/longitudinal studies."""
    patterns = [
        r"(follow[- ]up|theo doi)\s*(la|:)?\s*[^,.;]{0,30}(thang|month|nam|year|tuan|week|ngay|day)",
        r"(thoi gian theo doi|duration of follow[- ]up)[^,.;]{0,40}",
        r"(\d+)\s*(thang|month|nam|year)\s*(theo doi|follow[- ]up)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_data_source(text: str) -> Optional[str]:
    """Extract data source for retrospective studies."""
    patterns = [
        r"(ho so benh an|medical record|benh an dien tu|electronic health record|EHR)[^,.;]{0,30}",
        r"(registry|co so du lieu|database|so lieu quoc gia)[^,.;]{0,30}",
        r"(retrospective review|ho so|chart review)[^,.;]{0,30}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_case_definition(text: str) -> Optional[str]:
    """Extract case definition for case-control / case series."""
    patterns = [
        r"(dinh nghia ca benh|case definition|tieu chuan ca|nhom benh la)[^,.;]{0,60}",
        r"(ca benh duoc dinh nghia|cases were defined)[^,.;]{0,60}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:120]
    return None


def _extract_matching_criteria(text: str) -> Optional[str]:
    """Extract matching criteria for case-control studies."""
    patterns = [
        r"(ghep cap|matched?|matching)[^,.;]{0,60}",
        r"(tieu chi ghep|match theo|paired by)[^,.;]{0,60}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_index_test(text: str) -> Optional[str]:
    """Extract index test for diagnostic accuracy studies."""
    patterns = [
        r"(index test|test duoc danh gia|xet nghiem can danh gia)[^,.;]{0,60}",
        r"(do chinh xac cua|accuracy of)\s+([^,.;]{3,60})",
        r"(sieu am|CT scan|MRI|PCR|ELISA|rapid test)[^,.;]{0,40}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_reference_standard(text: str) -> Optional[str]:
    """Extract reference standard (gold standard) for diagnostic studies."""
    patterns = [
        r"(tieu chuan vang|gold standard|reference standard|tieu chuan tham chieu)[^,.;]{0,60}",
        r"(sinh thiet|biopsy|culture|nuoi cay vi khuan)[^,.;]{0,30}",
        r"(compared to|so voi)\s+(sinh thiet|biopsy|gold standard)[^,.;]{0,40}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_databases(text: str) -> Optional[list[str]]:
    """Extract literature databases for review studies."""
    db_keywords = [
        "pubmed", "medline", "embase", "cochrane", "scopus",
        "cinahl", "web of science", "psycinfo", "lilacs",
        "vietton", "co so du lieu",
    ]
    found = [db for db in db_keywords if db in text.lower()]
    return found if found else None


def _extract_search_strategy(text: str) -> Optional[str]:
    """Extract search strategy for systematic reviews."""
    patterns = [
        r"(chien luoc tim kiem|search strategy|tim kiem tren)[^,.;]{0,80}",
        r"(tu khoa|keywords?|MeSH terms?)[^,.;]{0,60}",
        r"(tim kiem trong|searched)\s+(pubmed|embase|cochrane|scopus)[^,.;]{0,40}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:120]
    return None


def _extract_data_collection_method(text: str) -> Optional[str]:
    """Extract data collection method for qualitative studies."""
    patterns = [
        r"(phong van|interview|focus group|nhom tap trung)[^,.;]{0,50}",
        r"(quan sat|observation|field note|ghi chu thuc dia)[^,.;]{0,50}",
        r"(thu thap du lieu bang|data collected via|data collection)[^,.;]{0,50}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def _extract_analysis_approach(text: str) -> Optional[str]:
    """Extract analysis approach for qualitative/mixed studies."""
    patterns = [
        r"(thematic analysis|phan tich chu de|grounded theory|phenomenology)[^,.;]{0,50}",
        r"(phuong phap phan tich|analysis approach|phan tich noi dung)[^,.;]{0,50}",
        r"(content analysis|narrative analysis)[^,.;]{0,30}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return None


def merge_attributes(
    base: ExtractedAttributes,
    new: ExtractedAttributes
) -> ExtractedAttributes:
    """
    Merge new attributes into base, keeping existing values if new is None.

    Args:
        base: Base attributes
        new: New attributes to merge

    Returns:
        Merged ExtractedAttributes
    """
    merged = base.model_copy()
    new_dict = new.model_dump()

    for key, value in new_dict.items():
        if value is not None:
            # For lists, extend rather than replace
            if isinstance(value, list) and value:
                existing = getattr(merged, key, None)
                if existing:
                    # Combine and deduplicate
                    combined = list(set(existing + value))
                    setattr(merged, key, combined)
                else:
                    setattr(merged, key, value)
            else:
                setattr(merged, key, value)

    return merged


def attributes_to_dict(attrs: ExtractedAttributes) -> dict:
    """Convert attributes to a clean dictionary for display."""
    result = {}
    attr_dict = attrs.model_dump()

    display_names = {
        "population": "Dan so nghien cuu",
        "sample_size": "Co mau",
        "age_range": "Do tuoi",
        "inclusion_criteria": "Tieu chi chon",
        "exclusion_criteria": "Tieu chi loai",
        "intervention": "Can thiep",
        "comparator": "Doi chung",
        "exposure": "Yeu to phoi nhiem",
        "primary_endpoint": "Ket qua chinh",
        "secondary_endpoints": "Ket qua phu",
        "design_type": "Thiet ke",
        "setting": "Dia diem",
        "duration": "Thoi gian",
        "specialty": "Chuyen khoa",
    }

    for key, display in display_names.items():
        value = attr_dict.get(key)
        if value:
            if isinstance(value, DesignType):
                value = value.value
            elif isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            result[display] = value

    return result
