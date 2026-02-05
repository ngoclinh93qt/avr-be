import asyncio
import time


from app.skills.input_clarifier.functions import (
    assess_completeness,
    generate_questions,
    smart_inference,
)
from app.skills.topic_analyzer.functions import (
    score_novelty,
    analyze_gaps,
    perform_swot,
    predict_publishability,
    suggest_improvements,
)


class TopicAnalyzerService:
    """
    Service for analyzing research topics for novelty and publishability.
    
    Pipeline:
    1. INPUT CLARIFICATION: Assess completeness, generate questions if needed, infer missing details.
    2. PARALLEL ANALYSIS: Run novelty scoring, gap analysis, and SWOT analysis in parallel.
    3. SEQUENTIAL ANALYSIS: Predict publishability, then suggest improvements.
    4. RESPONSE AGGREGATION: Combine all results into a final structured response.
    """

    async def analyze(
        self,
        abstract: str,
        language: str | None = "auto",
        user_responses: dict | None = None,
        skip_clarification: bool = False,
    ) -> dict:
        """
        Analyze a research abstract for novelty and publishability.

        Args:
            abstract: The research abstract to analyze.
            language: Language of the abstract (auto, vi, en).
            user_responses: Optional user responses to clarifying questions.
            skip_clarification: If True, skip clarification and infer missing details.

        Returns:
            Full analysis result including novelty, gaps, SWOT, publishability, and suggestions.
        """
        start_time = time.time()
        
        # ─────────────────────────────────────────────────────────────
        # Step 1: INPUT CLARIFICATION
        # ─────────────────────────────────────────────────────────────
        enriched_abstract = abstract
        clarification_result = None
        
        assessment = await assess_completeness(abstract)
        
        if assessment.get("completeness_score", 0) < 60 and not skip_clarification:
            if user_responses is None:
                # Need to return questions to user
                questions_result = await generate_questions(abstract, assessment)
                return {
                    "status": "needs_clarification",
                    "assessment": assessment,
                    "questions": questions_result,
                }
            else:
                # User provided responses, infer remaining gaps
                inference_result = await smart_inference(
                    abstract, assessment.get("missing_critical", [])
                )
                enriched_abstract = inference_result.get("enriched_abstract", abstract)
                clarification_result = inference_result
        elif assessment.get("completeness_score", 0) < 60 and skip_clarification:
            # User skipped, infer all missing details
            inference_result = await smart_inference(
                abstract, assessment.get("missing_critical", [])
            )
            enriched_abstract = inference_result.get("enriched_abstract", abstract)
            clarification_result = inference_result

        # ─────────────────────────────────────────────────────────────
        # Step 2: PARALLEL ANALYSIS (novelty, gaps, SWOT)
        # ─────────────────────────────────────────────────────────────
        novelty_task = score_novelty(enriched_abstract)
        gaps_task = analyze_gaps(enriched_abstract)
        
        # Run novelty and gaps in parallel first (SWOT needs novelty_score)
        novelty_result, gaps_result = await asyncio.gather(novelty_task, gaps_task)
        
        # Now run SWOT with the novelty score
        swot_result = await perform_swot(
            abstract=enriched_abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            num_similar=novelty_result.get("similar_papers_count", 0),
            target_tier="Q2",  # Default target tier
        )

        # ─────────────────────────────────────────────────────────────
        # Step 3: SEQUENTIAL ANALYSIS (publishability → suggestions)
        # ─────────────────────────────────────────────────────────────
        publishability_result = await predict_publishability(
            abstract=enriched_abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            gaps=gaps_result.get("gaps", []),
            strengths=swot_result.get("strengths", []),
            weaknesses=swot_result.get("weaknesses", []),
        )

        suggestions_result = await suggest_improvements(
            abstract=enriched_abstract,
            novelty_score=novelty_result.get("novelty_score", 50),
            weaknesses=swot_result.get("weaknesses", []),
            target_tier=publishability_result.get("target_tier", "Q2"),
        )

        # ─────────────────────────────────────────────────────────────
        # Step 4: RESPONSE AGGREGATION
        # ─────────────────────────────────────────────────────────────
        processing_time = time.time() - start_time

        return {
            "status": "complete",
            "novelty": {
                "score": novelty_result.get("novelty_score"),
                "reasoning": novelty_result.get("reasoning"),
                "most_similar_paper": novelty_result.get("most_similar_paper"),
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
                "similar_papers_count": novelty_result.get("similar_papers_count", 0),
                "completeness_score": assessment.get("completeness_score"),
                "clarification_applied": clarification_result is not None,
            },
        }

