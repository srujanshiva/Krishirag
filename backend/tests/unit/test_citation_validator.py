"""Unit tests for CitationValidator."""

import uuid
from backend.app.citations.validator import CitationValidator
from backend.app.rag.retriever import RetrievedChunk


def test_validator_preserves_valid_citations():
    """Verify legitimate retrieved chunk IDs are retained and formatted."""
    chunk_id1 = str(uuid.uuid4())
    chunk1 = RetrievedChunk(
        chunk_id=chunk_id1,
        document_title="TNAU Crop Guide",
        publisher="TNAU",
        source_url="https://tnagriculture.in/guide.pdf",
        page_number=14,
        section="Nutrient Management",
        chunk_text="Apply 120 kg/ha nitrogen in split doses: 50% basal, 25% tillering, 25% panicle initiation.",
        score=0.88,
    )

    raw_answer = f"For short-duration rice, apply 120 kg/ha nitrogen [{chunk_id1}]."
    validated = CitationValidator.validate(raw_answer, [chunk1])

    assert validated.valid_count == 1
    assert validated.stripped_count == 0
    assert chunk_id1 in validated.cleaned_answer
    assert len(validated.citations) == 1
    assert validated.citations[0].chunk_id == chunk_id1
    assert validated.citations[0].document_title == "TNAU Crop Guide"
    assert validated.citations[0].page_number == 14
    assert "120 kg/ha nitrogen" in validated.citations[0].excerpt


def test_validator_strips_hallucinated_citations():
    """Verify model-invented citation IDs not in retrieved chunks are stripped cleanly."""
    valid_id = str(uuid.uuid4())
    fake_id = str(uuid.uuid4())

    valid_chunk = RetrievedChunk(
        chunk_id=valid_id,
        document_title="ICAR Rice Handbook",
        publisher="ICAR",
        source_url=None,
        page_number=5,
        section="Soil Requirements",
        chunk_text="Rice is ideally cultivated on clay loam soils.",
        score=0.75,
    )

    raw_answer = (
        f"Rice thrives on clay loam soils [{valid_id}]. "
        f"You should also add unverified chemical X [{fake_id}] for growth."
    )

    validated = CitationValidator.validate(raw_answer, [valid_chunk])

    assert validated.valid_count == 1
    assert validated.stripped_count == 1
    assert valid_id in validated.cleaned_answer
    assert fake_id not in validated.cleaned_answer
    # Assert citations list only contains the legitimate retrieved chunk
    assert [c.chunk_id for c in validated.citations] == [valid_id]


def test_validator_excerpt_truncation():
    """Verify excerpts are safely capped at 300 characters."""
    chunk_id = str(uuid.uuid4())
    long_text = "Agronomy " * 50  # ~450 characters
    chunk = RetrievedChunk(
        chunk_id=chunk_id,
        document_title="Manual",
        publisher="SAU",
        source_url=None,
        page_number=1,
        section="Intro",
        chunk_text=long_text,
        score=0.9,
    )

    raw_answer = f"Reference details [{chunk_id}]."
    validated = CitationValidator.validate(raw_answer, [chunk])

    assert len(validated.citations) == 1
    excerpt = validated.citations[0].excerpt
    assert len(excerpt) <= 305  # 300 + "..."
    assert excerpt.endswith("...")
