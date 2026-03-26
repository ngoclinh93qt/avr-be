"""Pydantic models for AVR Research Formation System."""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from .enums import (
    Phase, SessionStatus, ConversationState, GateResult,
    ViolationSeverity, DesignType, EndpointType
)


# ═══════════════════════════════════════════════════════════════════════════════
# Blueprint & Extracted Attributes
# ═══════════════════════════════════════════════════════════════════════════════

class ExtractedAttributes(BaseModel):
    """Attributes extracted from user input during conversation."""
    # Population
    population: Optional[str] = None
    sample_size: Optional[int] = None
    age_range: Optional[str] = None
    inclusion_criteria: Optional[list[str]] = None
    exclusion_criteria: Optional[list[str]] = None

    # Intervention/Exposure
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    exposure: Optional[str] = None

    # Outcome
    primary_endpoint: Optional[str] = None
    secondary_endpoints: Optional[list[str]] = None
    endpoint_measurable: Optional[bool] = None

    # Design
    design_type: Optional[DesignType] = None
    design_structural: Optional[dict] = None  # arms, blinding, etc.

    # RCT / Interventional
    randomization_method: Optional[str] = None   # block, stratified, simple
    blinding: Optional[str] = None               # open-label, single-blind, double-blind
    allocation_concealment: Optional[str] = None  # sealed envelopes, etc.
    timepoints: Optional[list[str]] = None        # BEFORE_AFTER measurement points

    # Cohort / Longitudinal
    follow_up_duration: Optional[str] = None      # 6 months, 2 years, etc.
    data_source: Optional[str] = None             # medical records, registry, etc.

    # Case studies
    case_definition: Optional[str] = None         # criteria defining a case
    control_definition: Optional[str] = None      # criteria defining controls
    matching_criteria: Optional[str] = None       # age, sex, comorbidities…
    case_presentation: Optional[str] = None       # narrative of the case
    key_findings: Optional[str] = None            # main findings / outcomes

    # Diagnostic accuracy
    index_test: Optional[str] = None              # the test being evaluated
    reference_standard: Optional[str] = None      # gold standard comparator
    spectrum_of_disease: Optional[str] = None     # disease severity range

    # Prognostic
    prognostic_factors: Optional[list[str]] = None
    outcome: Optional[str] = None                 # prognostic outcome endpoint

    # Review / Synthesis
    search_strategy: Optional[str] = None          # search terms used
    databases: Optional[list[str]] = None          # PubMed, Embase, Cochrane…
    quality_assessment: Optional[str] = None       # tool used (Cochrane RoB, NOS)
    statistical_method: Optional[str] = None       # pooling method
    heterogeneity_assessment: Optional[str] = None  # I², Q-test
    charting_form: Optional[str] = None            # data extraction template

    # Qualitative / Mixed
    data_collection_method: Optional[str] = None   # interviews, focus groups…
    analysis_approach: Optional[str] = None        # thematic analysis, grounded…
    saturation_strategy: Optional[str] = None      # how saturation is determined
    quantitative_component: Optional[str] = None
    qualitative_component: Optional[str] = None
    integration_approach: Optional[str] = None     # how components are merged

    # Context
    setting: Optional[str] = None
    duration: Optional[str] = None
    specialty: Optional[str] = None

    # Feasibility flags
    rare_disease_flag: Optional[bool] = None
    rare_disease_confirmed: Optional[bool] = None
    multi_center: Optional[bool] = None



class ResearchBlueprint(BaseModel):
    """Structured research blueprint built from extracted attributes."""
    # Core PICO(T)
    population: str
    intervention_or_exposure: str
    comparator: Optional[str] = None
    primary_outcome: str
    secondary_outcomes: list[str] = []
    timeframe: Optional[str] = None

    # Design
    design_type: DesignType
    design_details: dict = {}  # arms, blinding, allocation, etc.

    # Sample
    sample_size: int
    sample_justification: Optional[str] = None

    # Methods
    statistical_approach: Optional[str] = None
    primary_analysis: Optional[str] = None

    # Metadata
    specialty: Optional[str] = None
    setting: Optional[str] = None

    # Completeness tracking
    missing_elements: list[str] = []
    warnings: list[str] = []


# ═══════════════════════════════════════════════════════════════════════════════
# Violations
# ═══════════════════════════════════════════════════════════════════════════════

class Violation(BaseModel):
    """A single constraint violation."""
    code: str  # e.g., "D-01", "S-03", "A-02"
    tier: int = Field(ge=0, le=4)
    severity: ViolationSeverity
    message_vi: str  # Vietnamese message for user
    path_vi: str     # Vietnamese guidance for fixing
    context: dict = {}  # Additional context


class ViolationList(BaseModel):
    """Collection of violations from gate check."""
    violations: list[Violation] = []
    has_block: bool = False
    has_major: bool = False
    total_deduction: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Session & Conversation
# ═══════════════════════════════════════════════════════════════════════════════

class SessionStartRequest(BaseModel):
    """Request to start a new research session."""
    phase: Phase = Phase.PHASE1


class SessionStartResponse(BaseModel):
    """Response after starting a session."""
    session_id: str
    phase: Phase
    status: SessionStatus
    conversation_state: ConversationState
    welcome_message: str


class ChatMessageRequest(BaseModel):
    """User message in conversation."""
    session_id: str
    message: str = Field(min_length=1, max_length=10000)


class ChatMessageResponse(BaseModel):
    """Assistant response in conversation."""
    session_id: str
    assistant_message: str
    conversation_state: ConversationState
    extracted_attributes: Optional[ExtractedAttributes] = None
    blueprint: Optional[ResearchBlueprint] = None
    next_action: Optional[str] = None  # "continue", "generate_abstract", "blocked"
    missing_elements: list[str] = []


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    id: int
    role: str
    content: str
    extracted_attributes: Optional[dict] = None
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """Full session details."""
    id: str
    user_id: str
    phase: Phase
    status: SessionStatus
    conversation_state: ConversationState
    clarifying_turns_count: int
    extracted_attributes: Optional[ExtractedAttributes] = None
    blueprint: Optional[ResearchBlueprint] = None
    estimated_abstract: Optional[str] = None
    journal_suggestions: list[dict] = []
    gate_result: Optional[GateResult] = None
    integrity_score: Optional[float] = None
    violations: list[Violation] = []
    reviewer_simulation: Optional[str] = None
    manuscript_outline: Optional[str] = None
    gate_run_count: int = 0
    created_at: datetime
    updated_at: datetime


class SessionListItem(BaseModel):
    """Summary item for session list."""
    id: str
    phase: Phase
    status: SessionStatus
    conversation_state: ConversationState
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Abstract Generation (Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

class JournalSuggestion(BaseModel):
    """A suggested journal from ChromaDB search."""
    journal_id: str
    name: str
    issn: Optional[str] = None
    impact_factor: Optional[float] = None
    specialty: Optional[str] = None
    open_access: Optional[str] = None   # "Diamond OA" | "Hybrid OA" | "Subscription"
    abstract_limit: Optional[str] = None  # e.g. "≤ 250 từ"
    citation_style: Optional[str] = None  # e.g. "Vancouver"
    similarity_score: float
    reasoning: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Novelty Check
# ═══════════════════════════════════════════════════════════════════════════════

class NoveltyPaper(BaseModel):
    """A single paper found during novelty check."""
    title: str
    authors: str
    year: str
    journal: str
    pmid: Optional[str] = None


class NoveltyCheck(BaseModel):
    """Result of PubMed novelty scan."""
    count: int
    papers: list[NoveltyPaper] = []
    commentary: str          # LLM-generated short commentary in Vietnamese
    keywords_used: list[str] = []


# ═══════════════════════════════════════════════════════════════════════════════
# Research Roadmap
# ═══════════════════════════════════════════════════════════════════════════════

class RoadmapStep(BaseModel):
    """A single step in the research roadmap."""
    step_number: int
    title: str
    description: str
    who: str                 # "Bạn tự làm" | "AVR hỗ trợ"
    duration_estimate: str
    avr_tool: Optional[str] = None   # coming-soon tool label


class ResearchRoadmap(BaseModel):
    """Roadmap generated from blueprint — template-based, no LLM."""
    steps: list[RoadmapStep] = []
    checklist_type: str      # STROBE | CONSORT | STARD | PRISMA | CARE
    total_timeline_estimate: str
    design_type: str


class AbstractGenerateRequest(BaseModel):
    """Request to generate estimated abstract."""
    session_id: str


class AbstractGenerateResponse(BaseModel):
    """Response with generated abstract, novelty check, journal suggestions, and roadmap."""
    session_id: str
    estimated_abstract: str
    journal_suggestions: list[JournalSuggestion] = []
    blueprint: ResearchBlueprint
    status: SessionStatus
    novelty_check: Optional[NoveltyCheck] = None
    roadmap: Optional[ResearchRoadmap] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Gate (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════

class GateRunRequest(BaseModel):
    """Request to run submission gate."""
    session_id: str
    abstract: str = Field(min_length=50, max_length=5000)


class GateRunResponse(BaseModel):
    """Response from gate run."""
    session_id: str
    gate_result: GateResult
    integrity_score: float
    violations: list[Violation] = []
    reviewer_simulation: Optional[str] = None
    gate_run_count: int
    score_history: list[float] = []
    can_proceed_to_phase3: bool


class RevisionExplainRequest(BaseModel):
    """Request for guided revision explanation."""
    session_id: str
    section_text: Optional[str] = None


class RevisionExplainResponse(BaseModel):
    """Response with revision guidance."""
    code: str
    violation: Violation
    explanation: str
    example: Optional[str] = None
    suggested_rewrite: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Outline (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════

class OutlineGenerateRequest(BaseModel):
    """Request to generate manuscript outline."""
    session_id: str
    target_journal_id: str
    validated_abstract: str = Field(min_length=50, max_length=5000)


class JournalMetadata(BaseModel):
    """Metadata about target journal."""
    journal_id: str
    name: str
    issn: Optional[str] = None
    impact_factor: Optional[float] = None
    word_limits: Optional[dict] = None
    section_requirements: list[str] = []
    author_guidelines_url: Optional[str] = None


class OutlineSection(BaseModel):
    """A section in the manuscript outline."""
    section_name: str
    word_count_suggested: str
    key_points: list[str] = []
    subsections: list[str] = []
    tips: list[str] = []


class OutlineGenerateResponse(BaseModel):
    """Response with manuscript outline."""
    session_id: str
    target_journal: JournalMetadata
    outline: list[OutlineSection] = []
    total_word_count: str
    estimated_figures: int = 0
    estimated_tables: int = 0
    references_suggested: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# History
# ═══════════════════════════════════════════════════════════════════════════════

class ConversationHistoryResponse(BaseModel):
    """Full conversation history for a session."""
    session_id: str
    turns: list[ConversationTurn] = []
    total_turns: int


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Messages
# ═══════════════════════════════════════════════════════════════════════════════

class WSMessageBase(BaseModel):
    """Base WebSocket message."""
    type: str
    session_id: Optional[str] = None


class WSChatMessage(WSMessageBase):
    """Chat message via WebSocket."""
    type: str = "chat"
    message: str
    form_data: Optional[dict] = None


class WSStreamChunk(WSMessageBase):
    """Streaming response chunk."""
    type: str = "stream"
    content: str
    done: bool = False


class WSStateUpdate(WSMessageBase):
    """State update notification."""
    type: str = "state_update"
    conversation_state: ConversationState
    extracted_attributes: Optional[dict] = None
    blueprint: Optional[dict] = None


class WSError(WSMessageBase):
    """Error message."""
    type: str = "error"
    error: str
    recoverable: bool = True
