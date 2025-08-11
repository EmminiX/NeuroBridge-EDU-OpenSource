"""
OpenAI Whisper transcription service
Handles audio chunk transcription with Whisper API using user-provided API keys
"""

import os
import tempfile
import asyncio
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI
from services.audio.processor import AudioProcessor
from services.openai.client import get_default_openai_client
from utils.logger import get_logger
from config import settings

logger = get_logger("whisper.transcribe")


class WhisperTranscriber:
    """Handles OpenAI Whisper transcription with user-provided API keys"""
    
    # Common Whisper hallucination patterns
    HALLUCINATION_PATTERNS = [
        r'^(thank you[.!]?\s*)+$',
        r'^(thanks[.!]?\s*)+$',
        r'^(bye[.!]?\s*)+$',
        r'^(goodbye[.!]?\s*)+$',
        r'^(psst[,.]?\s*)+$',
        r'^(you[.!]?\s*)+$',
        r'^\.$',  # Just a period
        r'^\.\.+$',  # Multiple periods
        r'^(\s*\.\s*)+$',  # Spaced periods
        r'^(please subscribe|like and subscribe|thanks for watching)[.!]?$',
        r'^(music|applause|laughter)$',
        r'^\[.*\]$',  # Anything in brackets like [Music]
        r'^\(.*\)$',  # Anything in parentheses
    ]
    
    def __init__(self):
        """Initialize Whisper transcriber with dynamic API key management"""
        self.audio_processor = AudioProcessor()
        self.hallucination_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.HALLUCINATION_PATTERNS]
        self._sync_client: Optional[OpenAI] = None
        logger.info("Whisper transcriber initialized with dynamic API key support")
    
    async def _get_sync_client(self) -> OpenAI:
        """Get synchronous OpenAI client for Whisper API (which doesn't support async)"""
        if self._sync_client:
            return self._sync_client
        
        try:
            # Get async client first
            async_client = await get_default_openai_client()
            
            # Extract API key to create sync client
            # Note: This is a workaround since Whisper API doesn't support async
            api_key = async_client.api_key
            self._sync_client = OpenAI(api_key=api_key)
            
            logger.info("Synchronous OpenAI client initialized for Whisper")
            return self._sync_client
            
        except Exception as e:
            logger.error(f"Failed to initialize sync OpenAI client: {e}")
            raise RuntimeError("No OpenAI API key available for Whisper transcription")
    
    async def transcribe_chunk(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Transcribe audio chunk using OpenAI Whisper
        
        Args:
            pcm_data: Raw PCM16 audio bytes
            session_id: Unique session identifier
            
        Returns:
            Transcription result with metadata
        """
        try:
            # Calculate audio levels for debugging
            audio_stats = self.audio_processor.calculate_audio_levels(pcm_data)
            
            logger.debug(f"Session {session_id}: Audio stats - "
                        f"Max: {audio_stats['max_level']:.6f}, "
                        f"RMS: {audio_stats['rms_level']:.6f}, "
                        f"dBFS: {audio_stats['dbfs']:.2f}, "
                        f"Silent: {audio_stats['is_silent']}, "
                        f"Duration: {audio_stats['duration_ms']:.0f}ms")
            
            # Balanced silence detection - only skip true silence to prevent hallucinations
            # But remain sensitive enough to catch quiet speech
            if audio_stats['is_silent'] and audio_stats['dbfs'] < -50 and audio_stats['max_level'] < 0.0005:
                logger.info(f"Skipping silent audio chunk for {session_id}: "
                          f"max={audio_stats['max_level']:.6f}, "
                          f"RMS={audio_stats['rms_level']:.6f}, "
                          f"dBFS={audio_stats['dbfs']:.2f}")
                return {
                    'transcript': '',
                    'confidence': 0.0,
                    'is_final': True,
                    'audio_stats': audio_stats,
                    'skip_reason': 'silent_audio'
                }
            
            # Convert PCM to WAV format with headers
            wav_data = self.audio_processor.pcm_to_wav(pcm_data)
            
            # Save WAV to temporary file (Whisper API requires file input)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                # Get OpenAI client
                client = await self._get_sync_client()
                
                # Call Whisper API for transcription
                with open(temp_file_path, 'rb') as audio_file:
                    # Run synchronous API call in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="en",  # Specify English for better accuracy
                            prompt=""  # Empty prompt to reduce hallucination bias
                        )
                    )
                
                # Extract transcript
                transcript = response.text.strip() if hasattr(response, 'text') else ''
                
                # Filter out common hallucinations
                filtered_transcript = self._filter_hallucinations(transcript, audio_stats)
                
                result = {
                    'transcript': filtered_transcript,
                    'confidence': 1.0 if filtered_transcript else 0.0,  # Whisper doesn't provide confidence scores
                    'is_final': True,
                    'audio_stats': audio_stats,
                    'model': 'whisper-1',
                    'original_transcript': transcript if transcript != filtered_transcript else None
                }
                
                # Log results with clear visibility
                if filtered_transcript:
                    logger.info(f"✅ WHISPER TRANSCRIPTION SUCCESS for {session_id}:")
                    logger.info(f"   📝 Text: '{filtered_transcript}'")
                    logger.info(f"   📊 Length: {len(filtered_transcript)} characters")
                elif transcript and not filtered_transcript:
                    logger.warning(f"🚫 FILTERED HALLUCINATION for {session_id}: '{transcript}'")
                    logger.warning(f"   Audio levels: max={audio_stats['max_level']:.6f}, "
                                  f"RMS={audio_stats['rms_level']:.6f}, "
                                  f"dBFS={audio_stats['dbfs']:.2f}")
                else:
                    logger.warning(f"⚠️ WHISPER RETURNED EMPTY for {session_id}")
                    logger.warning(f"   Audio levels: max={audio_stats['max_level']:.6f}, "
                                  f"RMS={audio_stats['rms_level']:.6f}, "
                                  f"dBFS={audio_stats['dbfs']:.2f}")
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Transcription failed for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'is_final': True,
                'error': str(e),
                'audio_stats': self.audio_processor.calculate_audio_levels(pcm_data) if pcm_data else {}
            }
    
    async def transcribe_final(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Perform final transcription with enhanced processing
        
        Args:
            pcm_data: Complete audio buffer for session
            session_id: Session identifier
            
        Returns:
            Final transcription result
        """
        try:
            # Convert PCM to WAV format
            wav_data = self.audio_processor.pcm_to_wav(pcm_data)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(wav_data)
                temp_file_path = temp_file.name
            
            try:
                # Get OpenAI client
                client = await self._get_sync_client()
                
                # Call Whisper API with additional parameters for final transcription
                with open(temp_file_path, 'rb') as audio_file:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="en",
                            prompt=""  # Empty prompt to reduce hallucination
                        )
                    )
                
                transcript = response.text.strip() if hasattr(response, 'text') else ''
                
                # Filter hallucinations from final transcript
                filtered_transcript = self._filter_hallucinations(transcript, self.audio_processor.calculate_audio_levels(pcm_data))
                
                result = {
                    'transcript': filtered_transcript,
                    'confidence': 1.0 if filtered_transcript else 0.0,
                    'paragraphs': [filtered_transcript] if filtered_transcript else [],  # Simple paragraph split
                    'utterances': [],  # Whisper doesn't provide word-level timing
                    'model': 'whisper-1',
                    'is_final': True,
                    'audio_stats': self.audio_processor.calculate_audio_levels(pcm_data)
                }
                
                logger.info(f"Final transcription for session {session_id}: "
                           f"{len(transcript)} characters")
                
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Final transcription failed for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'paragraphs': [],
                'utterances': [],
                'error': str(e),
                'is_final': True,
                'audio_stats': self.audio_processor.calculate_audio_levels(pcm_data) if pcm_data else {}
            }
    
    def _filter_hallucinations(self, transcript: str, audio_stats: Dict[str, Any]) -> str:
        """
        Filter out common Whisper hallucinations
        
        Args:
            transcript: Raw transcript from Whisper
            audio_stats: Audio statistics for context
            
        Returns:
            Filtered transcript with hallucinations removed
        """
        if not transcript:
            return ''
        
        # Check if transcript matches any hallucination pattern
        for pattern in self.hallucination_regex:
            if pattern.match(transcript.strip()):
                logger.info(f"Detected hallucination pattern: '{transcript}' "
                          f"(Audio: max={audio_stats.get('max_level', 0):.6f}, "
                          f"dBFS={audio_stats.get('dbfs', -100):.2f})")
                return ''
        
        # Check for repetitive patterns (e.g., "Thank you. Thank you. Thank you.")
        words = transcript.strip().split()
        if len(words) > 2:
            # Check if all words are the same or follow a repetitive pattern
            unique_words = set(w.lower().rstrip('.,!?') for w in words)
            if len(unique_words) <= 2 and len(words) > 4:
                logger.info(f"Detected repetitive hallucination: '{transcript}'")
                return ''
        
        # Filter transcripts that are suspiciously common in very low audio scenarios
        # Changed from -35 to -45 dBFS to avoid filtering legitimate quiet speech
        if audio_stats.get('dbfs', 0) < -45:  # Very low audio level (near silence)
            suspicious_phrases = ['thank you', 'thanks', 'bye', 'goodbye', 'you', 'yeah', 'okay', 'oh']
            transcript_lower = transcript.lower().strip().rstrip('.,!?')
            if transcript_lower in suspicious_phrases:
                logger.info(f"Filtered low-confidence hallucination: '{transcript}' "
                          f"(dBFS={audio_stats.get('dbfs', -100):.2f})")
                return ''
        
        return transcript