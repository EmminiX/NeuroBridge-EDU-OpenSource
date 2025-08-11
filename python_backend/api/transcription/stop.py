"""
Transcription Session Stop Endpoint
POST /api/transcribe/stop - End transcription session and cleanup
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.whisper.session import session_manager
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("transcription.stop")


class StopTranscriptionRequest(BaseModel):
    """Request model for stopping transcription"""
    sessionId: str


@router.post("/stop")
async def stop_transcription_session(request: StopTranscriptionRequest):
    """
    Stop transcription session and perform complete finalization
    Processes all audio buffers and returns final enhanced transcript
    """
    try:
        session_id = request.sessionId
        
        # Finalize session with complete audio processing
        result = await session_manager.finalize_session(session_id)
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown finalization error')
            logger.error(f"Session finalization failed: {error_msg}")
            
            # Even if finalization fails, attempt cleanup
            session_manager.cleanup_session(session_id)
            
            return {
                "sessionId": session_id,
                "status": "stopped_with_errors",
                "finalTranscript": "",
                "error": error_msg,
                "message": "Session stopped but finalization encountered errors"
            }
        
        # Schedule cleanup after short delay to allow SSE clients to receive final results
        import asyncio
        asyncio.create_task(_delayed_cleanup(session_id))
        
        # Prepare comprehensive response
        response = {
            "sessionId": session_id,
            "status": "stopped",
            "finalTranscript": result.get('transcript', ''),
            "confidence": result.get('confidence', 0.0),
            "totalChunks": result.get('total_chunks', 0),
            "totalDurationMs": result.get('total_duration_ms', 0),
            "paragraphs": result.get('paragraphs', []),
            "utterances": result.get('utterances', []),
            "audioStats": result.get('audio_stats', {}),
            "model": "whisper-1",
            "message": "Transcription session completed successfully"
        }
        
        logger.info(f"Successfully stopped session {session_id}: "
                   f"{len(result.get('transcript', ''))} characters, "
                   f"{result.get('total_chunks', 0)} chunks processed")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop transcription session {request.sessionId}: {e}")
        
        # Attempt emergency cleanup
        try:
            session_manager.cleanup_session(request.sessionId)
        except Exception as cleanup_error:
            logger.error(f"Emergency cleanup also failed: {cleanup_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop transcription session: {str(e)}"
        )


async def _delayed_cleanup(session_id: str):
    """Cleanup session after delay to allow SSE clients to receive final data"""
    import asyncio
    try:
        # Wait 5 seconds for SSE clients to receive final results
        await asyncio.sleep(5.0)
        session_manager.cleanup_session(session_id)
        logger.debug(f"Delayed cleanup completed for session: {session_id}")
    except Exception as e:
        logger.error(f"Delayed cleanup failed for session {session_id}: {e}")