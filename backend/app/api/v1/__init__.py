"""API v1 routers."""
from fastapi import APIRouter
from backend.app.api.v1.admin.ingestion import router as admin_ingestion_router
from backend.app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(admin_ingestion_router)
