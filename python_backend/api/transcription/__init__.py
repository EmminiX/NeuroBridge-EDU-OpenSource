"""
Transcription API Router
Real-time transcription endpoints using HTTP + SSE architecture
"""

from fastapi import APIRouter
from .start import router as start_router
from .chunk import router as chunk_router  
from .stream import router as stream_router
from .stop import router as stop_router
from .config import router as config_router

# Create main transcription router
router = APIRouter()

# Include all transcription endpoints
router.include_router(start_router)
router.include_router(chunk_router)
router.include_router(stream_router)
router.include_router(stop_router)
router.include_router(config_router)