from llama_index.core.tools import FunctionTool
from app.skills.journal_matcher.functions import (
    rank_journals,
    check_predatory,
    calculate_apc,
    estimate_timeline,
    plan_backup
)

# Tool definitions
journal_ranker_tool = FunctionTool.from_defaults(
    fn=rank_journals,
    name="journal_ranker",
    description="Rank top 10 journals by fit with research and preferences."
)

predatory_detector_tool = FunctionTool.from_defaults(
    fn=check_predatory,
    name="predatory_detector",
    description="Check if a journal is predatory or legitimate."
)

apc_calculator_tool = FunctionTool.from_defaults(
    fn=calculate_apc,
    name="apc_calculator",
    description="Calculate costs and find fee waivers."
)

timeline_estimator_tool = FunctionTool.from_defaults(
    fn=estimate_timeline,
    name="timeline_estimator",
    description="Estimate review and publication timeline."
)

backup_planner_tool = FunctionTool.from_defaults(
    fn=plan_backup,
    name="backup_planner",
    description="Create cascade strategy if rejected."
)

JOURNAL_MATCHER_TOOLS = [
    journal_ranker_tool,
    predatory_detector_tool,
    apc_calculator_tool,
    timeline_estimator_tool,
    backup_planner_tool
]
