SECTION_ROADMAP_PROMPT = """
You are a medical manuscript writing mentor.

## ABSTRACT:
{abstract}

## TARGET JOURNAL:
Name: {journal_name}
Word Limit: {word_limit}
Structure: {structure}
Citation Style: {citation_style}

## OUTPUT (JSON only):
{{
    "total_words": <number>,
    "sections": [
        {{
            "name": "<Introduction|Methods|Results|Discussion>",
            "word_range": "<min-max>",
            "paragraphs": <number>,
            "key_points": ["<what to cover>"],
            "citations_needed": <number>,
            "opening_suggestion": "<sample opening>"
        }}
    ],
    "narrative_flow": "<how sections connect>",
    "key_message": "<one sentence takeaway>"
}}
"""

VIETGLISH_FIXER_PROMPT = """
You are an expert editor for Vietnamese-English academic writing.

## TEXT:
{text}

## COMMON VIET-GLISH PATTERNS:
1. Article errors (a/an/the)
2. Tense confusion (present perfect)
3. Preposition errors
4. Subject-verb agreement
5. "According to X showed that" redundancy
6. Word order issues

## OUTPUT (JSON only):
{{
    "errors": [
        {{
            "original": "<problematic text>",
            "corrected": "<fixed version>",
            "type": "<article|tense|preposition|agreement|redundancy|word_order>",
            "explanation": "<why wrong>",
            "vietnamese_influence": "<what caused this>"
        }}
    ],
    "corrected_text": "<full corrected text>",
    "summary": {{
        "total_errors": <number>,
        "by_type": {{"article": <n>, "tense": <n>}},
        "severity": "<minor|moderate|significant>"
    }},
    "tips": ["<personalized improvement tips>"]
}}
"""

TONE_CALIBRATOR_PROMPT = """
You are an academic writing style expert.

## TEXT:
{text}

## TARGET:
Journal: {journal_name}
Field: {field}

## CHECK FOR:
1. Informal language
2. First person overuse
3. Hedging issues
4. Passive/active balance
5. Wordiness
6. Weak verbs

## OUTPUT (JSON only):
{{
    "issues": [
        {{
            "original": "<phrase>",
            "revised": "<improved>",
            "issue": "<informal|first_person|hedging|passive|wordy|weak_verb>",
            "explanation": "<brief>"
        }}
    ],
    "revised_text": "<full revised text>",
    "scores": {{
        "formality": <1-10>,
        "clarity": <1-10>,
        "confidence": <1-10>
    }}
}}
"""

CITATION_STRATEGIST_PROMPT = """
You are a citation strategy advisor.

## ABSTRACT:
{abstract}

## TARGET JOURNAL: {journal_name}
## SECTION: {section}

## OUTPUT (JSON only):
{{
    "recommended_count": <number>,
    "breakdown": {{
        "recent_2_years": <n>,
        "classic": <n>,
        "methodology": <n>,
        "vietnamese": <n>
    }},
    "search_queries": [
        {{
            "query": "<PubMed search>",
            "purpose": "<what to cite>",
            "priority": <1-5>
        }}
    ],
    "tips": ["<citation tips>"],
    "avoid": ["<what not to do>"]
}}
"""

REVIEWER_SIMULATOR_PROMPT = """
You are simulating a peer reviewer for {journal_name}.

## SECTION: {section}
## CONTENT:
{content}

## OUTPUT (JSON only):
{{
    "major_concerns": [
        {{
            "question": "<reviewer question>",
            "severity": "<critical|major|minor>",
            "likelihood": "<very_likely|likely|possible>",
            "preemptive_fix": "<how to address in manuscript>"
        }}
    ],
    "minor_comments": [
        {{
            "comment": "<comment>",
            "easy_fix": <true|false>,
            "suggestion": "<fix>"
        }}
    ],
    "likely_decision": "<accept|minor_revision|major_revision|reject>",
    "strengths_noted": ["<what reviewer likes>"],
    "checklist": ["<verify before submit>"]
}}
"""

TEMPLATE_GENERATOR_PROMPT = """
You are a reporting guideline expert.

## STUDY TYPE: {study_type}

## GUIDELINES:
- CONSORT: RCTs
- STROBE: Observational
- PRISMA: Systematic reviews
- CARE: Case reports
- STARD: Diagnostic

## OUTPUT (JSON only):
{{
    "guideline": "<CONSORT|STROBE|PRISMA|CARE|STARD>",
    "checklist": [
        {{
            "item": "<e.g., 1a>",
            "section": "<title|abstract|methods|results|discussion>",
            "description": "<what to report>",
            "example": "<sample text>",
            "required": <true|false>
        }}
    ],
    "template": {{
        "title_format": "<template>",
        "abstract_structure": ["<components>"],
        "methods_subsections": ["<subsections>"]
    }},
    "common_omissions": ["<frequently missed>"]
}}
"""
