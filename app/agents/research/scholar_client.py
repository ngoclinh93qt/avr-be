"""
Google Scholar Client using scholarly library.

Note: Google Scholar has no official API. This uses web scraping
which may be rate-limited or blocked. Use responsibly.
"""

import asyncio
from typing import Optional

from scholarly import scholarly

from app.agents.schemas import ResearchPaper


class ScholarClient:
    """Client for Google Scholar search."""

    def __init__(self):
        """Initialize Scholar client."""
        # Configure scholarly to use free proxies if needed
        # scholarly.use_proxy(http=proxy_url)  # Uncomment if getting blocked
        pass

    async def search(
        self,
        query: str,
        year_min: int = 2020,
        max_results: int = 50,
    ) -> list[ResearchPaper]:
        """
        Search Google Scholar.

        Args:
            query: Search query string
            year_min: Minimum publication year
            max_results: Maximum number of results

        Returns:
            List of ResearchPaper objects
        """
        # Run blocking scholarly calls in thread pool
        loop = asyncio.get_event_loop()
        papers = await loop.run_in_executor(
            None, self._search_sync, query, year_min, max_results
        )
        return papers

    def _search_sync(
        self, query: str, year_min: int, max_results: int
    ) -> list[ResearchPaper]:
        """Synchronous search implementation."""
        papers = []

        try:
            # Search with year filter
            search_query = scholarly.search_pubs(query, year_low=year_min)

            for i, result in enumerate(search_query):
                if i >= max_results:
                    break

                try:
                    paper = self._parse_result(result)
                    if paper:
                        papers.append(paper)
                except Exception:
                    continue

        except Exception as e:
            # Scholar might block or timeout
            print(f"Google Scholar error: {e}")

        return papers

    def _parse_result(self, result: dict) -> Optional[ResearchPaper]:
        """Parse a scholarly result into ResearchPaper."""
        bib = result.get("bib", {})

        title = bib.get("title", "")
        if not title:
            return None

        # Extract authors
        authors = bib.get("author", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(" and ")]

        # Extract abstract (scholarly calls it 'abstract')
        abstract = bib.get("abstract", "")
        if not abstract:
            # Sometimes in 'snippet'
            abstract = result.get("snippet", "No abstract available")

        # Year
        year = 2020
        pub_year = bib.get("pub_year")
        if pub_year:
            try:
                year = int(pub_year)
            except ValueError:
                pass

        # Journal/venue
        journal = bib.get("venue", bib.get("journal", "Unknown"))

        # Google Scholar doesn't have DOI directly, but may have URL
        url = result.get("pub_url", result.get("eprint_url", ""))

        # Citations
        citations = result.get("num_citations", 0)

        # Use Google Scholar ID as pmid (prefixed to distinguish)
        scholar_id = result.get("author_pub_id", result.get("url_scholarbib", ""))
        if not scholar_id:
            # Generate from title hash
            scholar_id = f"gs_{hash(title) % 100000000}"

        return ResearchPaper(
            pmid=scholar_id,  # Using pmid field for scholar ID
            title=title,
            authors=authors[:10],
            abstract=abstract,
            year=year,
            journal=journal,
            doi=url,  # Store URL in doi field
            citations=citations,
            similarity=0.0,
        )

    async def search_by_keywords(
        self,
        keywords: list[str],
        year_min: int = 2020,
        max_results: int = 50,
    ) -> list[ResearchPaper]:
        """
        Search by keyword list.

        Args:
            keywords: List of keywords to search
            year_min: Minimum publication year
            max_results: Maximum results

        Returns:
            List of ResearchPaper objects
        """
        # Join keywords with AND for more specific results
        query = " ".join(keywords[:5])
        return await self.search(query, year_min, max_results)
