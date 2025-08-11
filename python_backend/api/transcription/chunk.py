"""
Audio Chunk Processing Endpoint
POST /api/transcribe/chunk - Process 2-second audio chunks with binary PCM data
"""

from fastapi import APIRouter, Request, Header, HTTPException
from services.whisper.session import session_manager
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("transcription.chunk")


@router.post("/chunk")
async def process_audio_chunk(
    request: Request,
    x_session_id: str = Header(None, alias="X-Session-ID"),
    content_type: str = Header(None, alias="Content-Type")
):
    """
    Process a single 2-second audio chunk with binary PCM data
    
    Headers:
        X-Session-ID: Transcription session identifier
        Content-Type: Should be 'application/octet-stream'
        
    Body: Raw PCM16 audio bytes (little-endian, 16kHz, mono)
    """
    if not x_session_id:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required"
        )
    
    try:
        # Read raw binary audio data
        pcm_data = await request.body()
        
        if not pcm_data:
            raise HTTPException(
                status_code=400,
                detail="No audio data received"
            )
        
        # Validate content type for debugging
        if content_type and "octet-stream" not in content_type.lower():
            logger.warning(f"Unexpected content-type: {content_type} "
                          f"(should be application/octet-stream)")
        
        # Validate PCM data size (should be multiple of 2 for 16-bit samples)
        if len(pcm_data) % 2 != 0:
            logger.warning(f"PCM data size not multiple of 2: {len(pcm_data)} bytes")
            # Trim to even length
            pcm_data = pcm_data[:-1]
        
        # Log detailed audio info for debugging silence issues
        logger.debug(f"Processing audio chunk for session {x_session_id}: "
                    f"{len(pcm_data)} bytes, "
                    f"~{len(pcm_data)/2} samples, "
                    f"~{(len(pcm_data)/2/16000)*1000:.0f}ms duration")
        
        # Process audio chunk through session manager
        result = await session_manager.process_audio_chunk(x_session_id, pcm_data)
        
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown processing error')
            logger.error(f"Audio processing failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Return processing result
        # Convert numpy bool to Python bool to avoid JSON serialization errors
        response = {
            "sessionId": x_session_id,
            "chunkIndex": result.get('chunk_index', 0),
            "bytesProcessed": len(pcm_data),
            "audioStats": {
                "maxLevel": f"{result['audio_stats']['max_level']:.6f}",
                "rmsLevel": f"{result['audio_stats']['rms_level']:.6f}",
                "dbfs": f"{result['audio_stats']['dbfs']:.2f}",
                "isSilent": bool(result['audio_stats']['is_silent']),  # Convert numpy.bool to Python bool
                "durationMs": f"{result['audio_stats']['duration_ms']:.0f}"
            },
            "transcript": result.get('transcript', ''),
            "confidence": result.get('confidence', 0.0),
            "totalDurationMs": result.get('total_duration_ms', 0),
            "status": "processed"
        }
        
        # Log audio level info to help debug silence issues
        stats = result['audio_stats']
        if stats['is_silent']:
            logger.info(f"Session {x_session_id}: SILENT CHUNK detected - "
                       f"Max: {stats['max_level']:.6f}, "
                       f"RMS: {stats['rms_level']:.6f}, "
                       f"dBFS: {stats['dbfs']:.2f}")
        else:
            logger.debug(f"Session {x_session_id}: Audio levels - "
                        f"Max: {stats['max_level']:.6f}, "
                        f"RMS: {stats['rms_level']:.6f}, "
                        f"dBFS: {stats['dbfs']:.2f}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process audio chunk for session {x_session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process audio chunk: {str(e)}"
        )