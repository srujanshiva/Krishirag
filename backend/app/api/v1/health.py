"""Health and readiness check endpoints."""

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.db.session import get_db

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def get_health():
    """Liveness probe. Returns 200 unconditionally if app process is alive."""
    return {
        "status": "ok",
        "version": settings.VERSION,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def get_readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe. Checks Postgres DB, Qdrant vector store, LLM configuration, and knowledge base.

    Never exposes connection strings, credentials, or internal secrets.
    """
    # 1. Check PostgreSQL
    db_status = "error"
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_status = "ok"
    except Exception:
        db_status = "error"

    # 2. Check Qdrant Vector Store
    qdrant_status = "error"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.QDRANT_URL.rstrip('/')}/healthz")
            if resp.status_code == 200:
                qdrant_status = "ok"
    except Exception:
        qdrant_status = "error"

    # 3. Check LLM Configuration (Groq or Gemini)
    llm_configured = False
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        if not settings.GROQ_API_KEY.startswith("YOUR_"):
            llm_configured = True
    elif settings.LLM_PROVIDER in ("gemini", "google") and settings.GOOGLE_API_KEY:
        if not settings.GOOGLE_API_KEY.startswith("YOUR_"):
            llm_configured = True
    elif settings.GROQ_API_KEY or settings.GOOGLE_API_KEY:
        llm_configured = True

    # 4. Check Knowledge Base
    kb_status = "empty"
    try:
        kb_res = await db.execute(text("SELECT count(*) FROM documents WHERE ingestion_status = 'completed'"))
        doc_count = kb_res.scalar() or 0
        if doc_count > 0:
            kb_status = "populated"
    except Exception:
        kb_status = "empty"

    return {
        "db": db_status,
        "vector_store": qdrant_status,
        "llm_configured": llm_configured,
        "knowledge_base": kb_status,
    }
