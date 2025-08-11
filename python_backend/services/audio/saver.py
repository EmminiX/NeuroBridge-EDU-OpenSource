"""
Audio file saver for debugging transcription issues
Saves audio chunks as WAV files for manual inspection
"""

import os
import wave
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger("audio.saver")


class AudioSaver:
    """Utility class for saving audio chunks for debugging"""
    
    def __init__(self, debug_dir: Optional[str] = None):
        """
        Initialize audio saver
        
        Args:
            debug_dir: Directory to save debug files (defaults to temp/audio_debug)
        """
        if debug_dir is None:
            debug_dir = os.path.join(tempfile.gettempdir(), "neurobridge_audio_debug")
        
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Audio debug directory: {self.debug_dir}")
    
    def save_pcm_chunk(self, pcm_data: bytes, session_id: str, 
                      chunk_index: int = 0, sample_rate: int = 16000) -> Optional[str]:
        """
        Save PCM chunk as WAV file for debugging
        
        Args:
            pcm_data: Raw PCM16 bytes
            session_id: Transcription session ID
            chunk_index: Chunk sequence number
            sample_rate: Audio sample rate
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            if not pcm_data:
                logger.warning("No PCM data to save")
                return None
            
            # Create filename with timestamp and metadata
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{chunk_index:04d}_{timestamp}.wav"
            filepath = self.debug_dir / filename
            
            # Save as WAV file
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            
            file_size = len(pcm_data)
            duration_ms = (len(pcm_data) / 2 / sample_rate) * 1000
            
            logger.info(f"Saved audio chunk: {filename} "
                       f"({file_size} bytes, {duration_ms:.0f}ms)")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save audio chunk: {e}")
            return None
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old debug files
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Number of files cleaned up
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            for file_path in self.debug_dir.glob("*.wav"):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old debug files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0