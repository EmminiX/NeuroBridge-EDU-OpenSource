"""
Transcription Configuration API
Endpoints for managing transcription methods and model settings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from services.whisper.session import session_manager
from services.whisper.hybrid_transcribe import TranscriptionMethod
from utils.logger import get_logger

logger = get_logger("api.transcription.config")
router = APIRouter()


class TranscriptionConfigRequest(BaseModel):
    """Request model for updating transcription configuration"""
    method: str  # local_only, api_only, local_first, auto
    local_model_size: str = "base"  # tiny, base, small, medium, large-v2, large-v3


class TranscriptionConfigResponse(BaseModel):
    """Response model for transcription configuration"""
    success: bool
    current_method: str
    local_model_size: str
    local_model_loaded: bool
    performance_stats: Dict[str, Any]
    message: str = ""


@router.get("/config")
async def get_transcription_config():
    """
    Get current transcription configuration and status
    
    Returns:
        Current configuration and performance statistics
    """
    try:
        status = session_manager.get_transcription_status()
        performance = session_manager.get_performance_stats()
        
        return TranscriptionConfigResponse(
            success=True,
            current_method=status['method'],
            local_model_size=status['local_model_info']['model_size'],
            local_model_loaded=status['local_model_loaded'],
            performance_stats=performance,
            message="Configuration retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get transcription config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.post("/config")
async def update_transcription_config(request: TranscriptionConfigRequest):
    """
    Update transcription configuration
    
    Args:
        request: Configuration update request
        
    Returns:
        Updated configuration status
    """
    try:
        # Validate transcription method
        method_map = {
            'local_only': TranscriptionMethod.LOCAL_ONLY,
            'api_only': TranscriptionMethod.API_ONLY,
            'local_first': TranscriptionMethod.LOCAL_FIRST,
            'auto': TranscriptionMethod.AUTO
        }
        
        if request.method not in method_map:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid transcription method. Must be one of: {list(method_map.keys())}"
            )
        
        # Validate model size
        valid_model_sizes = ['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3']
        if request.local_model_size not in valid_model_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model size. Must be one of: {valid_model_sizes}"
            )
        
        # Update transcription method
        new_method = method_map[request.method]
        session_manager.set_transcription_method(new_method)
        
        # Note: Model size change requires restart for now
        # In a production system, you might want to implement hot model swapping
        
        # Get updated status
        status = session_manager.get_transcription_status()
        performance = session_manager.get_performance_stats()
        
        message = f"Transcription method updated to {request.method}"
        if request.local_model_size != status['local_model_info']['model_size']:
            message += f". Note: Model size change to {request.local_model_size} requires application restart."
        
        return TranscriptionConfigResponse(
            success=True,
            current_method=status['method'],
            local_model_size=status['local_model_info']['model_size'],
            local_model_loaded=status['local_model_loaded'],
            performance_stats=performance,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update transcription config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/status")
async def get_transcription_status():
    """
    Get detailed transcription status including performance metrics
    
    Returns:
        Detailed status information
    """
    try:
        status = session_manager.get_transcription_status()
        performance = session_manager.get_performance_stats()
        active_sessions = session_manager.get_active_sessions()
        
        return {
            'success': True,
            'transcription_status': status,
            'performance_stats': performance,
            'active_sessions': len(active_sessions),
            'session_ids': active_sessions[:5],  # Show first 5 session IDs
            'available_methods': [method.value for method in TranscriptionMethod],
            'available_model_sizes': ['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3']
        }
        
    except Exception as e:
        logger.error(f"Failed to get transcription status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/test-local")
async def test_local_transcription():
    """
    Test local Whisper model availability and performance
    
    Returns:
        Test results and model information
    """
    try:
        import numpy as np
        from services.whisper.local_transcribe import LocalWhisperTranscriber
        
        # Create test transcriber
        test_transcriber = LocalWhisperTranscriber(model_size="tiny")  # Use smallest model for test
        
        # Generate test audio (1 second of silence)
        test_audio = np.zeros(16000 * 2, dtype=np.int16)  # 2 seconds of silence
        test_pcm_data = test_audio.tobytes()
        
        # Test transcription
        import time
        start_time = time.time()
        
        result = await test_transcriber.transcribe_chunk(test_pcm_data, "test_session")
        
        test_time = time.time() - start_time
        
        # Cleanup
        await test_transcriber.unload_model()
        
        return {
            'success': True,
            'local_available': True,
            'model_info': test_transcriber.get_model_info(),
            'test_duration_seconds': round(test_time, 3),
            'test_result': {
                'transcript': result.get('transcript', ''),
                'processing_method': result.get('processing_method', ''),
                'device': result.get('device', ''),
                'model': result.get('model', '')
            },
            'message': f"Local Whisper test completed in {test_time:.3f}s"
        }
        
    except ImportError as e:
        logger.warning(f"Local Whisper dependencies not available: {e}")
        return {
            'success': False,
            'local_available': False,
            'error': 'Missing dependencies: faster-whisper, torch, or ctranslate2',
            'message': 'Install dependencies with: pip install faster-whisper torch ctranslate2'
        }
    except Exception as e:
        logger.error(f"Local transcription test failed: {e}")
        return {
            'success': False,
            'local_available': False,
            'error': str(e),
            'message': 'Local Whisper test failed'
        }


@router.post("/reset-stats")
async def reset_performance_stats():
    """
    Reset performance statistics
    
    Returns:
        Confirmation of stats reset
    """
    try:
        # Reset stats in the transcriber
        session_manager._transcriber.performance_stats = {
            'local_success_count': 0,
            'local_failure_count': 0,
            'api_success_count': 0,
            'api_failure_count': 0,
            'local_avg_time': 0.0,
            'api_avg_time': 0.0,
            'total_requests': 0
        }
        
        logger.info("Performance statistics reset")
        
        return {
            'success': True,
            'message': 'Performance statistics have been reset',
            'new_stats': session_manager.get_performance_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to reset performance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset stats: {str(e)}")


@router.get("/models")
async def get_available_models():
    """
    Get information about available Whisper models
    
    Returns:
        Model information and recommendations
    """
    return {
        'success': True,
        'models': {
            'tiny': {
                'parameters': '39M',
                'relative_speed': '~32x',
                'vram_required': '~1GB',
                'accuracy': 'Lower',
                'recommended_for': 'Testing, resource-constrained environments'
            },
            'base': {
                'parameters': '74M', 
                'relative_speed': '~16x',
                'vram_required': '~1GB',
                'accuracy': 'Good',
                'recommended_for': 'Default choice for most applications'
            },
            'small': {
                'parameters': '244M',
                'relative_speed': '~6x', 
                'vram_required': '~2GB',
                'accuracy': 'Better',
                'recommended_for': 'Production use with good hardware'
            },
            'medium': {
                'parameters': '769M',
                'relative_speed': '~2x',
                'vram_required': '~5GB', 
                'accuracy': 'Very Good',
                'recommended_for': 'High-accuracy requirements'
            },
            'large-v2': {
                'parameters': '1550M',
                'relative_speed': '1x',
                'vram_required': '~10GB',
                'accuracy': 'Excellent',
                'recommended_for': 'Maximum accuracy, powerful hardware'
            },
            'large-v3': {
                'parameters': '1550M',
                'relative_speed': '1x', 
                'vram_required': '~10GB',
                'accuracy': 'Best',
                'recommended_for': 'Latest model, best accuracy'
            }
        },
        'recommendations': {
            'development': 'base',
            'production_cpu': 'base or small',
            'production_gpu': 'small or medium',
            'high_accuracy': 'large-v3'
        }
    }