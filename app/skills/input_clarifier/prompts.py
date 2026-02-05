ASSESS_COMPLETENESS_PROMPT = """
You are a research consultant analyzing input completeness.

## USER INPUT:
{user_input}

## ANALYZE using PICO + 5W1H:

### PICO Elements (Medical Research):
- Population: Who are the subjects?
- Intervention: What method/treatment?
- Comparison: What is the control/comparison?
- Outcome: What is measured?

### 5W1H Elements:
- What: Research question
- Who: Subjects/researchers
- When: Timeline/period
- Where: Setting/location
- Why: Significance
- How: Methodology

## OUTPUT (JSON only, no markdown):
{{
    "completeness_score": <0-100>,
    "elements": {{
        "population": {{"status": "present|missing|unclear", "value": "..."}},
        "intervention": {{"status": "present|missing|unclear", "value": "..."}},
        "comparison": {{"status": "present|missing|unclear", "value": "..."}},
        "outcome": {{"status": "present|missing|unclear", "value": "..."}},
        "sample_size": {{"status": "present|missing|unclear", "value": "..."}},
        "setting": {{"status": "present|missing|unclear", "value": "..."}},
        "timeline": {{"status": "present|missing|unclear", "value": "..."}}
    }},
    "study_type": "<RCT|cohort|case-control|cross-sectional|case-report|diagnostic|review|unclear>",
    "missing_critical": ["<list of critical missing elements>"],
    "can_proceed": <true if score >= 60>
}}
"""

GENERATE_QUESTIONS_PROMPT = """
You are a research mentor helping clarify a study proposal.

## USER INPUT:
{user_input}

## ASSESSMENT:
{assessment}

## TASK:
Generate 2-4 clarifying questions in Vietnamese to fill critical gaps.

## RULES:
- Questions must be specific and answerable
- Prioritize PICO gaps
- Be supportive, not interrogative
- Max 4 questions

## OUTPUT (JSON only):
{{
    "intro_message": "<friendly Vietnamese intro, e.g., 'Để đánh giá chính xác hơn, tôi cần thêm thông tin:'>",
    "questions": [
        {{
            "question": "<Vietnamese question>",
            "element": "<population|intervention|comparison|outcome|sample_size|setting|timeline>",
            "priority": <1-4>
        }}
    ],
    "skip_message": "<Vietnamese message if user wants to skip, e.g., 'Bạn có thể bỏ qua, tôi sẽ dựa vào giả định hợp lý.'>"
}}
"""

SMART_INFERENCE_PROMPT = """
You are inferring missing research details from context.

## USER INPUT:
{user_input}

## MISSING ELEMENTS:
{missing_elements}

## INFERENCE RULES:
- Vietnamese hospital → Setting = Vietnam
- "trẻ em/nhi" → Population = Pediatric
- No comparison mentioned → Assume no control group
- No timeline → Assume retrospective
- Medical imaging → Likely diagnostic accuracy study

## OUTPUT (JSON only):
{{
    "inferences": [
        {{
            "element": "<element name>",
            "inferred_value": "<value>",
            "confidence": <0.0-1.0>,
            "assumption": "<what assumption was made>"
        }}
    ],
    "enriched_abstract": "<original abstract + inferred context combined into natural text>",
    "warnings": ["<any assumptions user should verify>"]
}}
"""
