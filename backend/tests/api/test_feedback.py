"""Tests for POST /api/v1/feedback endpoint."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Conversation, Message


@pytest.mark.asyncio
async def test_feedback_submission_success(async_client: AsyncClient, db_session: AsyncSession):
    """Verify valid farmer feedback is recorded successfully."""
    # Seed conversation and message
    conv = Conversation()
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Apply 120 kg/ha nitrogen.",
        uncertainty="none",
    )
    db_session.add(msg)
    await db_session.commit()

    # Submit feedback
    resp = await async_client.post(
        "/api/v1/feedback",
        json={
            "message_id": str(msg.id),
            "rating": 5,
            "comment": "Very accurate and helpful recommendation.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["message_id"] == str(msg.id)
    assert data["rating"] == 5
    assert data["comment"] == "Very accurate and helpful recommendation."


@pytest.mark.asyncio
async def test_feedback_rating_boundary_validation(async_client: AsyncClient):
    """Verify rating must be between 1 and 5."""
    random_msg_id = str(uuid.uuid4())

    # Rating 0 (below min 1)
    resp1 = await async_client.post(
        "/api/v1/feedback",
        json={"message_id": random_msg_id, "rating": 0},
    )
    assert resp1.status_code == 422

    # Rating 6 (above max 5)
    resp2 = await async_client.post(
        "/api/v1/feedback",
        json={"message_id": random_msg_id, "rating": 6},
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_feedback_nonexistent_message(async_client: AsyncClient):
    """Verify feedback on non-existent message returns 404."""
    non_existent_id = str(uuid.uuid4())
    resp = await async_client.post(
        "/api/v1/feedback",
        json={"message_id": non_existent_id, "rating": 4},
    )
    assert resp.status_code == 404
