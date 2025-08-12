"""
Advanced Audio File Security Validator
Comprehensive security validation for educational platform audio uploads
"""

import os
import re
import subprocess
import tempfile
import hashlib
import mimetypes
from typing import Optional, Dict, List, Tuple, Any, BinaryIO
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import magic
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class AudioValidationResult:
    """Result of audio file validation"""
    is_valid: bool
    file_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: int = 0
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bitrate: Optional[int] = None
    errors: List[str] = None
    warnings: List[str] = None
    security_score: int = 0  # 0-100, higher is safer
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

class AudioSecurityValidator:
    """
    Advanced audio file security validator for educational platforms
    
    Features:
    - Magic byte validation beyond headers
    - Malicious embedded content detection
    - Educational usage limits (size, duration)
    - Memory exhaustion protection
    - FFmpeg-based secure analysis
    """
    
    # Allowed audio formats for educational use
    ALLOWED_MIME_TYPES = {
        'audio/wav',
        'audio/wave', 
        'audio/x-wav',
        'audio/mpeg',
        'audio/mp3',
        'audio/ogg',
        'audio/vorbis',
        'audio/webm',
        'audio/flac',
        'audio/aac',
        'audio/m4a',
        'audio/x-m4a'
    }
    
    ALLOWED_EXTENSIONS = {
        '.wav', '.wave', '.mp3', '.ogg', '.oga', 
        '.webm', '.flac', '.aac', '.m4a', '.opus'
    }
    
    # Magic byte signatures for common audio formats
    AUDIO_SIGNATURES = {
        b'RIFF': 'wav',
        b'ID3': 'mp3',
        b'\xff\xfb': 'mp3',
        b'\xff\xf3': 'mp3', 
        b'\xff\xf2': 'mp3',
        b'OggS': 'ogg',
        b'fLaC': 'flac',
        b'\x1a\x45\xdf\xa3': 'webm',
        b'ftypM4A ': 'm4a'
    }
    
    # Educational platform limits
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_DURATION_SECONDS = 7200  # 2 hours (lecture length)
    MIN_DURATION_SECONDS = 1  # 1 second minimum
    
    # Security limits to prevent abuse
    MAX_SAMPLE_RATE = 192000  # 192kHz
    MAX_CHANNELS = 8  # Surround sound maximum
    MAX_BITRATE = 2000  # 2000 kbps
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """Initialize validator with FFmpeg paths"""
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        
        # Initialize libmagic
        try:
            self.mime_detector = magic.Magic(mime=True)
            self.type_detector = magic.Magic()
        except Exception as e:
            logger.warning(f"Failed to initialize libmagic: {e}")
            self.mime_detector = None
            self.type_detector = None
    
    async def validate_audio_file(
        self, 
        file_path: str, 
        original_filename: str = None,
        max_size_override: int = None
    ) -> AudioValidationResult:
        """
        Comprehensive audio file validation
        
        Args:
            file_path: Path to audio file to validate
            original_filename: Original filename for extension checking
            max_size_override: Override default max file size
            
        Returns:
            AudioValidationResult with validation details
        """
        result = AudioValidationResult(is_valid=False)
        
        try:
            # Basic file checks
            if not os.path.exists(file_path):
                result.errors.append("File does not exist")
                return result
            
            # File size check
            file_size = os.path.getsize(file_path)
            result.file_size_bytes = file_size
            
            max_size = max_size_override or self.MAX_FILE_SIZE
            if file_size > max_size:
                result.errors.append(f"File size {file_size} exceeds limit of {max_size} bytes")
                return result
            
            if file_size == 0:
                result.errors.append("File is empty")
                return result
            
            # Extension validation
            if original_filename:
                ext = Path(original_filename).suffix.lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    result.errors.append(f"File extension {ext} not allowed")
                    result.security_score -= 20
            
            # Magic byte validation
            magic_validation = await self._validate_magic_bytes(file_path)
            if not magic_validation["valid"]:
                result.errors.extend(magic_validation["errors"])
                result.security_score -= 30
            else:
                result.file_type = magic_validation["detected_type"]
                result.security_score += 20
            
            # MIME type validation
            mime_validation = await self._validate_mime_type(file_path)
            if not mime_validation["valid"]:
                result.warnings.extend(mime_validation["warnings"])
                result.security_score -= 10
            else:
                result.security_score += 10
            
            # Deep audio analysis with FFprobe
            audio_analysis = await self._analyze_with_ffprobe(file_path)
            if not audio_analysis["valid"]:
                result.errors.extend(audio_analysis["errors"])
                return result
            
            # Extract audio properties
            result.duration_seconds = audio_analysis.get("duration")
            result.sample_rate = audio_analysis.get("sample_rate")
            result.channels = audio_analysis.get("channels")
            result.bitrate = audio_analysis.get("bitrate")
            result.metadata = audio_analysis.get("metadata", {})
            
            # Duration validation
            if result.duration_seconds:
                if result.duration_seconds > self.MAX_DURATION_SECONDS:
                    result.errors.append(
                        f"Duration {result.duration_seconds:.1f}s exceeds limit of {self.MAX_DURATION_SECONDS}s"
                    )
                    return result
                elif result.duration_seconds < self.MIN_DURATION_SECONDS:
                    result.errors.append(
                        f"Duration {result.duration_seconds:.1f}s below minimum of {self.MIN_DURATION_SECONDS}s"
                    )
                    return result
                else:
                    result.security_score += 15
            
            # Technical parameter validation
            param_validation = self._validate_audio_parameters(result)
            result.warnings.extend(param_validation["warnings"])
            if param_validation["errors"]:
                result.errors.extend(param_validation["errors"])
                return result
            
            # Metadata security scan
            metadata_scan = await self._scan_metadata_security(result.metadata)
            if metadata_scan["suspicious"]:
                result.warnings.extend(metadata_scan["warnings"])
                result.security_score -= 15
            
            # Embedded content scan
            embedded_scan = await self._scan_embedded_content(file_path)
            if not embedded_scan["safe"]:
                result.errors.extend(embedded_scan["errors"])
                result.warnings.extend(embedded_scan["warnings"])
                result.security_score -= 25
            else:
                result.security_score += 20
            
            # Final security score calculation
            result.security_score = max(0, min(100, result.security_score + 50))  # Base score of 50
            
            # Determine overall validity
            if not result.errors and result.security_score >= 60:
                result.is_valid = True
                logger.info(
                    f"Audio file validation successful",
                    extra={
                        "file_size": result.file_size_bytes,
                        "duration": result.duration_seconds,
                        "file_type": result.file_type,
                        "security_score": result.security_score
                    }
                )
            else:
                logger.warning(
                    f"Audio file validation failed",
                    extra={
                        "errors": result.errors,
                        "warnings": result.warnings,
                        "security_score": result.security_score
                    }
                )
            
        except Exception as e:
            logger.error(f"Audio validation error: {e}")
            result.errors.append(f"Validation error: {str(e)}")
        
        return result
    
    async def _validate_magic_bytes(self, file_path: str) -> Dict[str, Any]:
        """Validate file using magic byte signatures"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)  # Read first 32 bytes
            
            # Check against known audio signatures
            detected_type = None
            for signature, file_type in self.AUDIO_SIGNATURES.items():
                if header.startswith(signature):
                    detected_type = file_type
                    break
            
            # Use libmagic if available
            if self.type_detector and not detected_type:
                try:
                    magic_type = self.type_detector.from_file(file_path).lower()
                    if 'audio' in magic_type or any(fmt in magic_type for fmt in ['wav', 'mp3', 'ogg', 'flac']):
                        detected_type = magic_type.split()[0]
                except Exception:
                    pass
            
            if detected_type:
                return {
                    "valid": True,
                    "detected_type": detected_type,
                    "errors": []
                }
            else:
                return {
                    "valid": False,
                    "detected_type": None,
                    "errors": ["File does not appear to be a valid audio file (magic byte check failed)"]
                }
                
        except Exception as e:
            return {
                "valid": False,
                "detected_type": None,
                "errors": [f"Magic byte validation error: {str(e)}"]
            }
    
    async def _validate_mime_type(self, file_path: str) -> Dict[str, Any]:
        """Validate MIME type"""
        try:
            # Use libmagic first
            mime_type = None
            if self.mime_detector:
                try:
                    mime_type = self.mime_detector.from_file(file_path)
                except Exception:
                    pass
            
            # Fallback to Python's mimetypes
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type and mime_type in self.ALLOWED_MIME_TYPES:
                return {
                    "valid": True,
                    "mime_type": mime_type,
                    "warnings": []
                }
            else:
                return {
                    "valid": False,
                    "mime_type": mime_type,
                    "warnings": [f"MIME type {mime_type} not in allowed list"]
                }
                
        except Exception as e:
            return {
                "valid": False,
                "mime_type": None,
                "warnings": [f"MIME type validation error: {str(e)}"]
            }
    
    async def _analyze_with_ffprobe(self, file_path: str) -> Dict[str, Any]:
        """Analyze audio file with FFprobe"""
        try:
            # Use FFprobe to get detailed audio information
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-show_error',
                file_path
            ]
            
            # Run with timeout and resource limits
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False
            )
            
            if result.returncode != 0:
                return {
                    "valid": False,
                    "errors": [f"FFprobe analysis failed: {result.stderr}"]
                }
            
            import json
            probe_data = json.loads(result.stdout)
            
            # Extract format information
            format_info = probe_data.get('format', {})
            duration = float(format_info.get('duration', 0))
            
            # Find audio stream
            audio_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return {
                    "valid": False,
                    "errors": ["No audio stream found in file"]
                }
            
            # Extract audio properties
            sample_rate = int(audio_stream.get('sample_rate', 0))
            channels = int(audio_stream.get('channels', 0))
            bitrate = int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else None
            
            # Extract metadata
            metadata = format_info.get('tags', {})
            
            return {
                "valid": True,
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": channels,
                "bitrate": bitrate,
                "metadata": metadata,
                "codec": audio_stream.get('codec_name'),
                "errors": []
            }
            
        except subprocess.TimeoutExpired:
            return {
                "valid": False,
                "errors": ["FFprobe analysis timed out"]
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"FFprobe analysis error: {str(e)}"]
            }
    
    def _validate_audio_parameters(self, result: AudioValidationResult) -> Dict[str, Any]:
        """Validate audio technical parameters"""
        warnings = []
        errors = []
        
        # Sample rate validation
        if result.sample_rate:
            if result.sample_rate > self.MAX_SAMPLE_RATE:
                errors.append(f"Sample rate {result.sample_rate}Hz exceeds maximum {self.MAX_SAMPLE_RATE}Hz")
            elif result.sample_rate < 8000:
                warnings.append(f"Low sample rate {result.sample_rate}Hz may indicate poor quality")
        
        # Channel validation
        if result.channels:
            if result.channels > self.MAX_CHANNELS:
                errors.append(f"Channel count {result.channels} exceeds maximum {self.MAX_CHANNELS}")
            elif result.channels == 0:
                errors.append("Invalid channel count of 0")
        
        # Bitrate validation
        if result.bitrate:
            if result.bitrate > self.MAX_BITRATE * 1000:  # Convert to bps
                warnings.append(f"High bitrate {result.bitrate}bps may indicate inefficient encoding")
        
        return {
            "warnings": warnings,
            "errors": errors
        }
    
    async def _scan_metadata_security(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Scan metadata for security issues"""
        warnings = []
        suspicious = False
        
        if not metadata:
            return {"suspicious": False, "warnings": []}
        
        # Check for suspicious metadata fields
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'vbscript:',
            r'<?php',
            r'<?xml',
            r'<!DOCTYPE',
            r'<html',
            r'http[s]?://',
            r'file://',
            r'ftp://'
        ]
        
        for key, value in metadata.items():
            if not isinstance(value, str):
                continue
                
            value_lower = value.lower()
            
            # Check for script injection attempts
            for pattern in suspicious_patterns:
                if re.search(pattern, value_lower):
                    warnings.append(f"Suspicious content in metadata field '{key}': {pattern}")
                    suspicious = True
            
            # Check for excessively long metadata (potential buffer overflow)
            if len(value) > 1000:
                warnings.append(f"Metadata field '{key}' is unusually long ({len(value)} characters)")
                suspicious = True
            
            # Check for binary content in text fields
            try:
                value.encode('ascii')
            except UnicodeEncodeError:
                # Non-ASCII content might be normal for international metadata
                if len([c for c in value if ord(c) < 32]) > 5:
                    warnings.append(f"Metadata field '{key}' contains suspicious binary content")
                    suspicious = True
        
        return {
            "suspicious": suspicious,
            "warnings": warnings
        }
    
    async def _scan_embedded_content(self, file_path: str) -> Dict[str, Any]:
        """Scan for embedded malicious content"""
        warnings = []
        errors = []
        safe = True
        
        try:
            # Read file in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            suspicious_patterns = [
                b'<script',
                b'javascript:',
                b'<?php',
                b'<?xml',
                b'<!DOCTYPE html',
                b'<html',
                b'MZ',  # PE executable header
                b'\x7fELF',  # ELF executable header
            ]
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Check for embedded executables or scripts
                    for pattern in suspicious_patterns:
                        if pattern in chunk:
                            if pattern in [b'MZ', b'\x7fELF']:
                                errors.append(f"File contains embedded executable content")
                                safe = False
                            else:
                                warnings.append(f"File contains potentially suspicious embedded content")
                                safe = False if pattern in [b'<script', b'javascript:', b'<?php'] else safe
                    
                    # Check for unusual data patterns that might hide malware
                    null_ratio = chunk.count(b'\x00') / len(chunk) if chunk else 0
                    if null_ratio > 0.5:
                        warnings.append("File contains high ratio of null bytes (potential steganography)")
            
            # Check file entropy (random data might indicate encryption/packing)
            entropy = self._calculate_file_entropy(file_path)
            if entropy > 7.5:
                warnings.append(f"High file entropy ({entropy:.2f}) may indicate packed or encrypted content")
            
        except Exception as e:
            errors.append(f"Embedded content scan error: {str(e)}")
            safe = False
        
        return {
            "safe": safe,
            "warnings": warnings,
            "errors": errors
        }
    
    def _calculate_file_entropy(self, file_path: str, sample_size: int = 1024*1024) -> float:
        """Calculate Shannon entropy of file (sample for performance)"""
        try:
            import math
            from collections import Counter
            
            with open(file_path, 'rb') as f:
                data = f.read(sample_size)
            
            if not data:
                return 0.0
            
            # Count byte frequencies
            byte_counts = Counter(data)
            data_len = len(data)
            
            # Calculate entropy
            entropy = 0.0
            for count in byte_counts.values():
                probability = count / data_len
                entropy -= probability * math.log2(probability)
            
            return entropy
            
        except Exception:
            return 0.0
    
    async def create_safe_audio_copy(
        self, 
        source_path: str, 
        dest_path: str,
        target_format: str = "wav"
    ) -> bool:
        """
        Create a safe copy of audio file by transcoding to canonical format
        This strips metadata and potential embedded content
        """
        try:
            # Use FFmpeg to transcode to safe format
            cmd = [
                self.ffmpeg_path,
                '-i', source_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le' if target_format == 'wav' else 'libmp3lame',
                '-ar', '44100',  # Standard sample rate
                '-ac', '2',  # Stereo
                '-map_metadata', '-1',  # Strip all metadata
                '-y',  # Overwrite output
                dest_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"Created safe audio copy: {dest_path}")
                return True
            else:
                logger.error(f"Failed to create safe audio copy: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating safe audio copy: {e}")
            return False
    
    def get_validation_summary(self, result: AudioValidationResult) -> str:
        """Generate human-readable validation summary"""
        if result.is_valid:
            summary = f"✓ Valid {result.file_type or 'audio'} file"
            if result.duration_seconds:
                summary += f" ({result.duration_seconds:.1f}s"
                if result.file_size_bytes:
                    size_mb = result.file_size_bytes / (1024 * 1024)
                    summary += f", {size_mb:.1f}MB"
                summary += ")"
            summary += f" - Security Score: {result.security_score}/100"
        else:
            summary = f"✗ Invalid audio file - {len(result.errors)} error(s)"
        
        if result.warnings:
            summary += f" - {len(result.warnings)} warning(s)"
        
        return summary


# Global validator instance
_audio_validator = None

def get_audio_validator() -> AudioSecurityValidator:
    """Get global audio validator instance"""
    global _audio_validator
    if _audio_validator is None:
        _audio_validator = AudioSecurityValidator()
    return _audio_validator