"""
Semantic similarity ranker using sentence embeddings.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.agents.schemas import ResearchPaper


class SemanticRanker:
    """Rank papers by semantic similarity to query."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize semantic ranker.

        Args:
            model_name: SentenceTransformer model name
                - all-MiniLM-L6-v2: Fast, high discrimination (default)
                - all-mpnet-base-v2: Better quality, 768 dims
        """
        self.model = SentenceTransformer(model_name)

    def rank_by_title_similarity(
        self,
        query_abstract: str,
        papers: list[ResearchPaper],
        top_k: int = 50,
    ) -> list[ResearchPaper]:
        """
        Rank papers by title similarity (fast filtering).

        Args:
            query_abstract: User's research abstract
            papers: List of papers to rank
            top_k: Number of top papers to return

        Returns:
            Top K papers sorted by title similarity
        """
        if not papers:
            return []

        # Embed query
        query_embedding = self.model.encode([query_abstract], show_progress_bar=False)

        # Embed paper titles (fast)
        titles = [p.title for p in papers]
        title_embeddings = self.model.encode(titles, show_progress_bar=False)

        # Cosine similarity
        similarities = self._cosine_similarity(query_embedding, title_embeddings)

        # Sort by similarity and take top K
        sorted_indices = np.argsort(similarities)[::-1][:top_k]

        # Create new list with similarity scores
        ranked_papers = []
        for idx in sorted_indices:
            paper = papers[idx]
            paper.similarity = float(similarities[idx])
            ranked_papers.append(paper)

        return ranked_papers

    def rank_by_abstract_similarity(
        self,
        query_abstract: str,
        papers: list[ResearchPaper],
        top_k: int = 20,
    ) -> list[ResearchPaper]:
        """
        Rank papers by abstract similarity (thorough ranking).

        Args:
            query_abstract: User's research abstract
            papers: List of papers to rank
            top_k: Number of top papers to return

        Returns:
            Top K papers sorted by abstract similarity
        """
        if not papers:
            return []

        # Embed query
        query_embedding = self.model.encode([query_abstract], show_progress_bar=False)

        # Embed paper abstracts
        abstracts = [p.abstract for p in papers]
        abstract_embeddings = self.model.encode(abstracts, show_progress_bar=False)

        # Cosine similarity
        similarities = self._cosine_similarity(query_embedding, abstract_embeddings)

        # Sort by similarity and take top K
        sorted_indices = np.argsort(similarities)[::-1][:top_k]

        # Create new list with similarity scores
        ranked_papers = []
        for idx in sorted_indices:
            paper = papers[idx]
            paper.similarity = float(similarities[idx])
            ranked_papers.append(paper)

        return ranked_papers

    def _cosine_similarity(
        self, query_embedding: np.ndarray, document_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Shape (1, embedding_dim)
            document_embeddings: Shape (n_docs, embedding_dim)

        Returns:
            Similarity scores: Shape (n_docs,)
        """
        # Normalize vectors
        query_norm = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        docs_norm = document_embeddings / np.linalg.norm(
            document_embeddings, axis=1, keepdims=True
        )

        # Dot product = cosine similarity for normalized vectors
        similarities = np.dot(query_norm, docs_norm.T)[0]

        return similarities

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text."""
        return self.model.encode([text], show_progress_bar=False)[0]
