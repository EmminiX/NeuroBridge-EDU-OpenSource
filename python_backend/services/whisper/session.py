"""
Whisper session management service
Handles transcription sessions with proper isolation and cleanup
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from services.whisper.hybrid_transcribe import HybridWhisperTranscriber, TranscriptionMethod
from services.audio.processor import AudioProcessor
from services.audio.saver import AudioSaver
from utils.logger import get_logger

logger = get_logger("whisper.session")


@dataclass
class SessionData:
    """Data structure for managing transcription session state"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    audio_buffer: bytes = b''
    chunk_count: int = 0
    total_duration: float = 0.0
    is_active: bool = True
    sse_clients: List[Any] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    

class SessionManager:
    """Manages transcription sessions with proper isolation and cleanup"""
    
    def __init__(self, 
                 enable_debug_audio: bool = True,
                 local_model_size: str = "base",
                 transcription_method: TranscriptionMethod = TranscriptionMethod.LOCAL_FIRST):
        """
        Initialize session manager
        
        Args:
            enable_debug_audio: Whether to save audio chunks for debugging
            local_model_size: Whisper model size for local processing
            transcription_method: Default transcription method
        """
        self._sessions: Dict[str, SessionData] = {}
        self._transcriber = HybridWhisperTranscriber(
            local_model_size=local_model_size,
            method=transcription_method
        )
        self._audio_processor = AudioProcessor()
        self._audio_saver = AudioSaver() if enable_debug_audio else None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"Hybrid Whisper session manager initialized - Method: {transcription_method.value}, Model: {local_model_size}")
    
    def create_session(self, session_id: str) -> SessionData:
        """
        Create a new transcription session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Created session data
        """
        if session_id in self._sessions:
            logger.warning(f"Session {session_id} already exists, returning existing")
            return self._sessions[session_id]
        
        session = SessionData(session_id=session_id)
        self._sessions[session_id] = session
        
        logger.info(f"Created transcription session: {session_id}")
        
        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())
        
        return session
    
    async def process_audio_chunk(self, session_id: str, pcm_data: bytes) -> Dict[str, Any]:
        """
        Process an audio chunk for a session
        
        Args:
            session_id: Session identifier
            pcm_data: Raw PCM16 audio bytes
            
        Returns:
            Processing result with transcript and metadata
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return {
                'success': False,
                'error': 'Session not found'
            }
        
        if not session.is_active:
            logger.warning(f"Session inactive: {session_id}")
            return {
                'success': False,
                'error': 'Session is inactive'
            }
        
        # Update session activity
        session.last_activity = datetime.utcnow()
        session.chunk_count += 1
        
        # Append to buffer
        session.audio_buffer += pcm_data
        
        # Calculate duration (16kHz, 16-bit mono)
        chunk_duration_ms = (len(pcm_data) / 2 / 16000) * 1000
        session.total_duration += chunk_duration_ms
        
        # Save debug audio if enabled
        if self._audio_saver:
            try:
                saved_path = self._audio_saver.save_pcm_chunk(
                    pcm_data, session_id, session.chunk_count
                )
                if saved_path:
                    logger.info(f"Saved audio chunk: {saved_path}")
            except Exception as e:
                logger.error(f"Failed to save debug audio: {e}")
        
        # Validate PCM format
        if not self._audio_processor.validate_pcm_format(pcm_data):
            logger.warning(f"Invalid PCM format for session {session_id}")
            return {
                'success': False,
                'error': 'Invalid PCM format'
            }
        
        # Calculate audio statistics
        audio_stats = self._audio_processor.calculate_audio_levels(pcm_data)
        
        # Process with Whisper transcriber
        try:
            result = await self._transcriber.transcribe_chunk(pcm_data, session_id)
            
            response = {
                'success': True,
                'chunk_index': session.chunk_count,
                'transcript': result.get('transcript', ''),
                'confidence': result.get('confidence', 0.0),
                'audio_stats': audio_stats,
                'total_duration_ms': session.total_duration
            }
            
            # Broadcast to SSE clients if transcript is not empty
            if result.get('transcript'):
                transcript_data = {
                    'type': 'transcript',
                    'text': result.get('transcript', ''),
                    'confidence': result.get('confidence', 0.0),
                    'chunkIndex': session.chunk_count,
                    'totalDuration': session.total_duration
                }
                logger.info(f"📡 BROADCASTING TO SSE for {session_id}:")
                logger.info(f"   Connected clients: {len(session.sse_clients)}")
                logger.info(f"   Transcript: '{result.get('transcript', '')[:50]}...'")
                await self.broadcast_to_sse_clients(session_id, transcript_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Transcription failed for session {session_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'audio_stats': audio_stats
            }
    
    async def finalize_session(self, session_id: str) -> Dict[str, Any]:
        """
        Finalize a transcription session and get final transcript
        
        Args:
            session_id: Session identifier
            
        Returns:
            Final transcription result
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot finalize - session not found: {session_id}")
            return {
                'success': False,
                'error': 'Session not found'
            }
        
        session.is_active = False
        
        # Get final transcription if we have audio
        final_transcript = ""
        confidence = 0.0
        
        if session.audio_buffer:
            try:
                result = await self._transcriber.transcribe_final(
                    session.audio_buffer, session_id
                )
                final_transcript = result.get('transcript', '')
                confidence = result.get('confidence', 0.0)
            except Exception as e:
                logger.error(f"Final transcription failed for session {session_id}: {e}")
        else:
            logger.warning(f"No audio data for session {session_id}")
        
        logger.info(f"Finalized session {session_id}: {len(final_transcript)} chars, "
                   f"{session.chunk_count} chunks, {session.total_duration:.0f}ms")
        
        return {
            'success': True,
            'session_id': session_id,
            'transcript': final_transcript,
            'confidence': confidence,
            'chunk_count': session.chunk_count,
            'total_duration_ms': session.total_duration
        }
    
    def cleanup_session(self, session_id: str):
        """
        Clean up a session and free resources
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleaned up session: {session_id}")
    
    async def _cleanup_inactive_sessions(self):
        """Background task to clean up inactive sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                now = datetime.utcnow()
                inactive_threshold = timedelta(minutes=5)
                
                sessions_to_cleanup = []
                for session_id, session in self._sessions.items():
                    if not session.is_active and (now - session.last_activity) > inactive_threshold:
                        sessions_to_cleanup.append(session_id)
                
                for session_id in sessions_to_cleanup:
                    self.cleanup_session(session_id)
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID"""
        return self._sessions.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return [sid for sid, session in self._sessions.items() if session.is_active]
    
    async def add_sse_client(self, session_id: str, sse_client: Any) -> bool:
        """
        Add an SSE client to a session for real-time updates
        
        Args:
            session_id: Session identifier
            sse_client: SSE client object
            
        Returns:
            True if client was added successfully, False otherwise
        """
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            logger.warning(f"Cannot add SSE client - session not found or inactive: {session_id}")
            return False
        
        session.sse_clients.append(sse_client)
        logger.info(f"Added SSE client to session {session_id} (total clients: {len(session.sse_clients)})")
        return True
    
    async def broadcast_to_sse_clients(self, session_id: str, data: Dict[str, Any]):
        """
        Broadcast data to all SSE clients connected to a session
        
        Args:
            session_id: Session identifier
            data: Data to broadcast
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot broadcast - session {session_id} not found")
            return
        
        if not session.sse_clients:
            logger.warning(f"No SSE clients connected to session {session_id}")
            return
        
        # Send to all connected SSE clients
        successful_sends = 0
        for client in session.sse_clients[:]:  # Copy list to avoid modification during iteration
            try:
                await client.send_json(data)
                successful_sends += 1
                logger.debug(f"✅ Sent transcript to SSE client {successful_sends}/{len(session.sse_clients)}")
            except Exception as e:
                logger.error(f"Failed to send to SSE client: {e}")
                session.sse_clients.remove(client)
        
        if successful_sends > 0:
            logger.info(f"📤 Successfully broadcasted to {successful_sends} SSE client(s)")
    
    def set_transcription_method(self, method: TranscriptionMethod):
        """Change the transcription method for all new sessions"""
        self._transcriber.set_method(method)
        logger.info(f"Session manager transcription method changed to: {method.value}")
    
    def get_transcription_status(self) -> Dict[str, Any]:
        """Get current transcription status and performance"""
        return self._transcriber.get_status()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._transcriber.get_performance_stats()
    
    async def cleanup(self):
        """Cleanup session manager resources"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        await self._transcriber.cleanup()
        logger.info("Session manager cleanup completed")


# Global session manager instance
def create_session_manager():
    """Create session manager with configuration-driven settings"""
    from config import settings
    
    # Map string configuration to enum
    method_map = {
        'local_only': TranscriptionMethod.LOCAL_ONLY,
        'api_only': TranscriptionMethod.API_ONLY,
        'local_first': TranscriptionMethod.LOCAL_FIRST,
        'auto': TranscriptionMethod.AUTO
    }
    
    transcription_method = method_map.get(
        settings.TRANSCRIPTION_METHOD.lower(), 
        TranscriptionMethod.LOCAL_FIRST
    )
    
    return SessionManager(
        enable_debug_audio=True,
        local_model_size=settings.LOCAL_WHISPER_MODEL_SIZE,
        transcription_method=transcription_method
    )

session_manager = create_session_manager()