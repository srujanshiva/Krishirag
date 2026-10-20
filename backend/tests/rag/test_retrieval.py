"""Tests for AgriculturalRetriever."""

import uuid
import pytest
from backend.app.rag.chunker import TextChunk
from backend.app.rag.embedder import FastEmbedder
from backend.app.rag.retriever import AgriculturalRetriever, RetrievedChunk
from backend.app.rag.vector_store import QdrantVectorStore


def test_retriever_semantic_search():
    """Verify retriever embeds query and returns structured RetrievedChunk instances."""
    test_collection = f"test_ret_{uuid.uuid4().hex[:8]}"
    vector_store = QdrantVectorStore(collection_name=test_collection)
    embedder = FastEmbedder()
    retriever = AgriculturalRetriever(embedder=embedder, vector_store=vector_store)

    try:
        # Seed test chunks
        chunk1 = TextChunk(
            chunk_index=0,
            chunk_text="Nitrogen recommendation for short duration rice is 120 kg per hectare.",
            vector_id=str(uuid.uuid4()),
            page_number=10,
            section="Nutrient Management",
        )
        chunk2 = TextChunk(
            chunk_index=1,
            chunk_text="Brown planthopper causes drying of leaves known as hopper burn in paddy.",
            vector_id=str(uuid.uuid4()),
            page_number=22,
            section="Pest Surveillance",
        )

        vectors = embedder.embed_documents([chunk1.chunk_text, chunk2.chunk_text])
        metadata = {
            "id": str(uuid.uuid4()),
            "title": "TNAU Agronomy Manual",
            "publisher": "TNAU",
            "source_url": "https://tnagriculture.in/manual.pdf",
        }
        vector_store.upsert_chunks([chunk1, chunk2], vectors, metadata)

        # Retrieve with query closely matching chunk 1
        results = retriever.retrieve("nitrogen fertilizer requirement for rice", top_k=2)

        assert len(results) >= 1
        top = results[0]
        assert isinstance(top, RetrievedChunk)
        assert top.chunk_id == chunk1.vector_id
        assert top.document_title == "TNAU Agronomy Manual"
        assert top.page_number == 10
        assert top.score > 0.40

    finally:
        try:
            vector_store.client.delete_collection(test_collection)
        except Exception:
            pass


def test_retriever_empty_collection():
    """Verify retriever returns empty list when collection has no matching vectors."""
    test_collection = f"test_empty_{uuid.uuid4().hex[:8]}"
    vector_store = QdrantVectorStore(collection_name=test_collection)
    vector_store.ensure_collection()
    retriever = AgriculturalRetriever(vector_store=vector_store)

    try:
        results = retriever.retrieve("any agricultural question", top_k=5)
        assert results == []
    finally:
        try:
            vector_store.client.delete_collection(test_collection)
        except Exception:
            pass
