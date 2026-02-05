"""
Medical keyword extraction for PubMed search queries.
"""

import re
from typing import Optional

from app.core.llm_router import llm_router


class KeywordExtractor:
    """Extract medical keywords from research abstracts."""

    # Common medical research terms
    METHODOLOGY_TERMS = [
        "randomized controlled trial",
        "systematic review",
        "meta-analysis",
        "cohort study",
        "case-control",
        "cross-sectional",
        "machine learning",
        "deep learning",
        "neural network",
        "random forest",
        "logistic regression",
        "survival analysis",
    ]

    INTERVENTION_TERMS = [
        "treatment",
        "therapy",
        "intervention",
        "drug",
        "medication",
        "surgery",
        "procedure",
    ]

    async def extract_structured_keywords(
        self, abstract: str
    ) -> tuple[list[str], dict | None]:
        """
        Extract structured keywords and return both flat list and structured dict.

        Returns:
            Tuple of (flat keyword list, structured dict with disease/method/population)
        """
        prompt = f"""Extract search terms from this abstract. Output ONLY valid JSON, no thinking or explanation.

Categories:
- disease: specific condition (e.g., "sepsis", "diabetes mellitus type 2")
- method: technique used (e.g., "machine learning", "ultrasound")
- population: target group (e.g., "newborns", "ICU patients")

Abstract:
{abstract}

Output format (JSON only, no other text):
{{"disease": ["term1"], "method": ["term1"], "population": ["term1"]}}"""

        try:
            result = await llm_router.call(
                prompt=prompt,
                json_output=True,
                temperature=0.1,
                max_tokens=300,
            )

            if isinstance(result, dict) and any(
                k in result for k in ("disease", "method", "population")
            ):
                # Build flat keyword list: disease first, then method, then population
                keywords = []
                for key in ("disease", "method", "population"):
                    for term in result.get(key, []):
                        if term and term.lower() not in [k.lower() for k in keywords]:
                            keywords.append(term)
                if keywords:
                    return keywords[:5], result

            # Fallback
            fallback = self._extract_simple(abstract, 5)
            return fallback, None

        except Exception as e:
            print(f"Keyword extraction LLM failed: {e}")
            fallback = self._extract_simple(abstract, 5)
            return fallback, None

    async def extract_keywords(
        self,
        abstract: str,
        max_keywords: int = 5,
        use_llm: bool = True,
    ) -> list[str]:
        """
        Extract key medical terms from abstract.

        Args:
            abstract: Research abstract text
            max_keywords: Maximum number of keywords to return
            use_llm: Whether to use LLM for extraction (more accurate)

        Returns:
            List of keywords
        """
        if use_llm:
            return await self._extract_with_llm(abstract, max_keywords)
        else:
            return self._extract_simple(abstract, max_keywords)

    async def _extract_with_llm(self, abstract: str, max_keywords: int) -> list[str]:
        """Extract keywords using LLM with structured disease/method/population fields."""
        prompt = f"""Extract search terms from this abstract. Output ONLY valid JSON, no thinking or explanation.

Categories:
- disease: specific condition (e.g., "sepsis", "diabetes mellitus type 2")
- method: technique used (e.g., "machine learning", "ultrasound")
- population: target group (e.g., "newborns", "ICU patients")

Abstract:
{abstract}

Output format (JSON only, no other text):
{{"disease": ["term1"], "method": ["term1"], "population": ["term1"]}}"""

        try:
            result = await llm_router.call(
                prompt=prompt,
                json_output=True,
                temperature=0.1,
                max_tokens=300,
            )

            if isinstance(result, dict):
                keywords = []
                # Disease terms are most important — add first
                for term in result.get("disease", []):
                    if term and term.lower() not in [k.lower() for k in keywords]:
                        keywords.append(term)
                # Method terms next
                for term in result.get("method", []):
                    if term and term.lower() not in [k.lower() for k in keywords]:
                        keywords.append(term)
                # Population terms last
                for term in result.get("population", []):
                    if term and term.lower() not in [k.lower() for k in keywords]:
                        keywords.append(term)
                if keywords:
                    return keywords[:max_keywords]

            # Fallback to simple extraction
            return self._extract_simple(abstract, max_keywords)

        except Exception:
            return self._extract_simple(abstract, max_keywords)

    def _extract_simple(self, abstract: str, max_keywords: int) -> list[str]:
        """Simple rule-based keyword extraction (fallback)."""
        keywords = []

        # Lowercase for matching
        text_lower = abstract.lower()

        # Extract methodology terms
        for term in self.METHODOLOGY_TERMS:
            if term in text_lower and term not in keywords:
                keywords.append(term)
                if len(keywords) >= max_keywords:
                    return keywords

        # Extract intervention terms
        for term in self.INTERVENTION_TERMS:
            if term in text_lower and term not in keywords:
                keywords.append(term)
                if len(keywords) >= max_keywords:
                    return keywords

        # Extract capitalized multi-word terms (likely medical terms)
        capitalized_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
        capitalized_terms = re.findall(capitalized_pattern, abstract)
        for term in capitalized_terms[:3]:
            if term.lower() not in keywords:
                keywords.append(term.lower())
                if len(keywords) >= max_keywords:
                    return keywords

        # If still not enough, extract frequent nouns (simple heuristic)
        words = re.findall(r"\b[a-z]{4,}\b", text_lower)
        word_freq = {}
        for word in words:
            if word not in ["study", "research", "result", "data", "method"]:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Add top frequent words
        for word, _ in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
            if word not in keywords:
                keywords.append(word)
                if len(keywords) >= max_keywords:
                    return keywords

        return keywords[:max_keywords] if keywords else ["biomedical research"]

    def build_pubmed_query(
        self,
        keywords: list[str],
        structured: dict | None = None,
        title_only: bool = True,
    ) -> str:
        """
        Build PubMed search query from keywords.

        When structured dict is provided (with disease/method/population keys),
        builds a smarter query: disease terms are required (AND), while method
        and population are optional boosters (OR within their group).

        Args:
            keywords: Flat list of keywords (fallback)
            structured: Optional dict with disease/method/population lists
            title_only: If True, search only in titles (more precise)

        Returns:
            PubMed query string
        """
        field = "[Title/Abstract]" if not title_only else "[Title]"

        if structured:
            disease_terms = structured.get("disease", [])
            method_terms = structured.get("method", [])
            population_terms = structured.get("population", [])

            parts = []

            # Disease group: OR between disease terms (required)
            if disease_terms:
                if len(disease_terms) == 1:
                    parts.append(f'"{disease_terms[0]}"{field}')
                else:
                    disease_or = " OR ".join(f'"{t}"{field}' for t in disease_terms)
                    parts.append(f"({disease_or})")

            # Method group: OR between method terms (required)
            if method_terms:
                if len(method_terms) == 1:
                    parts.append(f'"{method_terms[0]}"{field}')
                else:
                    method_or = " OR ".join(f'"{t}"{field}' for t in method_terms)
                    parts.append(f"({method_or})")

            # Population is optional — don't AND it in to avoid over-restricting
            # Instead, we'll let semantic ranking handle population filtering

            if parts:
                return " AND ".join(parts)

        # Fallback: use flat keyword list with AND on first 3 terms only
        if not keywords:
            return "biomedical research[Title]"

        query_parts = [f'"{kw}"{field}' for kw in keywords[:3]]
        return " AND ".join(query_parts)
