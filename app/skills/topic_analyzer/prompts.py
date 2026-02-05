NOVELTY_SCORER_PROMPT = """
You are an expert medical research evaluator.

## USER'S ABSTRACT:
{abstract}

## SIMILAR EXISTING PAPERS ({num_papers} found):
{similar_papers}

## SCORING CRITERIA:
- 0-30: Nearly identical to existing work
- 31-50: Minor variations only
- 51-70: Moderate novelty, small gaps
- 71-85: Good novelty, clear contribution
- 86-100: Highly novel, significant advancement

## OUTPUT (JSON only):
{{
    "novelty_score": <0-100>,
    "reasoning": "<2-3 sentences explaining score>",
    "most_similar_paper": "<title of closest work>",
    "differentiation": "<how user's work differs>"
}}
"""

GAP_ANALYZER_PROMPT = """
You are a research gap identification specialist.

## USER'S ABSTRACT:
{abstract}

## EXISTING LITERATURE:
{similar_papers}

## IDENTIFY gaps this study fills:
- Methodological gaps (technique, design)
- Geographical gaps (Vietnam/Asia context)
- Population gaps (specific demographic)
- Temporal gaps (outdated studies)

## OUTPUT (JSON only):
{{
    "gaps": [
        {{
            "type": "<methodological|geographical|population|temporal>",
            "description": "<specific gap>",
            "how_filled": "<how study addresses this>",
            "strength": "<strong|moderate|weak>"
        }}
    ],
    "summary": "<1-2 sentence overall assessment>"
}}
"""

SWOT_ANALYZER_PROMPT = """
You are a research proposal evaluator.

## ABSTRACT:
{abstract}

## CONTEXT:
- Novelty Score: {novelty_score}
- Similar Papers: {num_similar}
- Target Tier: {target_tier}

## OUTPUT (JSON only):
{{
    "strengths": [
        {{"point": "<strength>", "reviewer_appeal": "<why reviewers like>"}}
    ],
    "weaknesses": [
        {{"point": "<weakness>", "mitigation": "<how to address>"}}
    ],
    "opportunities": [
        {{"point": "<opportunity>", "action": "<recommended action>"}}
    ],
    "threats": [
        {{"point": "<threat>", "risk_level": "<high|medium|low>"}}
    ]
}}
"""

PUBLISHABILITY_PREDICTOR_PROMPT = """
You are a journal editor assistant.

## RESEARCH SUMMARY:
Abstract: {abstract}
Novelty Score: {novelty_score}/100
Gaps Filled: {gaps}
Strengths: {strengths}
Weaknesses: {weaknesses}

## OUTPUT (JSON only):
{{
    "publishability": "<LOW|MEDIUM|HIGH>",
    "confidence": <0.0-1.0>,
    "target_tier": "<Q1|Q2|Q3|Q4>",
    "reasoning": "<2-3 sentences>",
    "success_factors": ["<factor1>", "<factor2>"],
    "risk_factors": ["<risk1>", "<risk2>"]
}}
"""

IMPROVEMENT_SUGGESTER_PROMPT = """
You are a research mentor.

## CURRENT STATE:
Abstract: {abstract}
Novelty: {novelty_score}/100
Weaknesses: {weaknesses}
Target: {target_tier}

## TASK:
Provide 3-5 specific, actionable improvements.

## OUTPUT (JSON only):
{{
    "suggestions": [
        {{
            "action": "<specific action>",
            "impact": "<how it improves>",
            "effort": "<low|medium|high>",
            "priority": <1-5>
        }}
    ],
    "quick_wins": ["<easy immediate improvements>"],
    "long_term": ["<if time permits>"]
}}
"""
