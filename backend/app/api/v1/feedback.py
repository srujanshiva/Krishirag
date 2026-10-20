"""Feedback collection endpoint for rating agricultural advisory responses."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Feedback, Message
from backend.app.db.session import get_db
from backend.app.schemas.chat import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit farmer rating and comment on an advisory message."""
    # Verify message exists
    stmt = select(Message).where(Message.id == feedback_in.message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced message not found",
        )

    feedback = Feedback(
        id=uuid.uuid4(),
        message_id=feedback_in.message_id,
        rating=feedback_in.rating,
        comment=feedback_in.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return feedback
