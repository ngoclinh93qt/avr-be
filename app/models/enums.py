"""Enums for AVR Research Formation System."""

from enum import Enum


class Phase(str, Enum):
    """Research workflow phases."""
    PHASE1 = "phase1"  # Conversational Idea Engine (Free)
    PHASE2 = "phase2"  # Submission Gate (Paid)
    PHASE3 = "phase3"  # Manuscript Outline (Paid)


class SessionStatus(str, Enum):
    """Research session status."""
    ACTIVE = "active"
    GENERATING = "generating"
    ABSTRACT_READY = "abstract_ready"
    GATE_RUN = "gate_run"
    OUTLINE_READY = "outline_ready"
    ABANDONED = "abandoned"


class ConversationState(str, Enum):
    """Conversation state machine states."""
    INITIAL = "INITIAL"        # No attributes extracted yet
    CLARIFYING = "CLARIFYING"  # Some attributes, needs more
    BLOCKED = "BLOCKED"        # Critical issues detected
    COMPLETE = "COMPLETE"      # All required attributes collected


class GateResult(str, Enum):
    """Gate decision outcomes."""
    PASS = "PASS"      # IS >= 80, no BLOCK violations
    REVISE = "REVISE"  # 50 <= IS < 80, or has MAJOR violations
    REJECT = "REJECT"  # IS < 50, or has BLOCK violations


class ViolationSeverity(str, Enum):
    """Violation severity levels."""
    BLOCK = "BLOCK"  # Fatal, cannot proceed
    MAJOR = "MAJOR"  # Significant issue, caps IS at 10
    WARN = "WARN"    # Minor issue, deduction


class ViolationTier(int, Enum):
    """Constraint tiers (0-4)."""
    TIER0 = 0  # Data integrity
    TIER1 = 1  # Structural completeness
    TIER2 = 2  # Attribute consistency
    TIER3 = 3  # Scope validity
    TIER4 = 4  # Statistical completeness


class DesignType(str, Enum):
    """Research design types."""
    # Observational
    CROSS_SECTIONAL = "cross_sectional"
    CASE_CONTROL = "case_control"
    COHORT_RETROSPECTIVE = "cohort_retrospective"
    COHORT_PROSPECTIVE = "cohort_prospective"
    CASE_SERIES = "case_series"
    CASE_REPORT = "case_report"

    # Interventional
    RCT = "rct"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    BEFORE_AFTER = "before_after"

    # Synthesis
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    SCOPING_REVIEW = "scoping_review"

    # Other
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    DIAGNOSTIC_ACCURACY = "diagnostic_accuracy"
    PROGNOSTIC = "prognostic"
    UNKNOWN = "unknown"


class EndpointType(str, Enum):
    """Endpoint types for research."""
    PRIMARY = "primary"
    SECONDARY = "secondary"


class Specialty(str, Enum):
    """Medical specialties."""
    PEDIATRICS = "pediatrics"
    SURGERY = "surgery"
    INTERNAL_MEDICINE = "internal_medicine"
    CARDIOLOGY = "cardiology"
    ONCOLOGY = "oncology"
    NEUROLOGY = "neurology"
    ORTHOPEDICS = "orthopedics"
    RADIOLOGY = "radiology"
    PATHOLOGY = "pathology"
    ANESTHESIOLOGY = "anesthesiology"
    EMERGENCY = "emergency"
    INFECTIOUS_DISEASE = "infectious_disease"
    GASTROENTEROLOGY = "gastroenterology"
    PULMONOLOGY = "pulmonology"
    NEPHROLOGY = "nephrology"
    ENDOCRINOLOGY = "endocrinology"
    RHEUMATOLOGY = "rheumatology"
    DERMATOLOGY = "dermatology"
    OPHTHALMOLOGY = "ophthalmology"
    ENT = "ent"
    UROLOGY = "urology"
    OBSTETRICS_GYNECOLOGY = "obstetrics_gynecology"
    PSYCHIATRY = "psychiatry"
    OTHER = "other"


class UserTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PAID = "paid"


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
