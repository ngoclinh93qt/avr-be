"""
Agent data models and schemas.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResearchPaper:
    """A single research paper from literature search."""

    pmid: str
    title: str
    authors: list[str]
    abstract: str
    year: int
    journal: str
    doi: Optional[str] = None
    citations: int = 0
    similarity: float = 0.0  # Cosine similarity to query (0-1)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors[:3],  # First 3 authors
            "abstract": self.abstract[:300] + "..." if len(self.abstract) > 300 else self.abstract,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "citations": self.citations,
            "similarity": round(self.similarity, 3),
        }

    def citation_text(self) -> str:
        """Format as citation text."""
        authors_str = ", ".join(self.authors[:2])
        if len(self.authors) > 2:
            authors_str += " et al."
        return f"{authors_str} ({self.year}). {self.title}. {self.journal}."


@dataclass
class SearchQuery:
    """Search query configuration."""

    keywords: list[str]
    title_only: bool = False
    year_min: int = 2020
    year_max: int = 2025
    max_results: int = 500


@dataclass
class RankingResult:
    """Result of paper ranking operation."""

    papers: list[ResearchPaper]
    total_found: int
    total_ranked: int
    avg_similarity: float
    processing_time_seconds: float
