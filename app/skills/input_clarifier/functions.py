from app.core.llm_router import llm_router
from app.skills.input_clarifier.prompts import *
import json


async def assess_completeness(user_input: str) -> dict:
    """Assess input completeness using PICO + 5W1H"""
    prompt = ASSESS_COMPLETENESS_PROMPT.format(user_input=user_input)
    return await llm_router.call(prompt, json_output=True)


async def generate_questions(user_input: str, assessment: dict) -> dict:
    """Generate clarifying questions for missing information"""
    prompt = GENERATE_QUESTIONS_PROMPT.format(
        user_input=user_input,
        assessment=json.dumps(assessment, ensure_ascii=False, indent=2)
    )
    return await llm_router.call(prompt, json_output=True)


async def smart_inference(user_input: str, missing_elements: list) -> dict:
    """Infer missing details from context"""
    prompt = SMART_INFERENCE_PROMPT.format(
        user_input=user_input,
        missing_elements=json.dumps(missing_elements, ensure_ascii=False)
    )
    return await llm_router.call(prompt, json_output=True)
