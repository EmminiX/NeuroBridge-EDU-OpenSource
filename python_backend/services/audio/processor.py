"""
Audio processing utilities for PCM data handling
Handles audio level calculation, format conversion, and silence detection
"""

import numpy as np
from typing import Dict, Tuple, Any
from utils.logger import get_logger

logger = get_logger("audio.processor")


class AudioProcessor:
    """Handles PCM audio processing and level calculation"""
    
    @staticmethod
    def calculate_audio_levels(pcm_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Calculate audio levels from raw PCM16 bytes
        
        Args:
            pcm_data: Raw PCM16 bytes (little-endian)
            sample_rate: Sample rate in Hz
            
        Returns:
            Dictionary with level statistics
        """
        try:
            # Validate input
            if not pcm_data or len(pcm_data) == 0:
                return {
                    'max_level': 0.0,
                    'rms_level': 0.0,
                    'dbfs': -float('inf'),
                    'is_silent': True,
                    'duration_ms': 0,
                    'sample_count': 0
                }
            
            if len(pcm_data) % 2 != 0:
                logger.warning(f"Invalid PCM data length: {len(pcm_data)} (not multiple of 2)")
                # Trim to even length
                pcm_data = pcm_data[:-1]
            
            # Convert bytes to numpy array (little-endian 16-bit signed integers)
            pcm16 = np.frombuffer(pcm_data, dtype='<i2')  # '<i2' = little-endian int16
            
            if len(pcm16) == 0:
                return {
                    'max_level': 0.0,
                    'rms_level': 0.0,
                    'dbfs': -float('inf'),
                    'is_silent': True,
                    'duration_ms': 0,
                    'sample_count': 0
                }
            
            # Normalize to float range [-1.0, 1.0]
            normalized = pcm16.astype(np.float32) / 32768.0
            
            # Calculate levels
            max_level = float(np.max(np.abs(normalized)))
            rms_level = float(np.sqrt(np.mean(normalized**2)))
            
            # Calculate dBFS (decibels full scale)
            dbfs = 20 * np.log10(rms_level) if rms_level > 0 else -float('inf')
            
            # Duration calculation
            duration_ms = (len(pcm16) / sample_rate) * 1000
            
            # Balanced silence detection - sensitive enough for speech but filters true silence
            # Original threshold was -40 dBFS, using -45 dBFS for better balance
            # Convert to Python bool to avoid JSON serialization issues with numpy.bool
            is_silent = bool(dbfs < -45.0 or max_level < 0.001)
            
            result = {
                'max_level': max_level,
                'rms_level': rms_level,
                'dbfs': float(dbfs),
                'is_silent': is_silent,
                'duration_ms': float(duration_ms),
                'sample_count': len(pcm16)
            }
            
            # Debug logging for silence issues
            if is_silent and len(pcm_data) > 100:
                logger.debug(f"Silent audio detected - Bytes: {len(pcm_data)}, "
                           f"Samples: {len(pcm16)}, Max: {max_level:.6f}, "
                           f"RMS: {rms_level:.6f}, dBFS: {dbfs:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating audio levels: {e}")
            return {
                'max_level': 0.0,
                'rms_level': 0.0,
                'dbfs': -float('inf'),
                'is_silent': True,
                'duration_ms': 0,
                'sample_count': 0,
                'error': str(e)
            }
    
    @staticmethod
    def validate_pcm_format(pcm_data: bytes) -> bool:
        """Validate PCM data format"""
        if not pcm_data:
            return False
            
        if len(pcm_data) % 2 != 0:
            logger.warning("PCM data length not multiple of 2")
            return False
            
        # Check for common audio patterns
        try:
            pcm16 = np.frombuffer(pcm_data, dtype='<i2')
            # Very basic validation - check if all samples are zero
            if np.all(pcm16 == 0):
                logger.warning("All PCM samples are zero")
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_overlap_buffer(chunk1: bytes, chunk2: bytes, overlap_ms: int = 200, 
                            sample_rate: int = 16000) -> bytes:
        """
        Create overlapped audio buffer from two consecutive chunks
        
        Args:
            chunk1: First audio chunk
            chunk2: Second audio chunk
            overlap_ms: Overlap duration in milliseconds
            sample_rate: Audio sample rate
            
        Returns:
            Combined audio with overlap
        """
        try:
            overlap_samples = int((overlap_ms / 1000.0) * sample_rate)
            overlap_bytes = overlap_samples * 2  # 2 bytes per 16-bit sample
            
            if len(chunk1) < overlap_bytes:
                return chunk1 + chunk2
            
            # Take overlap from end of chunk1 and beginning of chunk2
            overlap_end = chunk1[-overlap_bytes:]
            return overlap_end + chunk2
            
        except Exception as e:
            logger.error(f"Error creating overlap buffer: {e}")
            return chunk1 + chunk2
    
    @staticmethod
    def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
        """
        Convert raw PCM data to WAV format with proper headers
        
        Args:
            pcm_data: Raw PCM audio bytes
            sample_rate: Sample rate (default 16000 Hz)
            channels: Number of channels (default 1 for mono)
            bits_per_sample: Bits per sample (default 16)
            
        Returns:
            WAV formatted audio bytes
        """
        import struct
        import io
        
        # Calculate sizes
        data_size = len(pcm_data)
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        
        # Write RIFF header
        wav_buffer.write(b'RIFF')
        wav_buffer.write(struct.pack('<I', 36 + data_size))  # File size - 8
        wav_buffer.write(b'WAVE')
        
        # Write fmt chunk
        wav_buffer.write(b'fmt ')
        wav_buffer.write(struct.pack('<I', 16))  # fmt chunk size
        wav_buffer.write(struct.pack('<H', 1))   # Audio format (1 = PCM)
        wav_buffer.write(struct.pack('<H', channels))
        wav_buffer.write(struct.pack('<I', sample_rate))
        wav_buffer.write(struct.pack('<I', byte_rate))
        wav_buffer.write(struct.pack('<H', block_align))
        wav_buffer.write(struct.pack('<H', bits_per_sample))
        
        # Write data chunk
        wav_buffer.write(b'data')
        wav_buffer.write(struct.pack('<I', data_size))
        wav_buffer.write(pcm_data)
        
        return wav_buffer.getvalue()