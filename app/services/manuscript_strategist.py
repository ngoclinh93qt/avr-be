from app.models.schemas import (
    ManuscriptResponse,
    SectionRoadmap,
    VietglishError,
)


class ManuscriptStrategistService:
    """Service for manuscript writing strategy and Vietglish corrections"""

    async def strategize(
        self,
        abstract: str,
        target_journal: str,
        full_text: str | None = None,
    ) -> ManuscriptResponse:
        """
        Generate manuscript writing strategy and detect Vietglish errors.

        Args:
            abstract: The research abstract
            target_journal: Target journal for submission
            full_text: Optional full manuscript text

        Returns:
            ManuscriptResponse with Vietglish errors and section roadmap
        """
        # TODO: Implement with LLM and Vietglish patterns
        # 1. Analyze text for Vietglish patterns
        # 2. Generate section-by-section roadmap
        # 3. Provide journal-specific tips

        return ManuscriptResponse(
            vietglish_errors=[
                VietglishError(
                    original="According to literature showed that",
                    suggestion="The literature shows that",
                    explanation="Incorrect verb tense and redundant phrasing",
                    category="grammar",
                )
            ],
            roadmap=[
                SectionRoadmap(
                    section="Introduction",
                    word_count="400-600",
                    key_points=[
                        "Background context",
                        "Research gap",
                        "Objectives",
                    ],
                    citations_needed=15,
                    tips=["Start broad, narrow to specific gap"],
                )
            ],
        )
