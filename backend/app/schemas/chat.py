"""Pydantic schemas for chat queries, advisory responses, and farmer feedback."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.citations import CitationResponse


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Agricultural or agronomic query from the farmer",
    )
    conversation_id: Optional[uuid.UUID] = Field(
        None,
        description="Existing conversation UUID to continue multi-turn dialogue",
    )
    crop: Optional[str] = Field(
        None,
        description="Optional crop context (e.g. Rice, Pepper, Coconut)",
    )
    location: Optional[str] = Field(
        None,
        description="Optional location / district context (e.g. Palakkad, Thrissur)",
    )


class ChatResponse(BaseModel):
    request_id: uuid.UUID
    answer: str
    citations: List[CitationResponse] = Field(default_factory=list)
    uncertainty: str = Field(
        ...,
        description="Confidence level: 'none' | 'low' | 'high'",
    )
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    retrieval_score: Optional[float] = None
    evidence_count: int


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[dict]] = None
    uncertainty: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    message_id: uuid.UUID = Field(..., description="Message UUID being evaluated")
    rating: int = Field(..., ge=1, le=5, description="Farmer satisfaction rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional qualitative feedback")


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
