"""Tests verifying idempotency of the PDF ingestion pipeline."""

import io
import uuid
import pypdf
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document, DocumentChunk, IngestionJob
from backend.app.rag.ingestion import IngestionPipeline
from backend.app.rag.vector_store import QdrantVectorStore


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Create a 2-page real agricultural PDF slice from TNAU guide."""
    reader = pypdf.PdfReader("data/sources/tnau_crop_production_guide_rice.pdf")
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_page(reader.pages[1])
    writer.add_metadata({"/TestRunId": uuid.uuid4().hex})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_ingestion_idempotency(sample_pdf_bytes: bytes, db_session: AsyncSession):
    """Verify that ingesting the identical document twice is strictly idempotent."""
    test_collection = f"test_idemp_{uuid.uuid4().hex[:8]}"
    vector_store = QdrantVectorStore(collection_name=test_collection)
    pipeline = IngestionPipeline(vector_store=vector_store)
    doc_id1 = None

    try:
        # First Ingestion
        job1 = await pipeline.ingest_file(
            pdf_bytes=sample_pdf_bytes,
            title="TNAU Rice Production Quick Guide",
            publisher="Tamil Nadu Agricultural University",
            source_url="https://tnagriculture.in/sample_rice.pdf",
            db=db_session,
        )

        assert job1.status == "completed"
        assert job1.chunk_count is not None and job1.chunk_count > 0
        doc_id1 = job1.document_id

        # Verify DB rows
        doc_chunks_1 = (
            await db_session.execute(
                select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id1)
            )
        ).scalar()
        docs_count_1 = (await db_session.execute(select(func.count(Document.id)))).scalar()
        total_chunks_1 = (await db_session.execute(select(func.count(DocumentChunk.id)))).scalar()
        vectors_count_1 = vector_store.count()

        assert docs_count_1 >= 1
        assert doc_chunks_1 == job1.chunk_count
        assert vectors_count_1 == job1.chunk_count

        # Second Ingestion with identical PDF
        job2 = await pipeline.ingest_file(
            pdf_bytes=sample_pdf_bytes,
            title="TNAU Rice Production Duplicate",
            publisher="Tamil Nadu Agricultural University",
            source_url="https://tnagriculture.in/sample_rice.pdf",
            db=db_session,
        )

        # Assert status is already_exists
        assert job2.status == "already_exists"
        assert job2.document_id == doc_id1
        assert job2.chunk_count == job1.chunk_count

        # Verify DB counts did not change
        docs_count_2 = (await db_session.execute(select(func.count(Document.id)))).scalar()
        total_chunks_2 = (await db_session.execute(select(func.count(DocumentChunk.id)))).scalar()
        vectors_count_2 = vector_store.count()

        assert docs_count_2 == docs_count_1, "Expected zero new Document rows"
        assert total_chunks_2 == total_chunks_1, "Expected zero new DocumentChunk rows"
        assert vectors_count_2 == vectors_count_1, "Expected zero new Qdrant points"

    finally:
        from sqlalchemy import delete
        if doc_id1:
            try:
                await db_session.execute(delete(Document).where(Document.id == doc_id1))
                await db_session.commit()
            except Exception:
                pass
        try:
            vector_store.client.delete_collection(test_collection)
        except Exception:
            pass
