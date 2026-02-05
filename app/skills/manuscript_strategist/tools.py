from llama_index.core.tools import FunctionTool
from app.skills.manuscript_strategist.functions import (
    generate_roadmap,
    fix_vietglish,
    calibrate_tone,
    plan_citations,
    simulate_reviewer,
    generate_template
)

# Tool definitions
roadmap_tool = FunctionTool.from_defaults(
    fn=generate_roadmap,
    name="section_roadmap",
    description="Generate writing roadmap for each manuscript section."
)

vietglish_tool = FunctionTool.from_defaults(
    fn=fix_vietglish,
    name="vietglish_fixer",
    description="Detect and fix Vietnamese-English writing errors."
)

tone_tool = FunctionTool.from_defaults(
    fn=calibrate_tone,
    name="tone_calibrator",
    description="Adjust writing tone for academic publication."
)

citation_tool = FunctionTool.from_defaults(
    fn=plan_citations,
    name="citation_strategist",
    description="Plan citation strategy per section."
)

reviewer_tool = FunctionTool.from_defaults(
    fn=simulate_reviewer,
    name="reviewer_simulator",
    description="Predict reviewer questions and concerns."
)

template_tool = FunctionTool.from_defaults(
    fn=generate_template,
    name="template_generator",
    description="Generate reporting guideline templates (CONSORT, STROBE, etc.)."
)

MANUSCRIPT_STRATEGIST_TOOLS = [
    roadmap_tool,
    vietglish_tool,
    tone_tool,
    citation_tool,
    reviewer_tool,
    template_tool
]
