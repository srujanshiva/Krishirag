"""Agricultural knowledge retriever querying Qdrant vector store."""

from dataclasses import dataclass
from typing import Any, List, Optional
from loguru import logger

from backend.app.rag.embedder import FastEmbedder
from backend.app.rag.vector_store import QdrantVectorStore


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_title: str
    publisher: str
    source_url: Optional[str]
    page_number: Optional[int]
    section: Optional[str]
    chunk_text: str
    score: float


class AgriculturalRetriever:
    """Retrieves relevant agricultural knowledge passages using semantic similarity."""

    def __init__(
        self,
        embedder: Optional[FastEmbedder] = None,
        vector_store: Optional[QdrantVectorStore] = None,
        reranker: Optional[Any] = None,
        default_top_k: int = 5,
        default_score_threshold: float = 0.35,
    ):
        self.embedder = embedder or FastEmbedder()
        self.vector_store = vector_store or QdrantVectorStore()
        self._reranker = reranker
        self.default_top_k = default_top_k
        self.default_score_threshold = default_score_threshold

    @property
    def reranker(self) -> Any:
        if self._reranker is None:
            from backend.app.rag.reranker import reranker as default_reranker
            self._reranker = default_reranker
        return self._reranker

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Compute query embedding, retrieve candidate pool from Qdrant, and apply neural reranking."""
        k = top_k or self.default_top_k
        threshold = score_threshold if score_threshold is not None else self.default_score_threshold

        try:
            query_vector = self.embedder.embed_query(query)
            # Retrieve candidate pool from vector store meeting minimum threshold
            fetch_limit = max(k * 2, 10)
            scored_points = self.vector_store.search(
                query_vector=query_vector,
                limit=fetch_limit,
                score_threshold=threshold,
            )

            raw_chunks: List[RetrievedChunk] = []
            for point in scored_points:
                payload = point.payload or {}
                raw_chunks.append(
                    RetrievedChunk(
                        chunk_id=str(point.id),
                        document_title=payload.get("title", "Agricultural Advisory Document"),
                        publisher=payload.get("publisher", "Government / Agricultural University"),
                        source_url=payload.get("source_url"),
                        page_number=payload.get("page_number"),
                        section=payload.get("section"),
                        chunk_text=payload.get("chunk_text", ""),
                        score=float(point.score),
                    )
                )

            # Apply neural cross-encoder reranker
            if self.reranker and raw_chunks:
                reranked_chunks = self.reranker.rerank(query, raw_chunks, top_k=k)
                chunks = [c for c in reranked_chunks if c.score >= threshold]
            else:
                chunks = raw_chunks[:k]

            logger.info(f"Retrieved and reranked {len(chunks)} evidence chunks for query: '{query[:60]}...'")
            return chunks

        except Exception as e:
            logger.error(f"Error during retrieval for query '{query[:60]}...': {e}")
            return []


# Default singleton instance
retriever = AgriculturalRetriever()
