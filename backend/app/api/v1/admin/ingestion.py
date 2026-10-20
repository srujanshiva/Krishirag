"""Admin API endpoints for document ingestion management."""

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Security,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.models import Document, IngestionJob
from backend.app.db.session import async_session_maker, get_db
from backend.app.rag.ingestion import IngestionPipeline
from backend.app.schemas.ingestion import DocumentResponse, IngestionJobResponse

router = APIRouter(prefix="/admin", tags=["Admin Ingestion"])
security = HTTPBearer()
pipeline = IngestionPipeline()


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Validate bearer token against configured ADMIN_TOKEN."""
    if credentials.credentials != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def _run_file_ingestion(
    job_id: uuid.UUID,
    file_bytes: bytes,
    title: str,
    publisher: Optional[str],
    source_url: Optional[str],
):
    """Background task runner for file-based ingestion."""
    async with async_session_maker() as db:
        try:
            await pipeline.ingest_file(
                pdf_bytes=file_bytes,
                title=title,
                db=db,
                publisher=publisher,
                source_url=source_url,
                job_id=job_id,
            )
        except Exception as e:
            logger.error(f"Background ingestion failed for job {job_id}: {e}")


async def _run_url_ingestion(
    job_id: uuid.UUID,
    url: str,
    title: Optional[str],
    publisher: Optional[str],
):
    """Background task runner for URL-based ingestion."""
    async with async_session_maker() as db:
        try:
            await pipeline.ingest_from_url(
                url=url,
                db=db,
                title=title,
                publisher=publisher,
                job_id=job_id,
            )
        except Exception as e:
            logger.error(f"Background URL ingestion failed for job {job_id}: {e}")


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post(
    "/ingest-file",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_200_OK,
)
async def ingest_file_direct(
    file: UploadFile = File(...),
    title: str = Form(...),
    publisher: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_token),
):
    """Synchronous file ingestion for immediate validation and chunk indexing."""
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 50MB.",
        )
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Uploaded file must be a valid PDF document.",
        )

    job = await pipeline.ingest_file(
        pdf_bytes=file_bytes,
        title=title,
        db=db,
        publisher=publisher,
        source_url=source_url,
    )
    return job


@router.post(
    "/ingestion-jobs",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ingestion_job(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_token),
):
    """Trigger a new ingestion job via PDF file upload or direct document URL."""
    if not file and not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a PDF file upload or a source_url must be provided.",
        )

    job_id = uuid.uuid4()
    job = IngestionJob(
        id=job_id,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    if file:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum allowed size is 50MB.",
            )
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Uploaded file must be a valid PDF document.",
            )

        inferred_title = title or file.filename.replace(".pdf", "").replace("_", " ").title()
        background_tasks.add_task(
            _run_file_ingestion,
            job_id=job_id,
            file_bytes=file_bytes,
            title=inferred_title,
            publisher=publisher,
            source_url=source_url,
        )
    elif source_url:
        background_tasks.add_task(
            _run_url_ingestion,
            job_id=job_id,
            url=source_url,
            title=title,
            publisher=publisher,
        )

    return job


@router.get("/ingestion-jobs", response_model=List[IngestionJobResponse])
async def list_ingestion_jobs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_token),
):
    """List recent ingestion jobs."""
    stmt = select(IngestionJob).order_by(desc(IngestionJob.created_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/ingestion-jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_token),
):
    """Retrieve details and status for a specific ingestion job."""
    res = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    return job


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_token),
):
    """List registered documents in the knowledge base."""
    stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
