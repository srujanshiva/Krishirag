"""Tests for admin document ingestion endpoints."""

import io
import uuid
import pytest
from httpx import AsyncClient
from backend.app.config import settings


@pytest.mark.asyncio
async def test_admin_auth_required(async_client: AsyncClient):
    """Verify endpoints reject unauthenticated or incorrectly authenticated requests."""
    # 1. No auth header
    resp1 = await async_client.post("/api/v1/admin/ingestion-jobs", data={"source_url": "https://example.com/doc.pdf"})
    assert resp1.status_code in (401, 403)

    # 2. Invalid auth token
    resp2 = await async_client.post(
        "/api/v1/admin/ingestion-jobs",
        headers={"Authorization": "Bearer wrong-token"},
        data={"source_url": "https://example.com/doc.pdf"},
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_admin_ingestion_file_submission(async_client: AsyncClient):
    """Verify authenticated PDF file submission triggers background job."""
    headers = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}

    # Prepare small dummy PDF
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"

    files = {"file": ("test_manual.pdf", io.BytesIO(dummy_pdf_content), "application/pdf")}
    data = {"title": "Test Agronomy Manual", "publisher": "ICAR"}

    response = await async_client.post(
        "/api/v1/admin/ingestion-jobs",
        headers=headers,
        files=files,
        data=data,
    )
    assert response.status_code == 202
    job_data = response.json()
    assert "id" in job_data
    assert job_data["status"] == "queued"
    job_id = job_data["id"]

    # Retrieve job status via GET /api/v1/admin/ingestion-jobs/{id}
    status_resp = await async_client.get(
        f"/api/v1/admin/ingestion-jobs/{job_id}",
        headers=headers,
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == job_id


@pytest.mark.asyncio
async def test_admin_list_jobs_and_documents(async_client: AsyncClient):
    """Verify listing ingestion jobs and cataloged documents."""
    headers = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}

    jobs_resp = await async_client.get("/api/v1/admin/ingestion-jobs", headers=headers)
    assert jobs_resp.status_code == 200
    assert isinstance(jobs_resp.json(), list)

    docs_resp = await async_client.get("/api/v1/admin/documents", headers=headers)
    assert docs_resp.status_code == 200
    assert isinstance(docs_resp.json(), list)
