"""LLM Prompts for AVR Research Formation System."""

from .clarify import get_clarification_prompt, format_clarification_response
from .abstract_gen import get_abstract_generation_prompt
from .reviewer_sim import get_reviewer_simulation_prompt
from .guided_revision import get_guided_revision_prompt
from .manuscript_outline import get_manuscript_outline_prompt

__all__ = [
    "get_clarification_prompt",
    "format_clarification_response",
    "get_abstract_generation_prompt",
    "get_reviewer_simulation_prompt",
    "get_guided_revision_prompt",
    "get_manuscript_outline_prompt",
]
