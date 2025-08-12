"""
Hybrid Whisper Transcription Service
Combines local Whisper processing with OpenAI API fallback
"""

import asyncio
import time
from typing import Dict, Any, Optional
from enum import Enum
from utils.logger import get_logger
from .local_transcribe import LocalWhisperTranscriber
from .transcribe import WhisperTranscriber

logger = get_logger("whisper.hybrid")


class TranscriptionMethod(Enum):
    """Transcription method preferences"""
    LOCAL_ONLY = "local_only"
    API_ONLY = "api_only"
    LOCAL_FIRST = "local_first"  # Try local, fallback to API
    AUTO = "auto"  # Intelligent selection based on performance


class HybridWhisperTranscriber:
    """
    Hybrid transcription service that intelligently selects between local and API processing
    """
    
    def __init__(
        self, 
        local_model_size: str = "base",
        method: TranscriptionMethod = TranscriptionMethod.LOCAL_FIRST,
        local_timeout: float = 120.0,  # Increased timeout for initial model loading
        api_timeout: float = 60.0
    ):
        """
        Initialize hybrid transcriber
        
        Args:
            local_model_size: Whisper model size for local processing
            method: Processing method preference
            local_timeout: Timeout for local processing (seconds)
            api_timeout: Timeout for API processing (seconds)
        """
        self.method = method
        self.local_timeout = local_timeout
        self.api_timeout = api_timeout
        
        # Initialize transcribers
        self.local_transcriber = LocalWhisperTranscriber(model_size=local_model_size)
        self.api_transcriber = WhisperTranscriber()
        
        # Performance tracking
        self.performance_stats = {
            'local_success_count': 0,
            'local_failure_count': 0,
            'api_success_count': 0,
            'api_failure_count': 0,
            'local_avg_time': 0.0,
            'api_avg_time': 0.0,
            'total_requests': 0
        }
        
        logger.info(f"Hybrid Whisper transcriber initialized - Method: {method.value}, Local model: {local_model_size}")
    
    async def transcribe_chunk(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Transcribe audio chunk using hybrid approach
        
        Args:
            pcm_data: Raw PCM16 audio bytes
            session_id: Unique session identifier
            
        Returns:
            Transcription result with metadata
        """
        self.performance_stats['total_requests'] += 1
        
        if self.method == TranscriptionMethod.API_ONLY:
            return await self._transcribe_with_api(pcm_data, session_id)
        elif self.method == TranscriptionMethod.LOCAL_ONLY:
            return await self._transcribe_with_local(pcm_data, session_id)
        elif self.method == TranscriptionMethod.LOCAL_FIRST:
            return await self._transcribe_local_first(pcm_data, session_id)
        elif self.method == TranscriptionMethod.AUTO:
            return await self._transcribe_auto(pcm_data, session_id)
        else:
            # Default to local first
            return await self._transcribe_local_first(pcm_data, session_id)
    
    async def transcribe_final(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Perform final transcription using hybrid approach
        
        Args:
            pcm_data: Complete audio buffer for session
            session_id: Session identifier
            
        Returns:
            Final transcription result
        """
        if self.method == TranscriptionMethod.API_ONLY:
            return await self._transcribe_final_with_api(pcm_data, session_id)
        elif self.method == TranscriptionMethod.LOCAL_ONLY:
            return await self._transcribe_final_with_local(pcm_data, session_id)
        elif self.method == TranscriptionMethod.LOCAL_FIRST:
            return await self._transcribe_final_local_first(pcm_data, session_id)
        elif self.method == TranscriptionMethod.AUTO:
            return await self._transcribe_final_auto(pcm_data, session_id)
        else:
            return await self._transcribe_final_local_first(pcm_data, session_id)
    
    async def _transcribe_with_local(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Transcribe using local Whisper only"""
        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                self.local_transcriber.transcribe_chunk(pcm_data, session_id),
                timeout=self.local_timeout
            )
            processing_time = time.time() - start_time
            
            self.performance_stats['local_success_count'] += 1
            self._update_avg_time('local', processing_time)
            
            result['processing_time'] = processing_time
            result['fallback_used'] = False
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Local transcription timeout for session {session_id}")
            self.performance_stats['local_failure_count'] += 1
            return {
                'transcript': '',
                'confidence': 0.0,
                'is_final': True,
                'error': 'Local transcription timeout',
                'processing_method': 'local_whisper_timeout',
                'fallback_used': False
            }
        except Exception as e:
            logger.error(f"Local transcription error for session {session_id}: {e}")
            self.performance_stats['local_failure_count'] += 1
            return {
                'transcript': '',
                'confidence': 0.0,
                'is_final': True,
                'error': str(e),
                'processing_method': 'local_whisper_error',
                'fallback_used': False
            }
    
    async def _transcribe_with_api(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Transcribe using OpenAI API only"""
        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                self.api_transcriber.transcribe_chunk(pcm_data, session_id),
                timeout=self.api_timeout
            )
            processing_time = time.time() - start_time
            
            self.performance_stats['api_success_count'] += 1
            self._update_avg_time('api', processing_time)
            
            result['processing_time'] = processing_time
            result['fallback_used'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"API transcription error for session {session_id}: {e}")
            self.performance_stats['api_failure_count'] += 1
            return {
                'transcript': '',
                'confidence': 0.0,
                'is_final': True,
                'error': str(e),
                'processing_method': 'api_whisper_error',
                'fallback_used': False
            }
    
    async def _transcribe_local_first(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Try local transcription first, fallback to API if needed"""
        logger.debug(f"Attempting local transcription first for session {session_id}")
        
        # Try local transcription
        local_result = await self._transcribe_with_local(pcm_data, session_id)
        
        # Check if local transcription was successful
        if (local_result.get('transcript') and 
            not local_result.get('error') and 
            local_result.get('confidence', 0) > 0.1):
            logger.debug(f"Local transcription successful for session {session_id}")
            return local_result
        
        # Fallback to API
        logger.info(f"Falling back to API transcription for session {session_id}")
        api_result = await self._transcribe_with_api(pcm_data, session_id)
        api_result['fallback_used'] = True
        api_result['primary_method'] = 'local_whisper'
        api_result['fallback_reason'] = local_result.get('error', 'low_confidence_or_empty')
        
        return api_result
    
    async def _transcribe_auto(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Intelligently select transcription method based on performance"""
        # Simple auto-selection logic based on recent performance
        local_success_rate = self._get_success_rate('local')
        api_success_rate = self._get_success_rate('api')
        
        # If we have enough data, prefer the method with better performance
        if self.performance_stats['total_requests'] > 10:
            local_avg_time = self.performance_stats['local_avg_time']
            api_avg_time = self.performance_stats['api_avg_time']
            
            # Prefer local if it's faster and reliable
            if (local_success_rate >= 0.8 and 
                local_avg_time > 0 and 
                (api_avg_time == 0 or local_avg_time < api_avg_time * 1.5)):
                return await self._transcribe_with_local(pcm_data, session_id)
            elif api_success_rate >= 0.8:
                return await self._transcribe_with_api(pcm_data, session_id)
        
        # Default to local-first approach
        return await self._transcribe_local_first(pcm_data, session_id)
    
    async def _transcribe_final_with_local(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Final transcription using local Whisper only"""
        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                self.local_transcriber.transcribe_final(pcm_data, session_id),
                timeout=self.local_timeout * 2  # Longer timeout for final transcription
            )
            processing_time = time.time() - start_time
            
            result['processing_time'] = processing_time
            result['fallback_used'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Final local transcription error for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'paragraphs': [],
                'utterances': [],
                'error': str(e),
                'processing_method': 'local_whisper_error',
                'is_final': True,
                'fallback_used': False
            }
    
    async def _transcribe_final_with_api(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Final transcription using OpenAI API only"""
        try:
            start_time = time.time()
            result = await self.api_transcriber.transcribe_final(pcm_data, session_id)
            processing_time = time.time() - start_time
            
            result['processing_time'] = processing_time
            result['fallback_used'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Final API transcription error for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'paragraphs': [],
                'utterances': [],
                'error': str(e),
                'processing_method': 'api_whisper_error',
                'is_final': True,
                'fallback_used': False
            }
    
    async def _transcribe_final_local_first(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Final transcription: try local first, fallback to API"""
        logger.debug(f"Attempting final local transcription first for session {session_id}")
        
        # Try local transcription
        local_result = await self._transcribe_final_with_local(pcm_data, session_id)
        
        # Check if local transcription was successful
        if (local_result.get('transcript') and 
            not local_result.get('error') and 
            local_result.get('confidence', 0) > 0.1):
            logger.debug(f"Final local transcription successful for session {session_id}")
            return local_result
        
        # Fallback to API
        logger.info(f"Falling back to API for final transcription, session {session_id}")
        api_result = await self._transcribe_final_with_api(pcm_data, session_id)
        api_result['fallback_used'] = True
        api_result['primary_method'] = 'local_whisper'
        api_result['fallback_reason'] = local_result.get('error', 'low_confidence_or_empty')
        
        return api_result
    
    async def _transcribe_final_auto(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """Auto-select method for final transcription"""
        # For final transcription, prefer quality over speed
        local_success_rate = self._get_success_rate('local')
        
        if local_success_rate >= 0.7:  # Lower threshold for final transcription
            return await self._transcribe_final_with_local(pcm_data, session_id)
        else:
            return await self._transcribe_final_local_first(pcm_data, session_id)
    
    def _get_success_rate(self, method: str) -> float:
        """Calculate success rate for a transcription method"""
        if method == 'local':
            total = self.performance_stats['local_success_count'] + self.performance_stats['local_failure_count']
            if total == 0:
                return 0.0
            return self.performance_stats['local_success_count'] / total
        elif method == 'api':
            total = self.performance_stats['api_success_count'] + self.performance_stats['api_failure_count']
            if total == 0:
                return 0.0
            return self.performance_stats['api_success_count'] / total
        return 0.0
    
    def _update_avg_time(self, method: str, new_time: float):
        """Update average processing time for a method"""
        if method == 'local':
            current_avg = self.performance_stats['local_avg_time']
            count = self.performance_stats['local_success_count']
            if count <= 1:
                self.performance_stats['local_avg_time'] = new_time
            else:
                # Exponential moving average
                alpha = 0.1
                self.performance_stats['local_avg_time'] = alpha * new_time + (1 - alpha) * current_avg
        elif method == 'api':
            current_avg = self.performance_stats['api_avg_time']
            count = self.performance_stats['api_success_count']
            if count <= 1:
                self.performance_stats['api_avg_time'] = new_time
            else:
                # Exponential moving average
                alpha = 0.1
                self.performance_stats['api_avg_time'] = alpha * new_time + (1 - alpha) * current_avg
    
    def set_method(self, method: TranscriptionMethod):
        """Change the transcription method"""
        self.method = method
        logger.info(f"Transcription method changed to: {method.value}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.performance_stats,
            'local_success_rate': self._get_success_rate('local'),
            'api_success_rate': self._get_success_rate('api'),
            'current_method': self.method.value,
            'local_model_info': self.local_transcriber.get_model_info()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the hybrid transcriber"""
        return {
            'method': self.method.value,
            'local_model_loaded': self.local_transcriber.model is not None,
            'local_model_info': self.local_transcriber.get_model_info(),
            'performance': self.get_performance_stats()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.local_transcriber.unload_model()
        logger.info("Hybrid transcriber cleanup completed")