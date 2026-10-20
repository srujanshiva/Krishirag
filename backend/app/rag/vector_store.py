"""Qdrant vector store interface for agricultural knowledge retrieval."""

from typing import Any, Dict, List, Optional
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from backend.app.config import settings
from backend.app.rag.chunker import TextChunk


class QdrantVectorStore:
    """Interface to Qdrant vector database for indexing and semantic search."""

    def __init__(self, url: Optional[str] = None, collection_name: Optional[str] = None):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = QdrantClient(url=self.url)
        self.vector_dim = 384

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        try:
            if not self.client.collection_exists(self.collection_name):
                logger.info(f"Creating Qdrant collection: {self.collection_name} (dim={self.vector_dim})")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise

    def count(self) -> int:
        """Return the total number of points in the collection."""
        try:
            if not self.client.collection_exists(self.collection_name):
                return 0
            return self.client.count(collection_name=self.collection_name).count
        except Exception as e:
            logger.warning(f"Could not count points in collection {self.collection_name}: {e}")
            return 0

    def upsert_chunks(
        self,
        chunks: List[TextChunk],
        vectors: List[List[float]],
        document_metadata: Dict[str, Any],
    ) -> int:
        """Batch upsert text chunks with vectors and metadata into Qdrant."""
        self.ensure_collection()
        if not chunks:
            return 0

        points: List[PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "vector_id": chunk.vector_id,
                "document_id": str(document_metadata.get("id")),
                "title": document_metadata.get("title", ""),
                "publisher": document_metadata.get("publisher", ""),
                "source_url": document_metadata.get("source_url", ""),
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "license_note": document_metadata.get("license_note", ""),
            }

            points.append(
                PointStruct(
                    id=chunk.vector_id,
                    vector=vector,
                    payload=payload,
                )
            )

        # Upsert in batches of 100
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True,
            )
            total_upserted += len(batch)

        logger.info(f"Upserted {total_upserted} vectors into {self.collection_name}")
        return total_upserted

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
    ) -> List[ScoredPoint]:
        """Search nearest neighbor vectors using Cosine similarity."""
        self.ensure_collection()
        try:
            threshold = score_threshold if score_threshold > 0.0 else None
            if hasattr(self.client, "query_points"):
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=threshold,
                )
                return results.points
            elif hasattr(self.client, "search"):
                return self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=threshold,
                )
            return []
        except Exception as e:
            logger.error(f"Error during vector search in {self.collection_name}: {e}")
            return []

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all points associated with a specific document."""
        if not self.client.collection_exists(self.collection_name):
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            ),
        )
