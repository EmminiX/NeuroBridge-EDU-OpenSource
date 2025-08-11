"""
Local Whisper Transcription Service
Handles audio transcription using local Whisper models with faster-whisper
"""

import os
import tempfile
import asyncio
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from services.audio.processor import AudioProcessor
from utils.logger import get_logger
from config import settings

# Optional imports for local Whisper - gracefully handle missing dependencies
try:
    import torch
    import numpy as np
    from faster_whisper import WhisperModel
    TORCH_AVAILABLE = True
except ImportError as e:
    TORCH_AVAILABLE = False
    torch = None
    np = None
    WhisperModel = None

logger = get_logger("whisper.local")


class LocalWhisperTranscriber:
    """Handles local Whisper transcription with GPU/CPU auto-detection"""
    
    # Common Whisper hallucination patterns (same as API version)
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
    
    def __init__(self, model_size: str = "base", device: Optional[str] = None):
        """
        Initialize local Whisper transcriber
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: Force specific device ("cuda", "cpu") or auto-detect
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch and faster-whisper not available. Local Whisper transcription disabled.")
            self.model = None
            self.device = "cpu"
            self.model_size = model_size
            return
        # Import here to avoid circular imports
        from config import settings
        
        self.model_size = model_size
        self.device = device or settings.LOCAL_WHISPER_DEVICE or self._detect_device()
        self.model: Optional[WhisperModel] = None
        self.audio_processor = AudioProcessor()
        self.hallucination_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.HALLUCINATION_PATTERNS]
        self._model_loading = False
        self.cache_dir = settings.WHISPER_CACHE or str(Path.home() / ".cache" / "whisper")
        
        # Create cache directory
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Local Whisper transcriber initialized - Model: {model_size}, Device: {self.device}, Cache: {self.cache_dir}")
    
    def _detect_device(self) -> str:
        """Auto-detect optimal device for processing"""
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            logger.info(f"CUDA detected: {gpu_count} GPU(s), {gpu_memory:.1f}GB VRAM")
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Apple Metal Performance Shaders (MPS) detected")
            return "mps"
        else:
            logger.info("Using CPU processing")
            return "cpu"
    
    async def _ensure_model_loaded(self) -> bool:
        """Ensure Whisper model is loaded and ready"""
        if self.model is not None:
            return True
            
        if self._model_loading:
            # Wait for concurrent loading to complete
            while self._model_loading:
                await asyncio.sleep(0.1)
            return self.model is not None
            
        try:
            self._model_loading = True
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            
            # Determine compute type based on device
            if self.device == "cuda":
                compute_type = "float16" if torch.cuda.is_available() else "int8"
            else:
                compute_type = "int8"
            
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type,
                    local_files_only=False,  # Allow download if not cached
                    download_root=self.cache_dir
                )
            )
            
            # Test model with dummy data
            test_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            segments, _ = self.model.transcribe(test_audio, language="en")
            list(segments)  # Consume generator to ensure model works
            
            logger.info(f"✅ Whisper model loaded successfully: {self.model_size}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model {self.model_size}: {e}")
            self.model = None
            return False
        finally:
            self._model_loading = False
    
    async def transcribe_chunk(self, pcm_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Transcribe audio chunk using local Whisper model
        
        Args:
            pcm_data: Raw PCM16 audio bytes
            session_id: Unique session identifier
            
        Returns:
            Transcription result with metadata
        """
        if not TORCH_AVAILABLE or self.model is None:
            logger.error("Local Whisper not available - cannot transcribe chunk")
            return {
                'success': False,
                'text': '',
                'error': 'Local Whisper transcription not available. Missing PyTorch/faster-whisper dependencies.',
                'processing_time': 0.0,
                'method': 'local_whisper',
                'model_size': self.model_size,
                'device': 'unavailable',
                'audio_stats': {}
            }
            
        try:
            # Calculate audio levels for debugging
            audio_stats = self.audio_processor.calculate_audio_levels(pcm_data)
            
            logger.debug(f"Session {session_id}: Audio stats - "
                        f"Max: {audio_stats['max_level']:.6f}, "
                        f"RMS: {audio_stats['rms_level']:.6f}, "
                        f"dBFS: {audio_stats['dbfs']:.2f}, "
                        f"Silent: {audio_stats['is_silent']}, "
                        f"Duration: {audio_stats['duration_ms']:.0f}ms")
            
            # Enhanced silence detection - skip true silence to prevent hallucinations
            if audio_stats['is_silent'] and audio_stats['dbfs'] < -50 and audio_stats['max_level'] < 0.0005:
                logger.info(f"Skipping silent audio chunk for {session_id}")
                return {
                    'transcript': '',
                    'confidence': 0.0,
                    'is_final': True,
                    'audio_stats': audio_stats,
                    'skip_reason': 'silent_audio',
                    'processing_method': 'local_whisper',
                    'model': f"whisper-{self.model_size}"
                }
            
            # Ensure model is loaded
            if not await self._ensure_model_loaded():
                raise RuntimeError("Failed to load Whisper model")
            
            # Convert PCM bytes to numpy array
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Resample if needed (Whisper expects 16kHz)
            if len(audio_array) > 0:
                # Simple resampling - for production, consider librosa for better quality
                target_length = int(len(audio_array) * 16000 / 48000) if len(audio_array) > 48000 else len(audio_array)
                if target_length != len(audio_array) and target_length > 0:
                    indices = np.linspace(0, len(audio_array) - 1, target_length)
                    audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)
            
            # Transcribe with local model
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_array,
                    language="en",
                    beam_size=1,  # Faster processing
                    best_of=1,    # Faster processing
                    temperature=0.0,  # Deterministic output
                    compression_ratio_threshold=2.4,
                    log_prob_threshold=-1.0,
                    no_captions_threshold=0.6,
                    condition_on_previous_text=False  # Reduce hallucinations
                )
            )
            
            # Extract transcript from segments
            transcript_parts = []
            total_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                if segment.text.strip():
                    transcript_parts.append(segment.text.strip())
                    total_confidence += getattr(segment, 'avg_logprob', 0.0)
                    segment_count += 1
            
            transcript = " ".join(transcript_parts).strip()
            
            # Calculate average confidence (convert from log prob)
            avg_confidence = 0.0
            if segment_count > 0 and total_confidence < 0:
                # Convert log probability to confidence (approximate)
                avg_confidence = min(1.0, max(0.0, 1.0 + (total_confidence / segment_count)))
            
            # Filter out common hallucinations
            filtered_transcript = self._filter_hallucinations(transcript, audio_stats)
            
            result = {
                'transcript': filtered_transcript,
                'confidence': avg_confidence if filtered_transcript else 0.0,
                'is_final': True,
                'audio_stats': audio_stats,
                'processing_method': 'local_whisper',
                'model': f"whisper-{self.model_size}",
                'device': self.device,
                'language_probability': getattr(info, 'language_probability', 0.0),
                'original_transcript': transcript if transcript != filtered_transcript else None
            }
            
            # Log results with clear visibility
            if filtered_transcript:
                logger.info(f"✅ LOCAL WHISPER SUCCESS for {session_id}:")
                logger.info(f"   📝 Text: '{filtered_transcript}'")
                logger.info(f"   📊 Length: {len(filtered_transcript)} chars, Confidence: {avg_confidence:.2f}")
                logger.info(f"   🎯 Device: {self.device}, Model: {self.model_size}")
            elif transcript and not filtered_transcript:
                logger.warning(f"🚫 FILTERED LOCAL HALLUCINATION for {session_id}: '{transcript}'")
                logger.warning(f"   Audio levels: max={audio_stats['max_level']:.6f}, dBFS={audio_stats['dbfs']:.2f}")
            else:
                logger.warning(f"⚠️ LOCAL WHISPER RETURNED EMPTY for {session_id}")
                logger.warning(f"   Audio levels: max={audio_stats['max_level']:.6f}, dBFS={audio_stats['dbfs']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Local Whisper transcription failed for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'is_final': True,
                'error': str(e),
                'processing_method': 'local_whisper_failed',
                'model': f"whisper-{self.model_size}",
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
        if not TORCH_AVAILABLE or self.model is None:
            logger.error("Local Whisper not available - cannot perform final transcription")
            return {
                'success': False,
                'transcript': '',
                'error': 'Local Whisper transcription not available. Missing PyTorch/faster-whisper dependencies.',
                'processing_time': 0.0,
                'method': 'local_whisper_unavailable',
                'confidence': 0.0,
                'audio_stats': {}
            }
            
        try:
            # Ensure model is loaded
            if not await self._ensure_model_loaded():
                raise RuntimeError("Failed to load Whisper model")
            
            # Convert PCM to numpy array
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Enhanced final transcription with better parameters
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_array,
                    language="en",
                    beam_size=5,  # Better quality for final transcription
                    best_of=3,    # Better quality
                    temperature=(0.0, 0.2, 0.4, 0.6, 0.8),  # Temperature fallback
                    compression_ratio_threshold=2.4,
                    log_prob_threshold=-1.0,
                    no_captions_threshold=0.6,
                    condition_on_previous_text=False,
                    word_timestamps=True  # Get word-level timing
                )
            )
            
            # Process segments with timing
            transcript_parts = []
            all_words = []
            
            for segment in segments:
                if segment.text.strip():
                    transcript_parts.append(segment.text.strip())
                    if hasattr(segment, 'words') and segment.words:
                        all_words.extend(segment.words)
            
            transcript = " ".join(transcript_parts).strip()
            
            # Filter hallucinations from final transcript
            filtered_transcript = self._filter_hallucinations(transcript, self.audio_processor.calculate_audio_levels(pcm_data))
            
            result = {
                'transcript': filtered_transcript,
                'confidence': getattr(info, 'language_probability', 0.0),
                'paragraphs': [filtered_transcript] if filtered_transcript else [],
                'utterances': [],  # Could be enhanced with word timing data
                'processing_method': 'local_whisper',
                'model': f"whisper-{self.model_size}",
                'device': self.device,
                'is_final': True,
                'audio_stats': self.audio_processor.calculate_audio_levels(pcm_data),
                'word_count': len(filtered_transcript.split()) if filtered_transcript else 0
            }
            
            logger.info(f"Final local transcription for session {session_id}: {len(transcript)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Final local transcription failed for session {session_id}: {e}")
            return {
                'transcript': '',
                'confidence': 0.0,
                'paragraphs': [],
                'utterances': [],
                'error': str(e),
                'processing_method': 'local_whisper_failed',
                'model': f"whisper-{self.model_size}",
                'is_final': True,
                'audio_stats': self.audio_processor.calculate_audio_levels(pcm_data) if pcm_data else {}
            }
    
    def _filter_hallucinations(self, transcript: str, audio_stats: Dict[str, Any]) -> str:
        """
        Filter out common Whisper hallucinations (same logic as API version)
        
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
        
        # Check for repetitive patterns
        words = transcript.strip().split()
        if len(words) > 2:
            unique_words = set(w.lower().rstrip('.,!?') for w in words)
            if len(unique_words) <= 2 and len(words) > 4:
                logger.info(f"Detected repetitive hallucination: '{transcript}'")
                return ''
        
        # Filter transcripts in very low audio scenarios
        if audio_stats.get('dbfs', 0) < -45:  # Very low audio level
            suspicious_phrases = ['thank you', 'thanks', 'bye', 'goodbye', 'you', 'yeah', 'okay', 'oh']
            transcript_lower = transcript.lower().strip().rstrip('.,!?')
            if transcript_lower in suspicious_phrases:
                logger.info(f"Filtered low-confidence hallucination: '{transcript}' "
                          f"(dBFS={audio_stats.get('dbfs', -100):.2f})")
                return ''
        
        return transcript
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            'model_size': self.model_size,
            'device': self.device,
            'is_loaded': self.model is not None,
            'loading': self._model_loading,
            'cuda_available': torch.cuda.is_available(),
            'mps_available': hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
        }
    
    async def unload_model(self):
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
            # Force garbage collection
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Whisper model {self.model_size} unloaded")