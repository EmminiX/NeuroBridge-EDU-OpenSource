"""
NeuroBridge EDU Python Backend
FastAPI application entry point with async lifespan management
"""

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import register_routes
from middleware.cors import setup_cors
from models.database.connection import init_database
from config import settings
from utils.logger import setup_logging
from utils.error_handler import global_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging()
    await init_database()
    yield
    # Shutdown (cleanup if needed)


# Create FastAPI application
app = FastAPI(
    title="NeuroBridge EDU API",
    description="Real-time transcription and AI summarization platform",
    version="2.0.0",
    lifespan=lifespan
)

# Setup middleware
setup_cors(app)

# Register all API routes
register_routes(app)

# Add global exception handler
@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception):
    return await global_exception_handler(request, exc)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "neurobridge-edu", "port": settings.PORT}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )