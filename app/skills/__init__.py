from app.skills.registry import registry
from app.skills.input_clarifier.tools import INPUT_CLARIFIER_TOOLS
from app.skills.topic_analyzer.tools import TOPIC_ANALYZER_TOOLS
from app.skills.journal_matcher.tools import JOURNAL_MATCHER_TOOLS
from app.skills.manuscript_strategist.tools import MANUSCRIPT_STRATEGIST_TOOLS

ALL_TOOLS = (
    INPUT_CLARIFIER_TOOLS +
    TOPIC_ANALYZER_TOOLS +
    JOURNAL_MATCHER_TOOLS +
    MANUSCRIPT_STRATEGIST_TOOLS
)

def get_all_tools():
    return ALL_TOOLS

def get_tools_by_feature(feature: str):
    mapping = {
        "clarifier": INPUT_CLARIFIER_TOOLS,
        "topic": TOPIC_ANALYZER_TOOLS,
        "journal": JOURNAL_MATCHER_TOOLS,
        "manuscript": MANUSCRIPT_STRATEGIST_TOOLS
    }
    return mapping.get(feature, [])
