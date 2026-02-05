from llama_index.core.tools import FunctionTool
from app.skills.topic_analyzer.functions import (
    score_novelty,
    analyze_gaps,
    perform_swot,
    predict_publishability,
    suggest_improvements
)

# Tool definitions
novelty_scorer_tool = FunctionTool.from_defaults(
    fn=score_novelty,
    name="novelty_scorer",
    description="Score research novelty 0-100 by comparing with existing literature via RAG."
)

gap_analyzer_tool = FunctionTool.from_defaults(
    fn=analyze_gaps,
    name="gap_analyzer",
    description="Identify research gaps the study could fill."
)

swot_analyzer_tool = FunctionTool.from_defaults(
    fn=perform_swot,
    name="swot_analyzer",
    description="SWOT analysis from reviewer perspective."
)

publishability_predictor_tool = FunctionTool.from_defaults(
    fn=predict_publishability,
    name="publishability_predictor",
    description="Predict publication success and target journal tier."
)

improvement_suggester_tool = FunctionTool.from_defaults(
    fn=suggest_improvements,
    name="improvement_suggester",
    description="Suggest specific actions to improve novelty and publishability."
)

TOPIC_ANALYZER_TOOLS = [
    novelty_scorer_tool,
    gap_analyzer_tool,
    swot_analyzer_tool,
    publishability_predictor_tool,
    improvement_suggester_tool
]
