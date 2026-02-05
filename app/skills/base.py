from pydantic import BaseModel
from typing import Callable, Optional, Any
from llama_index.core.tools import FunctionTool

class SkillConfig(BaseModel):
    name: str
    description: str
    category: str  # input_clarifier, topic_analyzer, journal_matcher, manuscript_strategist

class Skill:
    def __init__(
        self, 
        config: SkillConfig, 
        fn: Callable,
        prompt_template: str = ""
    ):
        self.config = config
        self.fn = fn
        self.prompt_template = prompt_template
        self.tool = FunctionTool.from_defaults(
            fn=fn,
            name=config.name,
            description=config.description
        )
