"""Unit tests for FastEmbedder wrapper."""

import pytest
from backend.app.rag.embedder import FastEmbedder


def test_embedder_dimension():
    """Verify FastEmbed model produces 384-dimensional dense vectors."""
    embedder = FastEmbedder()
    assert embedder.dimension == 384

    query_vec = embedder.embed_query("Nitrogen fertilizer application rate for paddy")
    assert isinstance(query_vec, list)
    assert len(query_vec) == 384
    assert all(isinstance(x, float) for x in query_vec)


def test_embedder_batch():
    """Verify batch document embedding preserves order and length."""
    embedder = FastEmbedder()
    docs = [
        "Transplanted rice requires continuous submergence during vegetative phase.",
        "Brown planthopper causes hopper burn symptoms in dense paddy fields.",
        "Zinc deficiency in rice is corrected by applying 25 kg zinc sulphate per hectare.",
    ]
    vectors = embedder.embed_documents(docs)
    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 384


def test_embedder_empty_input():
    """Verify empty input returns empty list."""
    embedder = FastEmbedder()
    assert embedder.embed_documents([]) == []
