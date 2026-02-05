"""
Test the Deep Research Agent.

Usage:
    python examples/test_research_agent.py
"""

import asyncio

from app.agents.research.agent import ResearchAgent


async def test_research():
    """Test deep research agent with sample abstract."""

    abstract = """
    This study investigates the use of machine learning techniques,
    specifically random forests and neural networks, for predicting
    30-day mortality in ICU patients with cardiovascular disease.
    We analyze data from 5000 patients across 10 hospitals.
    """

    print("🔬 Deep Research Agent - Test\n")
    print(f"Abstract: {abstract.strip()}\n")
    print("=" * 60)

    agent = ResearchAgent()

    def progress_callback(message: str, percent: int):
        print(f"[{percent}%] {message}")

    try:
        result = await agent.search(
            abstract=abstract,
            max_papers=10,  # Get top 10 papers
            title_search_limit=100,  # Search 100 titles (faster for testing)
            on_progress=progress_callback,
        )

        print("\n" + "=" * 60)
        print("📊 RESULTS")
        print("=" * 60)
        print(f"\nTotal papers found: {result.total_found}")
        print(f"Papers ranked: {result.total_ranked}")
        print(f"Average similarity: {result.avg_similarity:.3f}")
        print(f"Processing time: {result.processing_time_seconds:.2f}s")

        print(f"\n📄 Top {len(result.papers)} Papers:\n")
        for i, paper in enumerate(result.papers, 1):
            print(f"{i}. {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:3])}")
            print(f"   Year: {paper.year} | Journal: {paper.journal}")
            print(f"   Similarity: {paper.similarity:.3f}")
            print(f"   PMID: {paper.pmid}")
            print(f"   Abstract: {paper.abstract[:150]}...")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")

    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(test_research())
