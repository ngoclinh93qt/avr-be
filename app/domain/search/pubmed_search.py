"""PubMed search using NCBI E-utilities (free, no API key required)."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_TIMEOUT = 10.0


async def search_pubmed(
    keywords: list[str],
    max_results: int = 5,
    email: Optional[str] = "avr@research.app",  # NCBI recommends including email
) -> dict:
    """
    Search PubMed and return article count + top papers.

    Returns:
        {
            "count": int,
            "papers": [{ title, authors, year, journal, pmid }],
            "keywords_used": [...]
        }
    Fails gracefully — never raises, always returns a valid dict.
    """
    query = " ".join(keywords)
    params_base = {"email": email, "tool": "avr-research-app"}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Step 1: esearch — get count + IDs
            search_resp = await client.get(
                f"{ENTREZ_BASE}/esearch.fcgi",
                params={
                    **params_base,
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                },
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            esr = search_data.get("esearchresult", {})
            count = int(esr.get("count", 0))
            ids = esr.get("idlist", [])

            papers = []
            if ids:
                # Step 2: esummary — get metadata for each ID
                summary_resp = await client.get(
                    f"{ENTREZ_BASE}/esummary.fcgi",
                    params={
                        **params_base,
                        "db": "pubmed",
                        "id": ",".join(ids),
                        "retmode": "json",
                    },
                )
                summary_resp.raise_for_status()
                summary_data = summary_resp.json()
                result_map = summary_data.get("result", {})

                for pmid in ids:
                    doc = result_map.get(pmid)
                    if not doc or not isinstance(doc, dict):
                        continue

                    authors_list = doc.get("authors", [])
                    if authors_list:
                        first = authors_list[0].get("name", "")
                        authors_str = f"{first} et al." if len(authors_list) > 1 else first
                    else:
                        authors_str = "Unknown"

                    pub_date = doc.get("pubdate", "")
                    year = pub_date[:4] if pub_date and len(pub_date) >= 4 else ""

                    papers.append({
                        "title": doc.get("title", "").rstrip("."),
                        "authors": authors_str,
                        "year": year,
                        "journal": doc.get("fulljournalname") or doc.get("source", ""),
                        "pmid": pmid,
                    })

            logger.info("PubMed search: query=%r count=%d papers_fetched=%d", query, count, len(papers))
            return {"count": count, "papers": papers, "keywords_used": keywords}

    except Exception as e:
        logger.warning("PubMed search failed (non-critical): %s", e)
        return {"count": 0, "papers": [], "keywords_used": keywords}


def build_pubmed_keywords(blueprint) -> list[str]:
    """
    Extract search keywords from a ResearchBlueprint.
    Keeps it concise — PubMed works better with focused queries.
    """
    parts = []

    # Intervention / exposure
    if blueprint.intervention_or_exposure:
        parts.append(blueprint.intervention_or_exposure)

    # Comparator
    if blueprint.comparator:
        parts.append(blueprint.comparator)

    # Primary outcome
    if blueprint.primary_outcome:
        parts.append(blueprint.primary_outcome)

    # Population (trimmed to avoid over-specifying)
    if blueprint.population and len(blueprint.population) < 60:
        parts.append(blueprint.population)

    return parts[:4]  # max 4 terms for a tight query
