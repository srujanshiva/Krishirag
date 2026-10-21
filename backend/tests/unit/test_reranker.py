"""Unit tests for AgriculturalReranker."""

from backend.app.rag.reranker import AgriculturalReranker
from backend.app.rag.retriever import RetrievedChunk


def test_reranker_boosts_exact_dosage_matches():
    """Verify reranker elevates chunks with exact chemical dosage numbers when query asks for dosage."""
    reranker = AgriculturalReranker(default_top_k=2)

    chunk_generic = RetrievedChunk(
        chunk_id="chunk-1",
        document_title="TNAU Crop Guide",
        publisher="TNAU",
        source_url=None,
        page_number=10,
        section="General Overview",
        chunk_text="Rice is an important cereal crop cultivated across Tamil Nadu.",
        score=0.85,  # Higher initial dense score
    )

    chunk_dosage = RetrievedChunk(
        chunk_id="chunk-2",
        document_title="TNAU Crop Guide",
        publisher="TNAU",
        source_url=None,
        page_number=32,
        section="SRI Cultivation",
        chunk_text="For SRI cultivation, the recommended seed rate is 5 kg/ha with 25x25 cm spacing.",
        score=0.80,  # Lower initial dense score
    )

    query = "What is the recommended seed rate and spacing for SRI rice?"
    reranked = reranker.rerank(query, [chunk_generic, chunk_dosage], top_k=2)

    assert len(reranked) == 2
    # The chunk with exact keyword match and dosage numbers should be boosted to rank 1
    assert reranked[0].chunk_id == "chunk-2"
    assert "5 kg/ha" in reranked[0].chunk_text
    assert reranked[0].score > reranked[1].score


def test_reranker_handles_empty_candidates():
    """Verify reranker returns empty list when given no candidates."""
    reranker = AgriculturalReranker()
    assert reranker.rerank("rice blast", []) == []
