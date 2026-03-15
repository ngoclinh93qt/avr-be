"""Journal search using ChromaDB vector search.

This module implements R-08: Journal search via ChromaDB
using sentence-transformers for embeddings.
"""

import os
from typing import Optional
from pathlib import Path

from app.config import get_settings

# Lazy imports to avoid loading heavy libraries on startup
_chroma_client = None
_collection = None
_embedding_model = None


def get_chroma_client():
    """Get or create ChromaDB client."""
    global _chroma_client

    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings

        settings = get_settings()
        persist_dir = settings.chroma_db_path or "./app/data/chroma_journals"

        # Ensure directory exists
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

    return _chroma_client


def get_embedding_model():
    """Get or create embedding model."""
    global _embedding_model

    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        model_name = settings.embedding_model or "all-MiniLM-L6-v2"

        _embedding_model = SentenceTransformer(model_name)

    return _embedding_model


def get_journal_collection():
    """Get or create journals collection."""
    global _collection

    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name="journals",
            metadata={"description": "Medical journals for matching"}
        )

    return _collection


def search_journals(
    query: str,
    specialty: Optional[str] = None,
    top_k: int = 5,
    min_score: float = 0.3
) -> list[dict]:
    """
    Search for matching journals using vector similarity.

    Args:
        query: Search query (abstract text or keywords)
        specialty: Optional specialty filter
        top_k: Number of results to return
        min_score: Minimum similarity score

    Returns:
        List of matching journals with scores
    """
    try:
        collection = get_journal_collection()
        model = get_embedding_model()

        # Generate query embedding
        query_embedding = model.encode(query).tolist()

        # Build where filter
        where_filter = None
        if specialty:
            where_filter = {"specialty": specialty}

        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Process results
        journals = []
        if results and results["ids"] and results["ids"][0]:
            for i, journal_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0
                # Chroma uses L2 distance by default, convert to similarity
                similarity = 1 / (1 + distance)

                if similarity >= min_score:
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    journals.append({
                        "journal_id": journal_id,
                        "name": metadata.get("name", ""),
                        "issn": metadata.get("issn"),
                        "impact_factor": metadata.get("impact_factor"),
                        "specialty": metadata.get("specialty"),
                        "publisher": metadata.get("publisher"),
                        "similarity_score": round(similarity, 3),
                        "description": results["documents"][0][i] if results["documents"] else "",
                    })

        return journals

    except Exception as e:
        # Return empty list on error, don't crash
        print(f"Journal search error: {e}")
        return []


def get_journal_by_id(journal_id: str) -> Optional[dict]:
    """
    Get a specific journal by ID.

    Args:
        journal_id: Journal ID

    Returns:
        Journal metadata or None
    """
    try:
        collection = get_journal_collection()
        result = collection.get(
            ids=[journal_id],
            include=["documents", "metadatas"]
        )

        if result and result["ids"]:
            metadata = result["metadatas"][0] if result["metadatas"] else {}
            return {
                "journal_id": journal_id,
                "name": metadata.get("name", ""),
                "issn": metadata.get("issn"),
                "impact_factor": metadata.get("impact_factor"),
                "specialty": metadata.get("specialty"),
                "publisher": metadata.get("publisher"),
                "word_limits": metadata.get("word_limits"),
                "section_requirements": metadata.get("section_requirements", []),
                "author_guidelines_url": metadata.get("author_guidelines_url"),
                "description": result["documents"][0] if result["documents"] else "",
            }
        return None

    except Exception as e:
        print(f"Get journal error: {e}")
        return None


def add_journal(
    journal_id: str,
    name: str,
    description: str,
    metadata: Optional[dict] = None
) -> bool:
    """
    Add a journal to the collection.

    Args:
        journal_id: Unique journal ID
        name: Journal name
        description: Journal description/scope
        metadata: Additional metadata

    Returns:
        True if successful
    """
    try:
        collection = get_journal_collection()
        model = get_embedding_model()

        # Generate embedding for description
        embedding = model.encode(description).tolist()

        # Build metadata
        meta = metadata or {}
        meta["name"] = name

        collection.add(
            ids=[journal_id],
            embeddings=[embedding],
            documents=[description],
            metadatas=[meta]
        )

        return True

    except Exception as e:
        print(f"Add journal error: {e}")
        return False


def add_journals_batch(journals: list[dict]) -> int:
    """
    Add multiple journals in batch.

    Args:
        journals: List of journal dicts with id, name, description, metadata

    Returns:
        Number of journals added
    """
    try:
        collection = get_journal_collection()
        model = get_embedding_model()

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for journal in journals:
            journal_id = journal.get("id") or journal.get("journal_id")
            name = journal.get("name", "")
            description = journal.get("description", "")

            if not journal_id or not description:
                continue

            # Generate embedding
            embedding = model.encode(description).tolist()

            # Build metadata
            meta = {
                "name": name,
                "issn": journal.get("issn"),
                "impact_factor": journal.get("impact_factor"),
                "specialty": journal.get("specialty"),
                "publisher": journal.get("publisher"),
                "word_limits": journal.get("word_limits"),
                "section_requirements": journal.get("section_requirements"),
                "author_guidelines_url": journal.get("author_guidelines_url"),
            }
            # Remove None values
            meta = {k: v for k, v in meta.items() if v is not None}

            ids.append(journal_id)
            embeddings.append(embedding)
            documents.append(description)
            metadatas.append(meta)

        if ids:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

        return len(ids)

    except Exception as e:
        print(f"Batch add error: {e}")
        return 0


def get_collection_stats() -> dict:
    """Get statistics about the journals collection."""
    try:
        collection = get_journal_collection()
        count = collection.count()
        return {
            "total_journals": count,
            "collection_name": "journals",
        }
    except Exception as e:
        return {"error": str(e)}


def clear_collection() -> bool:
    """Clear all journals from collection. Use with caution."""
    try:
        client = get_chroma_client()
        client.delete_collection("journals")
        global _collection
        _collection = None
        return True
    except Exception as e:
        print(f"Clear collection error: {e}")
        return False
