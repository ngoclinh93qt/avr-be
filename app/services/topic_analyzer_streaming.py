"""
Streaming Topic Analyzer Service for WebSocket communication.

Provides realtime updates during analysis via callback functions.
"""

import asyncio
import time
from typing import Callable, Optional

from app.agents.research.agent import ResearchAgent
from app.skills.input_clarifier.functions import (
    assess_completeness,
    generate_questions,
    smart_inference,
)
from app.skills.topic_analyzer.functions import (
    analyze_gaps,
    perform_swot,
    predict_publishability,
    score_novelty,
    suggest_improvements,
)


class TopicAnalyzerStreamingService:
    """
    Streaming version of TopicAnalyzerService.

    Uses callbacks to send realtime updates during processing.
    """

    def __init__(self):
        """Initialize the service with research agent."""
        self.research_agent = ResearchAgent()

    async def assess_input(
        self,
        abstract: str,
        on_thinking: Optional[Callable[[str, str, int], None]] = None,
    ) -> dict:
        """
        Assess input completeness.

        Args:
            abstract: Research abstract
            on_thinking: Callback(message, step, progress)

        Returns:
            Assessment result with completeness score
        """
        if on_thinking:
            await on_thinking("Assessing abstract completeness...", "assessing", 10)

        assessment = await assess_completeness(abstract)

        if on_thinking:
            score = assessment.get("completeness_score", 0)
            await on_thinking(
                f"Completeness assessed: {score}% complete", "assessing", 20
            )

        return assessment

    async def get_clarification_questions(
        self,
        abstract: str,
        assessment: dict,
        on_thinking: Optional[Callable[[str, str, int], None]] = None,
    ) -> dict:
        """
        Generate clarification questions for incomplete input.

        Args:
            abstract: Research abstract
            assessment: Completeness assessment
            on_thinking: Callback(message, step, progress)

        Returns:
            Questions structure
        """
        if on_thinking:
            await on_thinking(
                "Generating clarification questions...", "generating", 30
            )

        questions = await generate_questions(abstract, assessment)

        if on_thinking:
            num_questions = len(questions.get("questions", []))
            await on_thinking(
                f"Generated {num_questions} clarification questions", "generating", 40
            )

        return questions

    async def enrich_abstract(
        self,
        abstract: str,
        user_answers: dict[str, str],
        missing_elements: list[str],
        on_thinking: Optional[Callable[[str, str, int], None]] = None,
    ) -> str:
        """
        Enrich abstract with user answers and smart inference.

        Args:
            abstract: Original abstract
            user_answers: User's answers to clarification questions
            missing_elements: Still-missing critical elements
            on_thinking: Callback(message, step, progress)

        Returns:
            Enriched abstract
        """
        if on_thinking:
            await on_thinking(
                "Enriching abstract with your answers...", "enriching", 20
            )

        # Combine user answers with abstract
        enriched = f"{abstract}\n\n## Additional Context:\n"
        for question_id, answer in user_answers.items():
            enriched += f"- {answer}\n"

        # Smart inference for remaining gaps
        if missing_elements:
            if on_thinking:
                await on_thinking(
                    "Inferring missing details from context...", "enriching", 30
                )

            inference = await smart_inference(enriched, missing_elements)
            enriched = inference.get("enriched_abstract", enriched)

        if on_thinking:
            await on_thinking("Abstract enriched successfully", "enriching", 40)

        return enriched

    async def analyze_full(
        self,
        abstract: str,
        on_progress: Optional[Callable[[str, str, int, Optional[dict]], None]] = None,
    ) -> dict:
        """
        Full analysis pipeline with realtime progress updates.

        Args:
            abstract: Research abstract (enriched)
            on_progress: Callback(step, message, progress, partial_result)

        Returns:
            Complete analysis results
        """
        start_time = time.time()
        results = {}

        # ────────────────────────────────────────────────────────────
        # Step 1: Deep Research (NEW!)
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress("research", "Searching PubMed for related papers...", 45, None)

        research_result = await self.research_agent.search(
            abstract=abstract,
            max_papers=20,
            title_search_limit=500,
            on_progress=lambda msg, pct: on_progress(
                "research", msg, 45 + int(pct * 0.1), None
            ) if on_progress else None,
        )

        research_papers = research_result.papers
        results["research"] = {
            "total_found": research_result.total_found,
            "total_ranked": research_result.total_ranked,
            "avg_similarity": research_result.avg_similarity,
            "papers": [p.to_dict() for p in research_papers[:5]],  # Top 5 for display
        }

        if on_progress:
            await on_progress(
                "research",
                f"Found {len(research_papers)} relevant papers (avg similarity: {research_result.avg_similarity:.2f})",
                55,
                {"papers_count": len(research_papers)},
            )

        # ────────────────────────────────────────────────────────────
        # Step 2: Novelty Scoring (with real papers)
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress("novelty", "Analyzing novelty with research papers...", 60, None)

        novelty_result = await score_novelty(abstract)
        results["novelty"] = novelty_result

        # Enhance with real papers
        if research_papers:
            novelty_result["most_similar_papers"] = [
                {
                    "title": p.title,
                    "authors": p.authors[:2],
                    "year": p.year,
                    "similarity": p.similarity,
                    "pmid": p.pmid,
                }
                for p in research_papers[:3]
            ]

        if on_progress:
            await on_progress(
                "novelty",
                f"Novelty score: {novelty_result.get('novelty_score', 0)}/100",
                65,
                {
                    "novelty_score": novelty_result.get("novelty_score"),
                    "most_similar_paper": research_papers[0].title if research_papers else None,
                },
            )

        # ────────────────────────────────────────────────────────────
        # Step 3: Gap Analysis (with real papers)
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress("gaps", "Identifying research gaps...", 70, None)

        gaps_result = await analyze_gaps(abstract)
        results["gaps"] = gaps_result

        # Enhance with evidence from real papers
        if research_papers:
            gaps_result["evidence_from_literature"] = [
                f"{p.authors[0] if p.authors else 'Unknown'} et al. ({p.year}): {p.title[:80]}..."
                for p in research_papers[:5]
            ]

        if on_progress:
            num_gaps = len(gaps_result.get("gaps", []))
            await on_progress(
                "gaps",
                f"Identified {num_gaps} research gaps",
                75,
                {"gap_count": num_gaps},
            )

        # ────────────────────────────────────────────────────────────
        # Step 4: SWOT Analysis (with research context)
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress("swot", "Performing SWOT analysis...", 80, None)

        swot_result = await perform_swot(
            abstract=abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            num_similar=len(research_papers),  # Use real paper count
            target_tier="Q2",
        )
        results["swot"] = swot_result

        if on_progress:
            await on_progress("swot", "SWOT analysis complete", 85, None)

        # ────────────────────────────────────────────────────────────
        # Step 5: Publishability Prediction
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress(
                "publishability", "Predicting publishability...", 90, None
            )

        publishability_result = await predict_publishability(
            abstract=abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            gaps=gaps_result.get("gaps", []),
            strengths=swot_result.get("strengths", []),
            weaknesses=swot_result.get("weaknesses", []),
        )
        results["publishability"] = publishability_result

        if on_progress:
            level = publishability_result.get("publishability", "MEDIUM")
            tier = publishability_result.get("target_tier", "Q2")
            await on_progress(
                "publishability",
                f"Publishability: {level} ({tier})",
                90,
                {"level": level, "tier": tier},
            )

        # ────────────────────────────────────────────────────────────
        # Step 6: Improvement Suggestions
        # ────────────────────────────────────────────────────────────
        if on_progress:
            await on_progress(
                "suggestions", "Generating improvement suggestions...", 95, None
            )

        suggestions_result = await suggest_improvements(
            abstract=abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            weaknesses=swot_result.get("weaknesses", []),
            target_tier=publishability_result.get("target_tier", "Q2"),
        )
        results["suggestions"] = suggestions_result

        if on_progress:
            num_suggestions = len(suggestions_result.get("suggestions", []))
            await on_progress(
                "suggestions",
                f"Generated {num_suggestions} improvement suggestions",
                100,
                None,
            )

        # ────────────────────────────────────────────────────────────
        # Aggregate Final Results
        # ────────────────────────────────────────────────────────────
        processing_time = time.time() - start_time

        return {
            "status": "complete",
            "research": {
                "total_found": research_result.total_found,
                "total_ranked": research_result.total_ranked,
                "avg_similarity": round(research_result.avg_similarity, 3),
                "top_papers": [p.to_dict() for p in research_papers[:5]],
            },
            "novelty": {
                "score": novelty_result.get("novelty_score"),
                "reasoning": novelty_result.get("reasoning"),
                "most_similar_paper": novelty_result.get("most_similar_paper"),
                "most_similar_papers": novelty_result.get("most_similar_papers", []),
                "differentiation": novelty_result.get("differentiation"),
            },
            "gaps": gaps_result.get("gaps", []),
            "swot": {
                "strengths": swot_result.get("strengths", []),
                "weaknesses": swot_result.get("weaknesses", []),
                "opportunities": swot_result.get("opportunities", []),
                "threats": swot_result.get("threats", []),
            },
            "publishability": {
                "level": publishability_result.get("publishability"),
                "target_tier": publishability_result.get("target_tier"),
                "confidence": publishability_result.get("confidence"),
                "reasoning": publishability_result.get("reasoning"),
                "success_factors": publishability_result.get("success_factors", []),
                "risk_factors": publishability_result.get("risk_factors", []),
            },
            "suggestions": suggestions_result.get("suggestions", []),
            "quick_wins": suggestions_result.get("quick_wins", []),
            "long_term": suggestions_result.get("long_term", []),
            "metadata": {
                "processing_time_seconds": round(processing_time, 2),
                "similar_papers_count": len(research_papers),
                "real_papers_analyzed": True,
            },
        }
