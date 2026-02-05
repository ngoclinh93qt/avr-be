JOURNAL_RANKER_PROMPT = """
You are a journal selection expert.

## ABSTRACT:
{abstract}

## CANDIDATE JOURNALS:
{journals}

## USER PREFERENCES:
- Max APC: ${max_apc}
- IF Range: {min_if} - {max_if}
- Open Access Only: {oa_only}
- Specialty: {specialty}

## OUTPUT (JSON only):
{{
    "rankings": [
        {{
            "rank": <1-10>,
            "journal_name": "<name>",
            "match_score": <0-100>,
            "reasoning": "<why this fits>",
            "pros": ["<pro1>"],
            "cons": ["<con1>"],
            "submission_tip": "<specific tip>"
        }}
    ]
}}
"""

PREDATORY_DETECTOR_PROMPT = """
You are a predatory journal detection expert.

## JOURNAL:
Name: {journal_name}
Publisher: {publisher}
ISSN: {issn}

## INDEXING STATUS:
- DOAJ: {in_doaj}
- Scopus: {in_scopus}
- PubMed: {in_pubmed}
- Beall's List: {in_bealls}

## RED FLAGS:
1. Aggressive solicitation
2. Unrealistic review time (<2 weeks)
3. No peer review
4. Fake impact factor
5. Hidden APCs

## OUTPUT (JSON only):
{{
    "is_predatory": <true|false>,
    "confidence": <0.0-1.0>,
    "risk_level": "<safe|caution|danger>",
    "red_flags": ["<found flags>"],
    "green_flags": ["<positive indicators>"],
    "recommendation": "<proceed|verify|avoid>",
    "verification_steps": ["<what to check>"]
}}
"""

APC_CALCULATOR_PROMPT = """
You are a publication cost advisor.

## JOURNAL OPTIONS:
{journals}

## USER BUDGET: ${budget}
## USER COUNTRY: Vietnam

## OUTPUT (JSON only):
{{
    "within_budget": [
        {{
            "journal": "<name>",
            "apc": <amount>,
            "waiver_available": <true|false>,
            "waiver_type": "<full|partial|none>",
            "waiver_eligibility": "<criteria>"
        }}
    ],
    "over_budget_with_waiver": [
        {{
            "journal": "<name>",
            "apc": <amount>,
            "potential_waiver": "<description>"
        }}
    ],
    "no_apc_options": ["<journal names>"],
    "recommendation": "<best choice with reasoning>"
}}
"""

TIMELINE_ESTIMATOR_PROMPT = """
You are a publication timeline analyst.

## JOURNALS:
{journals}

## USER DEADLINE: {deadline}

## OUTPUT (JSON only):
{{
    "analysis": [
        {{
            "journal": "<name>",
            "first_decision_weeks": <number>,
            "total_weeks": <number>,
            "meets_deadline": <true|false>,
            "confidence": "<high|medium|low>"
        }}
    ],
    "fastest_options": ["<journal1>", "<journal2>"],
    "recommendation": "<best for deadline>"
}}
"""

BACKUP_PLANNER_PROMPT = """
You are a publication strategy advisor.

## PRIMARY TARGET:
Journal: {primary_journal}
Match Score: {match_score}

## ALTERNATIVES:
{alternatives}

## OUTPUT (JSON only):
{{
    "cascade_plan": [
        {{
            "priority": <1-5>,
            "journal": "<name>",
            "adaptation_needed": "<what to change>",
            "resubmit_time_days": <number>
        }}
    ],
    "pivot_triggers": [
        {{
            "rejection_reason": "<reason>",
            "next_action": "<what to do>"
        }}
    ],
    "total_timeline_estimate": "<X-Y months>"
}}
"""
