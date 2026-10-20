"""Tests for health and readiness endpoints."""

import pytest
from httpx import AsyncClient
from backend.app.config import settings


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify root endpoint returns project metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert "/docs" in data["docs"]


@pytest.mark.asyncio
async def test_health_liveness(async_client: AsyncClient):
    """Verify /api/v1/health returns 200 and status ok."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == settings.VERSION


@pytest.mark.asyncio
async def test_readiness_probe(async_client: AsyncClient):
    """Verify /api/v1/ready checks DB, vector store, and LLM configuration."""
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert "db" in data
    assert "vector_store" in data
    assert "llm_configured" in data
    assert "knowledge_base" in data
    assert data["db"] == "ok"
    assert data["vector_store"] == "ok"
    assert data["knowledge_base"] in ("empty", "populated")
    assert isinstance(data["llm_configured"], bool)


@pytest.mark.asyncio
async def test_readiness_no_secret_leakage(async_client: AsyncClient):
    """Verify /api/v1/ready never leaks database credentials or API keys."""
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    text_content = response.text

    # Verify no secrets in response body
    if settings.GROQ_API_KEY:
        assert settings.GROQ_API_KEY not in text_content
    if settings.GOOGLE_API_KEY:
        assert settings.GOOGLE_API_KEY not in text_content
    assert "password" not in text_content.lower()
    assert "postgresql://" not in text_content
    assert "psycopg://" not in text_content
