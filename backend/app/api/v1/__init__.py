"""API v1 routers."""
from fastapi import APIRouter

from backend.app.api.v1.admin.ingestion import router as admin_ingestion_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.conversations import router as conversations_router
from backend.app.api.v1.feedback import router as feedback_router
from backend.app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_ingestion_router)
