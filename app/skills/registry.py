from typing import Dict, List
from llama_index.core.tools import FunctionTool
from app.skills.base import Skill

class SkillRegistry:
    _skills: Dict[str, Skill] = {}
    
    @classmethod
    def register(cls, skill: Skill):
        cls._skills[skill.config.name] = skill
    
    @classmethod
    def get(cls, name: str) -> Skill:
        return cls._skills.get(name)
    
    @classmethod
    def get_tool(cls, name: str) -> FunctionTool:
        return cls._skills[name].tool
    
    @classmethod
    def all_tools(cls) -> List[FunctionTool]:
        return [s.tool for s in cls._skills.values()]
    
    @classmethod
    def tools_by_category(cls, category: str) -> List[FunctionTool]:
        return [s.tool for s in cls._skills.values() if s.config.category == category]

registry = SkillRegistry()
