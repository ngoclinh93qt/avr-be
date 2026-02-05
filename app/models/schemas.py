from typing import Optional

from pydantic import BaseModel, Field


# === Topic Analyzer Full Pipeline ===
class TopicAnalyzeFullRequest(BaseModel):
    abstract: str = Field(..., min_length=10, max_length=5000)
    language: Optional[str] = "auto"
    user_responses: Optional[dict] = None
    skip_clarification: bool = False


class NoveltyDetail(BaseModel):
    score: Optional[int] = None
    reasoning: Optional[str] = None
    most_similar_paper: Optional[str] = None
    differentiation: Optional[str] = None


class GapDetail(BaseModel):
    type: str
    description: str
    how_filled: Optional[str] = None
    strength: Optional[str] = None


class SwotPoint(BaseModel):
    point: str
    reviewer_appeal: Optional[str] = None
    mitigation: Optional[str] = None
    action: Optional[str] = None
    risk_level: Optional[str] = None


class SwotDetail(BaseModel):
    strengths: list[SwotPoint] = []
    weaknesses: list[SwotPoint] = []
    opportunities: list[SwotPoint] = []
    threats: list[SwotPoint] = []


class PublishabilityDetail(BaseModel):
    level: Optional[str] = None
    target_tier: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    success_factors: list[str] = []
    risk_factors: list[str] = []


class SuggestionDetail(BaseModel):
    action: str
    impact: Optional[str] = None
    effort: Optional[str] = None
    priority: Optional[int] = None


class AnalysisMetadata(BaseModel):
    processing_time_seconds: float
    similar_papers_count: int
    completeness_score: Optional[int] = None
    clarification_applied: bool = False


class ClarificationQuestion(BaseModel):
    question: str
    element: str
    priority: int


class ClarificationQuestions(BaseModel):
    intro_message: str
    questions: list[ClarificationQuestion]
    skip_message: str


class ResearchPaper(BaseModel):
    title: str
    authors: list[str]
    year: int
    similarity: float
    pmid: str
    url: Optional[str] = None
    abstract: Optional[str] = None


class ResearchDetail(BaseModel):
    total_found: int
    total_ranked: int
    avg_similarity: float
    top_papers: list[ResearchPaper]


class TopicAnalyzeFullResponse(BaseModel):
    status: str  # "complete" or "needs_clarification"
    research: Optional[ResearchDetail] = None
    novelty: Optional[NoveltyDetail] = None
    gaps: list[GapDetail] = []
    swot: Optional[SwotDetail] = None
    publishability: Optional[PublishabilityDetail] = None
    suggestions: list[SuggestionDetail] = []
    quick_wins: list[str] = []
    long_term: list[str] = []
    metadata: Optional[AnalysisMetadata] = None
    # For needs_clarification status
    assessment: Optional[dict] = None
    questions: Optional[ClarificationQuestions] = None




# === Journal Matcher ===
class JournalMatchRequest(BaseModel):
    abstract: str
    max_apc: Optional[int] = 500
    min_if: Optional[float] = 0.5
    max_if: Optional[float] = 5.0
    open_access_only: bool = False
    specialty: Optional[str] = None


class JournalResult(BaseModel):
    name: str
    match_score: int
    impact_factor: float
    apc: int
    review_weeks: str
    acceptance_rate: Optional[float]
    reasoning: str
    is_predatory: bool = False


class JournalMatchResponse(BaseModel):
    journals: list[JournalResult]


# === Manuscript Strategist ===
class ManuscriptRequest(BaseModel):
    abstract: str
    target_journal: str
    full_text: Optional[str] = None


class VietglishError(BaseModel):
    original: str
    suggestion: str
    explanation: str
    category: str


class SectionRoadmap(BaseModel):
    section: str
    word_count: str
    key_points: list[str]
    citations_needed: int
    tips: list[str]


class ManuscriptResponse(BaseModel):
    vietglish_errors: list[VietglishError]
    roadmap: list[SectionRoadmap]
