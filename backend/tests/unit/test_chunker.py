"""Unit tests for DocumentChunker."""

import uuid
import pytest
from backend.app.rag.chunker import DocumentChunker, TextChunk


def test_chunker_basic_splitting():
    """Verify text is split into target word windows with proper overlap."""
    chunker = DocumentChunker(target_words=50, overlap_words=10)
    # Generate 120 words
    words = [f"word{i}" for i in range(120)]
    text = " ".join(words)
    pages = [(1, text)]

    checksum = "dummy-checksum-12345678"
    chunks = chunker.chunk_pages(pages, checksum)

    assert len(chunks) >= 3
    # First chunk should have ~50 words
    assert len(chunks[0].chunk_text.split()) == 50
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1

    # Second chunk should overlap with first chunk
    chunk0_words = chunks[0].chunk_text.split()
    chunk1_words = chunks[1].chunk_text.split()
    # Check that overlap words match
    assert chunk0_words[-10:] == chunk1_words[:10]


def test_chunker_stable_deterministic_id():
    """Verify that vector_id is a deterministic UUID v5."""
    checksum = "97c933318298b249cf74bbb737f66a614687c8f45e4e8353ac4c04e17b2987e2"
    id1 = DocumentChunker.generate_vector_id(checksum, 0)
    id2 = DocumentChunker.generate_vector_id(checksum, 0)
    id3 = DocumentChunker.generate_vector_id(checksum, 1)

    # Determinism
    assert id1 == id2
    # Distinct indices produce distinct IDs
    assert id1 != id3
    # Valid UUID format
    parsed = uuid.UUID(id1)
    assert parsed.version == 5


def test_chunker_section_detection():
    """Verify that section headings are extracted and attached to chunks."""
    chunker = DocumentChunker(target_words=40, overlap_words=5)
    page_text = (
        "1. RICE CLIMATE REQUIREMENT\n"
        "Rice requires warm and humid climate with optimum temperature between 30 and 32 degrees Celsius. "
        "Rainfall requirement ranges from 1000 to 4500 mm annually."
    )
    pages = [(1, page_text)]
    checksum = "test-section-checksum"
    chunks = chunker.chunk_pages(pages, checksum)

    assert len(chunks) >= 1
    assert chunks[0].section == "1. RICE CLIMATE REQUIREMENT"
    assert chunks[0].page_number == 1


def test_chunker_empty_pages_ignored():
    """Verify empty or whitespace-only pages are skipped cleanly."""
    chunker = DocumentChunker()
    pages = [(1, "   "), (2, ""), (3, "Valid agronomic content for crop production.")]
    chunks = chunker.chunk_pages(pages, "chk123")

    assert len(chunks) == 1
    assert chunks[0].page_number == 3
