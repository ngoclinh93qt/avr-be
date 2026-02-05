"""
Embedding service for semantic similarity calculations.

Uses lazy initialization to avoid loading the model until first use.
"""

from typing import Optional
import numpy as np


class EmbeddingService:
    """
    Embedding service with lazy model loading.
    
    The model is only loaded when first used to speed up application startup.
    """
    
    def __init__(self):
        self._model = None
        self._cache = {}
    
    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"
            )
        return self._model
    
    def embed(self, text: str) -> np.ndarray:
        """Get embedding for text, with caching."""
        if text not in self._cache:
            self._cache[text] = self.model.encode(text)
        return self._cache[text]
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        try:
            emb1, emb2 = self.embed(text1), self.embed(text2)
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        except Exception as e:
            print(f"Embedding error: {e}")
            return 0.0


# Global instance (lazy initialization)
embedding_service = EmbeddingService()
