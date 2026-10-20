"""Pydantic schemas for knowledge ingestion."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IngestionJobCreate(BaseModel):
    source_url: Optional[str] = Field(None, description="Direct URL to downloadable PDF document")
    title: Optional[str] = Field(None, description="Optional title override")
    publisher: Optional[str] = Field(None, description="Publishing organization (e.g. ICAR, KAU, TNAU)")


class IngestionJobResponse(BaseModel):
    id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    status: str
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    publisher: Optional[str] = None
    source_url: Optional[str] = None
    language: str
    checksum_sha256: str
    ingestion_status: str
    license_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
