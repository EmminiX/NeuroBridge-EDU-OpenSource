"""
Transcription Session Start Endpoint
POST /api/transcribe/start - Initialize new transcription session
"""

from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from services.whisper.session import session_manager
from services.openai.client import get_default_openai_client
from utils.logger import get_logger
from pydantic import BaseModel
from typing import Optional
from openai import AsyncOpenAI

router = APIRouter()
logger = get_logger("transcription.start")


@router.get("/test")
async def test_transcription_service():
    """
    Test endpoint for checking transcription service availability
    Used by frontend to verify backend connectivity
    """
    try:
        # Check if OpenAI client can be initialized
        try:
            client = await get_default_openai_client()
            is_available = client is not None
            message = "Transcription service is ready" if is_available else "Transcription service requires stored API key"
        except RuntimeError as e:
            # This is expected when no API keys are stored
            is_available = False
            message = "No API key available. Please add an OpenAI API key in Settings."
        except Exception as e:
            logger.error(f"Error checking OpenAI client: {e}")
            is_available = False
            message = f"Service check failed: {str(e)}"
        
        return {
            "status": "healthy" if is_available else "unavailable",
            "service": "transcription",
            "whisper_available": is_available,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return {
            "status": "error",
            "service": "transcription", 
            "whisper_available": False,
            "message": f"Service check failed: {str(e)}"
        }


class SessionStartRequest(BaseModel):
    sessionId: Optional[str] = None
    
@router.post("/start")
async def start_transcription_session(
    request: SessionStartRequest
):
    """
    Start a new transcription session
    Accepts optional sessionId from client or generates a new one
    Supports both local and API-based transcription methods
    """
    try:
        # Check transcription method configuration to determine if API key is required
        from config import settings
        
        # Only validate API key for API-only mode
        # For local_first, local_only, and auto modes, session can start without API key
        if settings.TRANSCRIPTION_METHOD == "api_only":
            try:
                openai_client = await get_default_openai_client()
                logger.info("API-only mode: OpenAI client validated")
            except RuntimeError as e:
                logger.warning(f"API-only mode requires API key: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="API-only transcription mode requires an OpenAI API key. Please add an API key in Settings."
                )
        else:
            # For local_first, local_only, and auto modes, we can start without API key
            # The session manager and transcriber will handle API key requirements dynamically
            logger.info(f"Starting session with transcription method: {settings.TRANSCRIPTION_METHOD}")
        
        # Use client-provided session ID or generate a new one
        session_id = request.sessionId if request.sessionId else str(uuid4())
        
        # Initialize transcription session
        session = session_manager.create_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize transcription session"
            )
        
        logger.info(f"Started transcription session: {session_id}")
        
        return {
            "sessionId": session_id,
            "status": "ready",
            "message": "Transcription session initialized",
            "service": "whisper-1"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start transcription session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize transcription session"
        )