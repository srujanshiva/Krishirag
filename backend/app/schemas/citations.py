"""Pydantic schemas for citations and evidence attribution."""

import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    chunk_id: str = Field(..., description="Stable vector ID of the source chunk")
    document_title: str = Field(..., description="Title of the authoritative publication")
    publisher: str = Field(..., description="Issuing agency or university (e.g. TNAU, ICAR, KAU)")
    source_url: Optional[str] = Field(None, description="Direct URL to source publication")
    publication_date: Optional[str] = Field(None, description="Date or year of publication")
    page_number: Optional[int] = Field(None, description="Source page number in document")
    section: Optional[str] = Field(None, description="Document section or topic heading")
    excerpt: str = Field(..., description="Excerpt from chunk (first 300 characters)")
