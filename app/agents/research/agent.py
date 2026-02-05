"""
Deep Research Agent - Main Orchestrator.

Multi-source search strategy:
1. Extract keywords from abstract
2. Search PubMed and/or Google Scholar
3. Merge and deduplicate results
4. Rank by semantic similarity
5. LLM relevance validation
"""

import asyncio
import time
from typing import Callable, Literal, Optional

from app.agents.research.keyword_extractor import KeywordExtractor
from app.agents.research.pubmed_client import PubMedClient
from app.agents.research.scholar_client import ScholarClient
from app.agents.research.semantic_ranker import SemanticRanker
from app.agents.schemas import RankingResult, ResearchPaper
from app.core.llm_router import llm_router

# Source types
SourceType = Literal["pubmed", "scholar"]


class ResearchAgent:
    """
    Autonomous agent for deep literature research.

    Supports multiple sources:
    - PubMed: Biomedical literature (NCBI)
    - Google Scholar: Broader academic papers

    Workflow:
    1. Extract structured keywords (disease/method/population)
    2. Search selected sources in parallel
    3. Merge and deduplicate results
    4. Filter out papers without abstracts
    5. Rank by title similarity (filter to top 50)
    6. Rank by abstract similarity (top 20 candidates)
    7. LLM relevance validation (final top papers)
    """

    def __init__(
        self,
        pubmed_api_key: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize research agent.

        Args:
            pubmed_api_key: Optional NCBI API key for higher rate limits
            embedding_model: SentenceTransformer model name
        """
        self.pubmed = PubMedClient(api_key=pubmed_api_key)
        self.scholar = ScholarClient()
        self.ranker = SemanticRanker(model_name=embedding_model)
        self.extractor = KeywordExtractor()

    async def search(
        self,
        abstract: str,
        max_papers: int = 20,
        title_search_limit: int = 500,
        sources: list[SourceType] | None = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
    ) -> RankingResult:
        """
        Perform deep literature search.

        Args:
            abstract: User's research abstract
            max_papers: Number of final papers to return (default: 20)
            title_search_limit: Number of papers to fetch in title search (default: 500)
            sources: List of sources to search (default: ["pubmed", "scholar"])
            on_progress: Optional callback for progress updates (message, percent)

        Returns:
            RankingResult with ranked papers
        """
        if sources is None:
            sources = ["pubmed", "scholar"]

        start_time = time.time()

        # ════════════════════════════════════════════════════════
        # Stage 1: Structured Keyword Extraction
        # ════════════════════════════════════════════════════════
        if on_progress:
            await on_progress("Extracting keywords...", 10)

        keywords, structured = await self.extractor.extract_structured_keywords(abstract)

        if on_progress:
            await on_progress(f"Keywords: {', '.join(keywords)}", 15)

        # ════════════════════════════════════════════════════════
        # Stage 2: Search Sources in Parallel
        # ════════════════════════════════════════════════════════
        source_names = ", ".join(s.title() for s in sources)
        if on_progress:
            await on_progress(f"Searching {source_names}...", 20)

        all_papers: list[ResearchPaper] = []
        search_tasks = []

        # PubMed search
        if "pubmed" in sources:
            query = self.extractor.build_pubmed_query(
                keywords=keywords, structured=structured, title_only=False
            )
            search_tasks.append(
                self._search_pubmed(keywords, query, title_search_limit)
            )

        # Google Scholar search
        if "scholar" in sources:
            search_tasks.append(
                self._search_scholar(keywords, min(50, title_search_limit // 10))
            )

        # Run searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)
            elif isinstance(result, Exception):
                # Log but continue with other sources
                print(f"Search error: {result}")

        # Deduplicate by title (case-insensitive)
        seen_titles = set()
        unique_papers = []
        for paper in all_papers:
            title_lower = paper.title.lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_papers.append(paper)

        total_found = len(unique_papers)

        if on_progress:
            await on_progress(f"Found {total_found} unique papers", 35)

        if not unique_papers:
            return RankingResult(
                papers=[],
                total_found=0,
                total_ranked=0,
                avg_similarity=0.0,
                processing_time_seconds=time.time() - start_time,
            )

        # ════════════════════════════════════════════════════════
        # Stage 3: Filter Papers Without Abstracts
        # ════════════════════════════════════════════════════════
        initial_papers = [
            p for p in unique_papers if p.abstract != "No abstract available"
        ]

        if on_progress:
            await on_progress(
                f"Filtered to {len(initial_papers)} papers with abstracts", 45
            )

        # ════════════════════════════════════════════════════════
        # Stage 4: Title Similarity Ranking
        # ════════════════════════════════════════════════════════
        if on_progress:
            await on_progress("Ranking by title similarity...", 50)

        top_50_by_title = self.ranker.rank_by_title_similarity(
            query_abstract=abstract,
            papers=initial_papers,
            top_k=min(50, len(initial_papers)),
        )

        # ════════════════════════════════════════════════════════
        # Stage 5: Abstract Similarity Ranking
        # ════════════════════════════════════════════════════════
        if on_progress:
            await on_progress("Ranking by abstract similarity...", 70)

        # Get more candidates than max_papers so validation can filter some out
        candidate_count = min(max_papers + 10, len(top_50_by_title))
        candidates = self.ranker.rank_by_abstract_similarity(
            query_abstract=abstract, papers=top_50_by_title, top_k=candidate_count
        )

        # ════════════════════════════════════════════════════════
        # Stage 6: LLM Relevance Validation
        # ════════════════════════════════════════════════════════
        if on_progress:
            await on_progress("Validating relevance with LLM...", 85)

        final_papers = await self._validate_relevance(
            abstract=abstract,
            candidates=candidates,
            max_papers=max_papers,
        )

        # ════════════════════════════════════════════════════════
        # Calculate Metrics
        # ════════════════════════════════════════════════════════
        avg_similarity = (
            sum(p.similarity for p in final_papers) / len(final_papers)
            if final_papers
            else 0.0
        )

        processing_time = time.time() - start_time

        if on_progress:
            await on_progress(
                f"Completed! {len(final_papers)} papers ranked (avg similarity: {avg_similarity:.2f})",
                100,
            )

        return RankingResult(
            papers=final_papers,
            total_found=total_found,
            total_ranked=len(final_papers),
            avg_similarity=avg_similarity,
            processing_time_seconds=processing_time,
        )

    async def _validate_relevance(
        self,
        abstract: str,
        candidates: list[ResearchPaper],
        max_papers: int,
    ) -> list[ResearchPaper]:
        """
        Use LLM to validate that candidate papers are truly relevant.

        Checks each paper's title and abstract against the query abstract
        to confirm disease, method, and population match.

        Args:
            abstract: User's research abstract
            candidates: Semantic-ranked candidate papers
            max_papers: Maximum papers to return

        Returns:
            Filtered list of relevant papers
        """
        if not candidates:
            return []

        # Build a compact summary of each candidate for LLM evaluation
        paper_summaries = []
        for i, paper in enumerate(candidates):
            # Truncate abstract to 200 chars for LLM input
            abstract_snippet = paper.abstract[:200]
            paper_summaries.append(
                f"{i}. Title: {paper.title}\n   Abstract: {abstract_snippet}..."
            )

        papers_text = "\n".join(paper_summaries)

        prompt = f"""Output ONLY a JSON array of relevant paper indices. No thinking, no explanation.

Query: {abstract[:300]}

Papers:
{papers_text}

Relevant = similar disease OR similar method. Return indices only, e.g.: [0, 2, 5]"""

        try:
            result = await llm_router.call(
                prompt=prompt,
                json_output=True,
                temperature=0.1,
                max_tokens=500,
            )

            relevant_indices = set()
            if isinstance(result, list):
                relevant_indices = {int(i) for i in result if isinstance(i, (int, float))}
            elif isinstance(result, dict):
                # Handle wrapped response like {"relevant": [0, 1, 2]}
                for key in result.values():
                    if isinstance(key, list):
                        relevant_indices = {int(i) for i in key if isinstance(i, (int, float))}
                        break

            # Filter candidates to only relevant ones
            validated = [
                candidates[i]
                for i in range(len(candidates))
                if i in relevant_indices
            ]

            # If LLM validation filtered out too many, keep top by similarity
            if len(validated) < max_papers // 2:
                return candidates[:max_papers]

            return validated[:max_papers]

        except Exception as e:
            # If LLM validation fails, fall back to semantic ranking only
            print(f"LLM relevance validation failed: {e}")
            return candidates[:max_papers]

    async def _search_pubmed(
        self, keywords: list[str], query: str, max_results: int
    ) -> list[ResearchPaper]:
        """Search PubMed and fetch abstracts."""
        pmids = await self.pubmed.search_titles(
            keywords=keywords,
            year_min=2020,
            year_max=2025,
            max_results=max_results,
            query=query,
        )

        if not pmids:
            return []

        # Fetch first 100 papers with abstracts
        papers = await self.pubmed.fetch_abstracts_batch(
            pmids[: min(100, len(pmids))]
        )
        return papers

    async def _search_scholar(
        self, keywords: list[str], max_results: int
    ) -> list[ResearchPaper]:
        """Search Google Scholar."""
        try:
            papers = await self.scholar.search_by_keywords(
                keywords=keywords,
                year_min=2020,
                max_results=max_results,
            )
            return papers
        except Exception as e:
            print(f"Google Scholar search failed: {e}")
            return []

    async def close(self):
        """Close resources."""
        await self.pubmed.close()
