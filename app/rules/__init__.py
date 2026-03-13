"""Rule-based constraint layer for AVR Research Formation System.

This module implements the deterministic rule layer that runs BEFORE any LLM calls.
Rules are organized by tier (0-4) with increasing specificity.

Rule Philosophy (R-01 to R-12):
- R-01: Rule layer runs BEFORE LLM
- R-02: LLM cannot decide state
- R-03: Gate decision 100% deterministic
- R-04: No fake data
- R-05: Results = [PLACEHOLDER]
- R-06: Every issue has path
- R-07: Reviewer sim doesn't see abstract
- R-08: Journal search via ChromaDB
- R-09: IS bonus capped at 10 with MAJOR
- R-10: Rare disease override needs confirm
- R-11: Re-run full check each submission
- R-12: Outline only after Gate pass
"""

from .design_rules import (
    DESIGN_RULES,
    infer_design_type,
    infer_design_structural,
    get_required_elements,
)

from .endpoint_rules import (
    MEASURABLE_ENDPOINT_SIGNALS,
    VAGUE_ENDPOINT_PATTERNS,
    is_endpoint_measurable,
    extract_endpoints,
)

from .feasibility_rules import (
    BLOCK_RULES,
    WARN_RULES,
    check_feasibility,
)

from .constraint_tier0 import check_tier0_violations
from .constraint_tier1 import check_tier1_violations
from .constraint_tier2 import check_tier2_violations
from .constraint_tier3 import check_tier3_violations
from .constraint_tier4 import check_tier4_violations


__all__ = [
    # Design rules
    "DESIGN_RULES",
    "infer_design_type",
    "infer_design_structural",
    "get_required_elements",
    # Endpoint rules
    "MEASURABLE_ENDPOINT_SIGNALS",
    "VAGUE_ENDPOINT_PATTERNS",
    "is_endpoint_measurable",
    "extract_endpoints",
    # Feasibility rules
    "BLOCK_RULES",
    "WARN_RULES",
    "check_feasibility",
    # Constraint tiers
    "check_tier0_violations",
    "check_tier1_violations",
    "check_tier2_violations",
    "check_tier3_violations",
    "check_tier4_violations",
]
