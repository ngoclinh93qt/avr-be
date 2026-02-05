"""
RAG Engine for finding similar research papers using Qdrant vector database.

The engine uses lazy initialization to avoid startup failures when Qdrant is not available.
"""

from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.config import get_settings

settings = get_settings()

# Collection configuration
COLLECTION_NAME = "pubmed_abstracts"
EMBEDDING_DIM = 768  # PubMedBERT dimension


class RAGEngine:
    """
    RAG Engine with lazy initialization.
    
    Components are only initialized when first accessed to avoid startup failures.
    """
    
    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._embed_model = None
        self._index = None
        self._initialized = False
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )
        return self._client
    
    @property
    def embed_model(self):
        """Get or create embedding model."""
        if self._embed_model is None:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            self._embed_model = HuggingFaceEmbedding(
                model_name="microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"
            )
        return self._embed_model
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
    
    def _ensure_initialized(self):
        """Ensure the RAG engine is fully initialized."""
        if not self._initialized:
            from llama_index.core import VectorStoreIndex, Settings
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            
            # Ensure collection exists
            self._ensure_collection_exists()
            
            # Set global embedding model
            Settings.embed_model = self.embed_model
            
            # Create vector store and index
            self._vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=COLLECTION_NAME
            )
            self._index = VectorStoreIndex.from_vector_store(self._vector_store)
            self._initialized = True
    
    async def find_similar_papers(
        self,
        abstract: str,
        top_k: int = 20,
        year_filter: int = None
    ) -> list[dict]:
        """
        Find similar papers to the given abstract.
        
        Args:
            abstract: The research abstract to find similar papers for.
            top_k: Number of similar papers to return.
            year_filter: Optional filter for minimum publication year.
        
        Returns:
            List of similar papers with title, abstract, year, pmid, and similarity score.
        """
        try:
            self._ensure_initialized()
            
            retriever = self._index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(abstract)
            
            return [
                {
                    "title": n.metadata.get("title", ""),
                    "abstract": n.text,
                    "year": n.metadata.get("year"),
                    "pmid": n.metadata.get("pmid"),
                    "similarity": n.score
                }
                for n in nodes
            ]
        except Exception as e:
            # If RAG fails, return empty list so the pipeline can continue
            print(f"RAG Engine error: {e}")
            return []
    
    def health_check(self) -> dict:
        """Check if the RAG engine is healthy."""
        try:
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "qdrant_connected": True,
                "collections": [c.name for c in collections.collections]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "qdrant_connected": False,
                "error": str(e)
            }


# Global instance (lazy initialization)
rag_engine = RAGEngine()
