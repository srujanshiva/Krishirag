"""Integration tests for QdrantVectorStore."""

import uuid
import pytest
from backend.app.rag.chunker import TextChunk
from backend.app.rag.vector_store import QdrantVectorStore


def test_qdrant_collection_lifecycle():
    """Verify Qdrant collection creation, upsert, count, search, and deletion."""
    test_collection = f"test_col_{uuid.uuid4().hex[:8]}"
    store = QdrantVectorStore(collection_name=test_collection)

    try:
        # 1. Ensure collection
        store.ensure_collection()
        assert store.count() == 0

        # 2. Prepare chunks and dummy 384-d vectors
        doc_id = uuid.uuid4()
        chunk1 = TextChunk(
            chunk_index=0,
            chunk_text="Rice blast disease is caused by Magnaporthe oryzae.",
            vector_id=str(uuid.uuid4()),
            page_number=12,
            section="Disease Management",
        )
        chunk2 = TextChunk(
            chunk_index=1,
            chunk_text="Apply Tricyclazole 75 WP at 500 g/ha for blast control.",
            vector_id=str(uuid.uuid4()),
            page_number=13,
            section="Chemical Control",
        )

        vec1 = [1.0] + [0.0] * 383
        vec2 = [0.0, 1.0] + [0.0] * 382

        metadata = {
            "id": str(doc_id),
            "title": "TNAU Rice Guide",
            "publisher": "TNAU",
            "source_url": "https://tnagriculture.in/test.pdf",
        }

        # 3. Upsert
        count_upserted = store.upsert_chunks([chunk1, chunk2], [vec1, vec2], metadata)
        assert count_upserted == 2
        assert store.count() == 2

        # 4. Search
        search_results = store.search(query_vector=vec1, limit=2)
        assert len(search_results) == 2
        top_match = search_results[0]
        assert top_match.id == chunk1.vector_id
        assert top_match.payload["title"] == "TNAU Rice Guide"
        assert top_match.payload["page_number"] == 12

        # 5. Delete by document ID
        store.delete_by_document_id(str(doc_id))
        # Allow brief sync
        assert store.count() == 0

    finally:
        # Cleanup test collection
        try:
            store.client.delete_collection(test_collection)
        except Exception:
            pass
