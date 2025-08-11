"""
Summaries API Router
Minimal implementation for generation and export without database storage
"""

from fastapi import APIRouter
from .generate import router as generate_router
from .export import router as export_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(generate_router)
router.include_router(export_router)