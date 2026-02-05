"""
PubMed E-utilities API Client.

Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import asyncio
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from app.agents.schemas import ResearchPaper


class PubMedClient:
    """Client for PubMed E-utilities API."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    RATE_LIMIT_DELAY = 0.34  # ~3 requests per second (NCBI limit without API key)

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PubMed client.

        Args:
            api_key: Optional NCBI API key (increases rate limit to 10 req/sec)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        if api_key:
            self.RATE_LIMIT_DELAY = 0.1  # 10 requests per second with API key

    async def search_titles(
        self,
        keywords: list[str],
        year_min: int = 2020,
        year_max: int = 2025,
        max_results: int = 500,
        query: str | None = None,
    ) -> list[str]:
        """
        Search PubMed by keywords or pre-built query.

        Args:
            keywords: List of keywords (used if query is None)
            year_min: Minimum publication year
            year_max: Maximum publication year
            max_results: Maximum number of results
            query: Pre-built PubMed query string (overrides keywords)

        Returns:
            List of PMIDs
        """
        if query is None:
            # Fallback: simple AND query on first 3 keywords
            query_parts = [f"{kw}[Title/Abstract]" for kw in keywords[:3]]
            query = " AND ".join(query_parts)

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "datetype": "pdat",
            "mindate": f"{year_min}/01/01",
            "maxdate": f"{year_max}/12/31",
            "sort": "relevance",
            "retmode": "json",
        }

        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.BASE_URL}/esearch.fcgi"

        await asyncio.sleep(self.RATE_LIMIT_DELAY)  # Rate limiting
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])

        return pmids

    async def fetch_abstracts_batch(
        self, pmids: list[str], batch_size: int = 200
    ) -> list[ResearchPaper]:
        """
        Fetch full paper details including abstracts.

        Args:
            pmids: List of PubMed IDs
            batch_size: Number of papers to fetch per request

        Returns:
            List of ResearchPaper objects
        """
        all_papers = []

        # Process in batches to avoid URL length limits
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            papers = await self._fetch_batch(batch)
            all_papers.extend(papers)

        return all_papers

    async def _fetch_batch(self, pmids: list[str]) -> list[ResearchPaper]:
        """Fetch a single batch of papers."""
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }

        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.BASE_URL}/efetch.fcgi"

        await asyncio.sleep(self.RATE_LIMIT_DELAY)  # Rate limiting
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        return self._parse_xml(response.text)

    def _parse_xml(self, xml_text: str) -> list[ResearchPaper]:
        """Parse PubMed XML response into ResearchPaper objects."""
        papers = []

        try:
            root = ET.fromstring(xml_text)
            articles = root.findall(".//PubmedArticle")

            for article in articles:
                try:
                    paper = self._parse_article(article)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    # Skip malformed articles
                    continue

        except ET.ParseError:
            pass

        return papers

    def _parse_article(self, article: ET.Element) -> Optional[ResearchPaper]:
        """Parse a single PubmedArticle XML element."""
        # PMID
        pmid_elem = article.find(".//PMID")
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text

        # Title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else "No title"

        # Authors
        authors = []
        author_elems = article.findall(".//Author")
        for author in author_elems[:10]:  # Limit to 10 authors
            last = author.find("LastName")
            first = author.find("ForeName")
            if last is not None:
                name = last.text
                if first is not None:
                    name = f"{last.text} {first.text[0]}"
                authors.append(name)

        # Abstract
        abstract_texts = article.findall(".//AbstractText")
        abstract_parts = []
        for text_elem in abstract_texts:
            label = text_elem.get("Label", "")
            text = text_elem.text or ""
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"

        # Year
        year_elem = article.find(".//PubDate/Year")
        year = int(year_elem.text) if year_elem is not None else 2020

        # Journal
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else "Unknown"

        # DOI
        doi = None
        doi_elem = article.find(".//ArticleId[@IdType='doi']")
        if doi_elem is not None:
            doi = doi_elem.text

        # Citations (not available in standard API, set to 0)
        citations = 0

        return ResearchPaper(
            pmid=pmid,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            journal=journal,
            doi=doi,
            citations=citations,
            similarity=0.0,  # Will be set by semantic ranker
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
