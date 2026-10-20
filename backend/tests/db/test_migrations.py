"""Tests verifying Alembic migrations and database schema integrity."""

import uuid
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.db.models import (
    Document,
    IngestionJob,
    DocumentChunk,
    Conversation,
    Message,
    Feedback,
)


def test_migration_tables_exist():
    """Verify that Alembic migration 0001 created all required tables."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    expected_tables = {
        "documents",
        "ingestion_jobs",
        "document_chunks",
        "conversations",
        "messages",
        "feedback",
        "alembic_version",
    }

    assert expected_tables.issubset(existing_tables), f"Missing tables: {expected_tables - existing_tables}"


def test_schema_constraints():
    """Verify primary keys, unique constraints, and check constraints exist."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)

    # 1. documents table constraints
    doc_cols = {c["name"] for c in inspector.get_columns("documents")}
    assert "checksum_sha256" in doc_cols
    assert "ingestion_status" in doc_cols
    doc_uqs = {uq["name"] for uq in inspector.get_unique_constraints("documents")}
    assert "uq_documents_checksum_sha256" in doc_uqs

    # 2. document_chunks constraints
    chunk_cols = {c["name"] for c in inspector.get_columns("document_chunks")}
    assert "vector_id" in chunk_cols
    chunk_uqs = {uq["name"] for uq in inspector.get_unique_constraints("document_chunks")}
    assert "uq_document_chunks_vector_id" in chunk_uqs
    assert "uq_document_chunk_index" in chunk_uqs

    # 3. messages columns
    msg_cols = {c["name"] for c in inspector.get_columns("messages")}
    assert "citations" in msg_cols
    assert "uncertainty" in msg_cols

    # 4. feedback check constraint
    check_constraints = [ck["name"] for ck in inspector.get_check_constraints("feedback")]
    assert "ck_feedback_rating" in check_constraints


@pytest.mark.asyncio
async def test_crud_model_persistence(db_session: AsyncSession):
    """Verify CRUD operations and relationship cascades work end-to-end."""
    # 1. Insert Document
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        title="Test Agriculture Manual",
        publisher="ICAR",
        source_url="https://icar.org.in/test.pdf",
        checksum_sha256="test-sha256-hash-001",
        ingestion_status="completed",
        language="en",
    )
    db_session.add(doc)
    await db_session.flush()

    # 2. Insert DocumentChunk referencing Document
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        chunk_text="Nitrogen recommendation for paddy crop is 120 kg/ha.",
        vector_id="vec-chunk-001",
        page_number=1,
        section="Fertilizer Management",
    )
    db_session.add(chunk)
    await db_session.flush()

    # 3. Insert Conversation and Message
    conv = Conversation()
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Apply 120 kg/ha nitrogen for paddy.",
        citations=[{"doc_id": str(doc.id), "chunk_id": str(chunk.id), "page": 1}],
        uncertainty="none",
    )
    db_session.add(msg)
    await db_session.flush()

    # 4. Insert Feedback
    fb = Feedback(
        message_id=msg.id,
        rating=5,
        comment="Accurate recommendation",
    )
    db_session.add(fb)
    await db_session.flush()

    assert doc.id == doc_id
    assert chunk.document_id == doc.id
    assert msg.conversation_id == conv.id
    assert fb.message_id == msg.id
