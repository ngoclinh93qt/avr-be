#!/usr/bin/env python3
"""
Script to seed journals into ChromaDB from journals_source.json.

Usage:
    python -m app.scripts.seed_journals
    # or
    python app/scripts/seed_journals.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Seed journals into ChromaDB."""
    from app.domain.search.journal_search import (
        add_journals_batch,
        get_collection_stats,
        clear_collection,
    )

    # Load journals from JSON
    journals_file = Path(__file__).parent.parent / "data" / "journals_source.json"

    if not journals_file.exists():
        print(f"Error: {journals_file} not found")
        sys.exit(1)

    with open(journals_file, "r", encoding="utf-8") as f:
        journals = json.load(f)

    print(f"Loaded {len(journals)} journals from {journals_file}")

    # Check current state
    stats = get_collection_stats()
    print(f"Current collection: {stats}")

    # Ask for confirmation if collection not empty
    if stats.get("total_journals", 0) > 0:
        response = input("Collection not empty. Clear and reseed? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)
        clear_collection()
        print("Collection cleared.")

    # Seed journals
    print("Seeding journals...")
    count = add_journals_batch(journals)
    print(f"Added {count} journals to ChromaDB")

    # Verify
    stats = get_collection_stats()
    print(f"Final collection stats: {stats}")

    # Test search
    print("\nTesting search...")
    from app.domain.search.journal_search import search_journals

    test_queries = [
        "pediatric surgery appendicitis laparoscopic",
        "cardiac intervention stent",
        "systematic review meta-analysis",
    ]

    for query in test_queries:
        results = search_journals(query, top_k=3)
        print(f"\nQuery: '{query}'")
        for r in results:
            print(f"  - {r['name']} (score: {r['similarity_score']:.3f})")


if __name__ == "__main__":
    main()
