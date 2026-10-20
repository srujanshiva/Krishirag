"""API tests for POST /api/v1/chat endpoint."""

import uuid
from typing import List
import pytest
from httpx import AsyncClient

from backend.app.llm.gateway import (
    LLMGateway,
    LLMNotConfiguredError,
    LLMQuotaExceededError,
    LLMResponse,
    get_llm_gateway,
)
from backend.app.main import app
from backend.app.rag.retriever import RetrievedChunk


class MockGroundedLLMGateway(LLMGateway):
    """Mock LLM gateway for hermetic, deterministic testing."""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        cited_id = context_chunks[0].chunk_id if context_chunks else "none"
        content = (
            f"Based on recommendations, apply 120 kg/ha nitrogen for rice [{cited_id}]. "
            f"You should also add unverified chemical [{uuid.uuid4()}]."
        )
        return LLMResponse(
            content=content,
            model_used="mock-qwen-27b",
            provider="mock",
        )


class MockUnconfiguredLLMGateway(LLMGateway):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        raise LLMNotConfiguredError()


class MockQuotaExceededLLMGateway(LLMGateway):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        raise LLMQuotaExceededError()


@pytest.mark.asyncio
async def test_chat_grounded_response_with_citations(async_client: AsyncClient):
    """Verify chat endpoint returns grounded advice and valid citations from populated KB."""
    app.dependency_overrides[get_llm_gateway] = lambda: MockGroundedLLMGateway()

    try:
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "question": "What is the nitrogen requirement for rice crop?",
                "crop": "Rice",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "answer" in data
        assert "citations" in data
        assert "conversation_id" in data
        assert "message_id" in data

        # Check citations
        assert len(data["citations"]) >= 1
        citation = data["citations"][0]
        assert "chunk_id" in citation
        assert "document_title" in citation
        assert "page_number" in citation
        assert "excerpt" in citation

        # Hallucinated citation was stripped
        assert data["evidence_count"] >= 1
        assert data["uncertainty"] in ("none", "low")

    finally:
        app.dependency_overrides.pop(get_llm_gateway, None)


@pytest.mark.asyncio
async def test_chat_empty_kb_uncertainty_guardrail(async_client: AsyncClient, monkeypatch):
    """Verify query with no evidence returns high uncertainty and extension advisory."""
    from backend.app.api.v1.chat import retriever

    monkeypatch.setattr(retriever, "retrieve", lambda *args, **kwargs: [])

    response = await async_client.post(
        "/api/v1/chat",
        json={
            "question": "xyznonexistentcropdisease12345 obscure question with zero matches",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["uncertainty"] == "high"
    assert data["citations"] == []
    assert data["evidence_count"] == 0
    assert "Krishi Bhavan" in data["answer"] or "KVK" in data["answer"]


@pytest.mark.asyncio
async def test_chat_llm_not_configured_error(async_client: AsyncClient):
    """Verify missing LLM configuration returns HTTP 503 with LLM_NOT_CONFIGURED error code."""
    app.dependency_overrides[get_llm_gateway] = lambda: MockUnconfiguredLLMGateway()

    try:
        response = await async_client.post(
            "/api/v1/chat",
            json={"question": "How to control blast in rice?"},
        )
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error_code"] == "LLM_NOT_CONFIGURED"

    finally:
        app.dependency_overrides.pop(get_llm_gateway, None)


@pytest.mark.asyncio
async def test_chat_rate_limit_error(async_client: AsyncClient):
    """Verify rate limit error returns HTTP 429 with LLM_QUOTA_EXCEEDED error code."""
    app.dependency_overrides[get_llm_gateway] = lambda: MockQuotaExceededLLMGateway()

    try:
        response = await async_client.post(
            "/api/v1/chat",
            json={"question": "How to control blast in rice?"},
        )
        assert response.status_code == 429
        detail = response.json()["detail"]
        assert detail["error_code"] == "LLM_QUOTA_EXCEEDED"

    finally:
        app.dependency_overrides.pop(get_llm_gateway, None)


@pytest.mark.asyncio
async def test_chat_input_validation(async_client: AsyncClient):
    """Verify empty or excessively long inputs are rejected with 422."""
    # Empty question
    resp1 = await async_client.post("/api/v1/chat", json={"question": ""})
    assert resp1.status_code == 422

    # Excessively long question (> 2000 chars)
    resp2 = await async_client.post("/api/v1/chat", json={"question": "A" * 2001})
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_chat_dialogue_persistence(async_client: AsyncClient):
    """Verify multi-turn conversation persistence and retrieval via conversations API."""
    app.dependency_overrides[get_llm_gateway] = lambda: MockGroundedLLMGateway()

    try:
        conv_id = uuid.uuid4()
        # Message 1
        resp1 = await async_client.post(
            "/api/v1/chat",
            json={"question": "What is the seed rate for transplanted rice?", "conversation_id": str(conv_id)},
        )
        assert resp1.status_code == 200

        # Message 2
        resp2 = await async_client.post(
            "/api/v1/chat",
            json={"question": "What about nursery management?", "conversation_id": str(conv_id)},
        )
        assert resp2.status_code == 200

        # Retrieve conversation history
        conv_resp = await async_client.get(f"/api/v1/conversations/{conv_id}")
        assert conv_resp.status_code == 200
        history = conv_resp.json()
        assert history["id"] == str(conv_id)
        assert len(history["messages"]) >= 4  # 2 user + 2 assistant messages

    finally:
        app.dependency_overrides.pop(get_llm_gateway, None)
