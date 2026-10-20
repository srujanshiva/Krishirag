"""Admin API package."""
from backend.app.api.v1.admin.ingestion import router as ingestion_router

__all__ = ["ingestion_router"]
