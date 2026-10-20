"""Ingestion worker for processing, chunking, embedding, and indexing agricultural PDFs."""

import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import pdfplumber
import pypdf
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Document, DocumentChunk, IngestionJob
from backend.app.rag.chunker import DocumentChunker, TextChunk
from backend.app.rag.embedder import FastEmbedder
from backend.app.rag.vector_store import QdrantVectorStore


class IngestionPipeline:
    """End-to-end ingestion pipeline with SHA-256 deduplication and Qdrant vector indexing."""

    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        embedder: Optional[FastEmbedder] = None,
        vector_store: Optional[QdrantVectorStore] = None,
    ):
        self.chunker = chunker or DocumentChunker()
        self.embedder = embedder or FastEmbedder()
        self.vector_store = vector_store or QdrantVectorStore()

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Calculate SHA-256 checksum of raw file bytes."""
        return hashlib.sha256(content).hexdigest()

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> List[Tuple[int, str]]:
        """Extract text page by page from PDF bytes using pypdf with pdfplumber fallback."""
        pages: List[Tuple[int, str]] = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append((idx + 1, text.strip()))
        except Exception as e:
            logger.warning(f"pypdf extraction issue: {e}. Falling back to pdfplumber.")
            pages = []

        # If pypdf yielded no text at all, attempt pdfplumber
        total_text = "".join(t for _, t in pages)
        if not total_text.strip():
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    pages = []
                    for idx, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        pages.append((idx + 1, text.strip()))
            except Exception as e:
                logger.error(f"pdfplumber extraction failed: {e}")
                raise ValueError(f"Could not extract text from PDF: {e}")

        return pages

    async def ingest_file(
        self,
        pdf_bytes: bytes,
        title: str,
        db: AsyncSession,
        publisher: Optional[str] = None,
        source_url: Optional[str] = None,
        license_note: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
    ) -> IngestionJob:
        """Execute idempotent ingestion of a PDF document."""
        checksum = self.compute_sha256(pdf_bytes)
        now = datetime.now(timezone.utc)

        # Retrieve or initialize IngestionJob
        job: Optional[IngestionJob] = None
        if job_id:
            res = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
            job = res.scalar_one_or_none()

        if not job:
            job = IngestionJob(
                id=job_id or uuid.uuid4(),
                status="processing",
                created_at=now,
            )
            db.add(job)
            await db.flush()

        # Deduplication check: does document already exist?
        stmt = select(Document).where(Document.checksum_sha256 == checksum)
        res = await db.execute(stmt)
        existing_doc = res.scalar_one_or_none()

        if existing_doc and existing_doc.ingestion_status == "completed":
            logger.info(f"Document with checksum {checksum} already exists (id={existing_doc.id}). Skipping.")
            # Count existing chunks
            count_res = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == existing_doc.id)
            )
            existing_chunks = count_res.scalars().all()

            job.status = "already_exists"
            job.document_id = existing_doc.id
            job.chunk_count = len(existing_chunks)
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return job

        try:
            # Create or update Document record
            document = existing_doc
            if not document:
                document = Document(
                    id=uuid.uuid4(),
                    title=title,
                    publisher=publisher,
                    source_url=source_url,
                    checksum_sha256=checksum,
                    retrieved_at=now,
                    ingestion_status="processing",
                    license_note=license_note,
                )
                db.add(document)
                await db.flush()
            else:
                document.ingestion_status = "processing"

            job.document_id = document.id
            job.status = "processing"
            await db.flush()

            # 1. Extract text
            pages = self.extract_text_from_pdf(pdf_bytes)
            if not any(text for _, text in pages):
                raise ValueError("Extracted PDF content is empty.")

            # 2. Chunk text
            chunks = self.chunker.chunk_pages(pages, checksum)
            if not chunks:
                raise ValueError("No valid text chunks generated from PDF content.")

            # 3. Generate embeddings
            texts_to_embed = [c.chunk_text for c in chunks]
            vectors = self.embedder.embed_documents(texts_to_embed)

            # 4. Upsert vectors into Qdrant
            metadata = {
                "id": str(document.id),
                "title": document.title,
                "publisher": document.publisher or "",
                "source_url": document.source_url or "",
                "license_note": document.license_note or "",
            }
            self.vector_store.upsert_chunks(chunks, vectors, metadata)

            # 5. Persist document chunks to PostgreSQL
            for c in chunks:
                chunk_record = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    chunk_index=c.chunk_index,
                    chunk_text=c.chunk_text,
                    vector_id=c.vector_id,
                    page_number=c.page_number,
                    section=c.section,
                )
                db.add(chunk_record)

            # 6. Finalize statuses
            document.ingestion_status = "completed"
            job.status = "completed"
            job.chunk_count = len(chunks)
            job.finished_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"Ingestion successful: doc={document.id}, chunks={len(chunks)}")
            return job

        except Exception as e:
            logger.error(f"Ingestion error for doc {title}: {e}")
            await db.rollback()
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.add(job)
            await db.commit()
            return job

    async def ingest_from_url(
        self,
        url: str,
        db: AsyncSession,
        title: Optional[str] = None,
        publisher: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
    ) -> IngestionJob:
        """Download PDF from URL and trigger ingestion."""
        async with httpx.AsyncClient(timeout=60.0, verify=False, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            pdf_bytes = resp.content

        inferred_title = title or Path(url).stem.replace("_", " ").title()
        return await self.ingest_file(
            pdf_bytes=pdf_bytes,
            title=inferred_title,
            db=db,
            publisher=publisher,
            source_url=url,
            job_id=job_id,
        )
