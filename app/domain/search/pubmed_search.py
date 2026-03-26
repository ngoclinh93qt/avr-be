"""PubMed search using NCBI E-utilities (free, no API key required)."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_TIMEOUT = 10.0


async def search_pubmed(
    query: str,
    max_results: int = 20,
    email: Optional[str] = "avr@research.app",  # NCBI recommends including email
) -> dict:
    """
    Search PubMed and return article count + top papers.

    Returns:
        {
            "count": int,
            "papers": [{ title, authors, year, journal, pmid }],
            "query_used": str
        }
    Fails gracefully — never raises, always returns a valid dict.
    """
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
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })

            logger.info("PubMed search: query=%r count=%d papers_fetched=%d", query, count, len(papers))
            return {"count": count, "papers": papers, "query_used": query}

    except Exception as e:
        logger.warning("PubMed search failed (non-critical): %s", e)
        return {"count": 0, "papers": [], "query_used": query}


async def build_pubmed_query(blueprint, llm) -> str:
    """
    Extract search keywords from a ResearchBlueprint using LLM.
    Ensures broad but relevant [tiab] tags in English.
    """
    try:
        from app.llm.prompts.pubmed_query import get_pubmed_query_prompt, SYSTEM_PROMPT
        prompt = get_pubmed_query_prompt(blueprint)
        
        response = await llm.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2, # Keep it strictly compliant
            max_tokens=200,
        )
        
        query = response.content.strip()
        # Clean up if LLM outputs markdown
        if query.startswith("```"):
            query = "\n".join(query.split("\n")[1:-1]).strip()
            
        # Ensure it has something
        if len(query) < 5:
            raise ValueError("Query string too short")
            
        return query
    except Exception as e:
        logger.error("Failed to generate PubMed query with LLM: %s. Using simple fallback.", e)
        # Fallback to basic english/vietnamese join without [tiab] if LLM completely burns down
        parts = []
        if blueprint.intervention_or_exposure: parts.append(blueprint.intervention_or_exposure)
        if blueprint.primary_outcome: parts.append(blueprint.primary_outcome)
        if blueprint.population: parts.append(blueprint.population)
        return " AND ".join(parts[:3])
