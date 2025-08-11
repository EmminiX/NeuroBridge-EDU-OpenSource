"""
Transcription Session Start Endpoint
POST /api/transcribe/start - Initialize new transcription session
"""

from fastapi import APIRouter, HTTPException
from uuid import uuid4
from services.whisper.session import session_manager
from utils.logger import get_logger
from pydantic import BaseModel
from typing import Optional
from config import settings

router = APIRouter()
logger = get_logger("transcription.start")


@router.get("/test")
async def test_transcription_service():
    """
    Test endpoint for checking transcription service availability
    Used by frontend to verify backend connectivity
    """
    try:
        # Check if OpenAI API key is available
        api_key = settings.OPENAI_API_KEY
        is_available = bool(api_key)
        
        return {
            "status": "healthy",
            "service": "transcription",
            "whisper_available": is_available,
            "message": "Transcription service is ready" if is_available else "Transcription service requires OPENAI_API_KEY"
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
async def start_transcription_session(request: SessionStartRequest):
    """
    Start a new transcription session
    Accepts optional sessionId from client or generates a new one
    """
    try:
        # Check if OpenAI API key is available
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="Transcription service unavailable - check OPENAI_API_KEY"
            )
        
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