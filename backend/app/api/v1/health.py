"""Health and readiness check endpoints."""

import httpx
from fastapi import APIRouter, Depends, status
from loguru import logger
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
        "environment": settings.APP_ENV,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def get_readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe. Checks Postgres DB, Qdrant vector store, LLM configuration, and knowledge base.

    Never exposes connection strings, credentials, or internal secrets.
    """
    # 1. Check PostgreSQL
    db_status = "error"
    doc_count = 0
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_status = "connected"
            kb_res = await db.execute(text("SELECT count(*) FROM documents WHERE ingestion_status = 'completed'"))
            doc_count = kb_res.scalar() or 0
    except Exception as e:
        logger.error(f"DB ready check error: {e}")
        db_status = "error"

    # 2. Check Qdrant Vector Store
    qdrant_status = "error"
    vector_count = 0
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.QDRANT_URL.rstrip('/')}/healthz")
            if resp.status_code == 200:
                qdrant_status = "connected"
                try:
                    col_resp = await client.get(
                        f"{settings.QDRANT_URL.rstrip('/')}/collections/{settings.QDRANT_COLLECTION}"
                    )
                    if col_resp.status_code == 200:
                        vector_count = col_resp.json().get("result", {}).get("points_count", 0)
                except Exception:
                    pass
    except Exception:
        qdrant_status = "error"

    # 3. Check LLM Configuration (Groq, Gemini, or Ollama)
    llm_configured = False
    local_llm_status = "disabled"

    # Optional local LLM probe
    if settings.ENABLE_LOCAL_LLM_FALLBACK or settings.LLM_PROVIDER == "ollama" or settings.OFFLINE_MODE:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                if r.status_code == 200:
                    models = [m.get("name", "") for m in r.json().get("models", [])]
                    if any(settings.OLLAMA_MODEL in m for m in models):
                        local_llm_status = "ready"
                    else:
                        local_llm_status = "model_missing"
                else:
                    local_llm_status = "error"
        except Exception:
            local_llm_status = "unreachable"

    if settings.OFFLINE_MODE:
        llm_configured = (local_llm_status == "ready")
    elif settings.LLM_PROVIDER == "ollama":
        llm_configured = (local_llm_status == "ready")
    elif settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        if not settings.GROQ_API_KEY.startswith("YOUR_"):
            llm_configured = True
    elif settings.LLM_PROVIDER in ("gemini", "google") and settings.GOOGLE_API_KEY:
        if not settings.GOOGLE_API_KEY.startswith("YOUR_"):
            llm_configured = True
    elif settings.GROQ_API_KEY or settings.GOOGLE_API_KEY:
        llm_configured = True

    return {
        "status": "ready" if db_status == "connected" and qdrant_status == "connected" else "not_ready",
        "database": db_status,
        "db": "ok" if db_status == "connected" else "error",
        "vector_store": qdrant_status,
        "document_count": doc_count,
        "vector_count": vector_count,
        "knowledge_base": "populated" if doc_count > 0 else "empty",
        "llm_configured": llm_configured,
        "local_llm": local_llm_status,
        "offline_mode": settings.OFFLINE_MODE,
    }
