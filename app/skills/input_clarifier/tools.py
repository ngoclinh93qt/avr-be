from llama_index.core.tools import FunctionTool
from app.skills.base import Skill, SkillConfig
from app.skills.input_clarifier.functions import (
    assess_completeness,
    generate_questions,
    smart_inference
)
from app.skills.input_clarifier.prompts import *

# Tool definitions
assess_completeness_tool = FunctionTool.from_defaults(
    fn=assess_completeness,
    name="assess_completeness",
    description="Assess research input completeness using PICO + 5W1H frameworks. Returns completeness score and missing elements."
)

generate_questions_tool = FunctionTool.from_defaults(
    fn=generate_questions,
    name="generate_clarifying_questions",
    description="Generate 2-4 clarifying questions in Vietnamese to fill information gaps."
)

smart_inference_tool = FunctionTool.from_defaults(
    fn=smart_inference,
    name="smart_inference",
    description="Intelligently infer missing details from context when user skips clarification."
)

INPUT_CLARIFIER_TOOLS = [
    assess_completeness_tool,
    generate_questions_tool,
    smart_inference_tool
]
