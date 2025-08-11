"""
API Routes Registration
Centralizes all route registration for the FastAPI application
"""

from fastapi import FastAPI
from .transcription import router as transcription_router
from .summaries import router as summaries_router
from .errors import router as errors_router
from .api_keys import router as api_keys_router


def register_routes(app: FastAPI) -> None:
    """Register all API routes with the FastAPI application"""
    
    # Transcription endpoints
    app.include_router(
        transcription_router,
        prefix="/api/transcribe",
        tags=["transcription"]
    )
    
    # Summary generation endpoints (without database)
    app.include_router(
        summaries_router,
        prefix="/api/summaries",
        tags=["summaries"]
    )
    
    # API key management endpoints
    app.include_router(
        api_keys_router,
        prefix="/api/keys",
        tags=["api-keys"]
    )
    
    # Error logging endpoints
    app.include_router(
        errors_router,
        prefix="/api/errors",
        tags=["errors"]
    )