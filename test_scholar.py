import asyncio
from app.agents.research.scholar_client import ScholarClient

async def test_scholar():
    print("Initializing Scholar Client...")
    client = ScholarClient()
    
    print("Searching for 'machine learning'...")
    try:
        results = await client.search("machine learning", max_results=3)
        print(f"Found {len(results)} results.")
        for i, paper in enumerate(results):
            print(f"\n{i+1}. Title: {paper.title}")
            print(f"   Authors: {', '.join(paper.authors)}")
            print(f"   Year: {paper.year}")
            print(f"   Citations: {paper.citations}")
            
        if results:
            print("\nScholar Client Verification SUCCESS")
        else:
            print("\nScholar Client Verification WARNING: No results found, but no error.")
            
    except Exception as e:
        print(f"\nScholar Client Verification FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_scholar())
