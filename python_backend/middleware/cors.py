"""
CORS Middleware Configuration
Cross-Origin Resource Sharing setup for FastAPI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI application"""
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )