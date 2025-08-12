"""
Whisper Preprocessing Pipeline Integration
Combines advanced audio processing with Whisper-specific optimizations
"""

import asyncio
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from utils.logger import get_logger
from services.audio.advanced_processor import EducationalAudioProcessor
from services.audio.processor import AudioProcessor

# Optional import for resampling
try:
    import scipy.signal as sp_signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    sp_signal = None

logger = get_logger("whisper.preprocessing")


class WhisperPreprocessor:
    """
    Whisper-specific preprocessing pipeline that integrates advanced audio processing
    with Whisper model requirements for optimal educational content transcription
    """
    
    # Whisper model requirements
    WHISPER_SAMPLE_RATE = 16000
    WHISPER_FRAME_LENGTH = 0.025  # 25ms frames
    WHISPER_HOP_LENGTH = 0.010    # 10ms hop
    WHISPER_N_FFT = 400           # FFT points for 25ms at 16kHz
    
    # Educational content preprocessing parameters
    EDUCATIONAL_PREPROCESS_PARAMS = {
        'target_lufs': -16.0,       # Target loudness for educational content
        'max_lufs': -12.0,          # Maximum loudness to prevent distortion
        'min_lufs': -30.0,          # Minimum loudness threshold
        'high_pass_cutoff': 80,     # Remove sub-bass rumble
        'low_pass_cutoff': 8000,    # Remove high-frequency noise above speech
        'noise_gate_threshold': -40, # Noise gate threshold in dBFS
        'segment_length_ms': 8000,   # Optimal segment length for Whisper (8 seconds)
        'overlap_ms': 500           # Overlap between segments
    }
    
    def __init__(
        self,
        educational_mode: bool = True,
        aggressive_preprocessing: bool = False,
        preserve_dynamics: bool = True
    ):
        """
        Initialize Whisper preprocessor
        
        Args:
            educational_mode: Enable educational content optimizations
            aggressive_preprocessing: Enable more aggressive processing for challenging audio
            preserve_dynamics: Preserve speech dynamics vs. heavy processing
        """
        self.educational_mode = educational_mode
        self.aggressive_preprocessing = aggressive_preprocessing
        self.preserve_dynamics = preserve_dynamics
        
        # Initialize processors
        self.advanced_processor = EducationalAudioProcessor(
            sample_rate=self.WHISPER_SAMPLE_RATE,
            educational_mode=educational_mode,
            noise_reduction_enabled=True,
            spectral_enhancement_enabled=True
        )
        self.basic_processor = AudioProcessor()
        
        # Preprocessing statistics
        self.preprocessing_stats = {
            'chunks_preprocessed': 0,
            'resampling_applied': 0,
            'loudness_normalization_applied': 0,
            'segmentation_applied': 0,
            'average_preprocessing_time': 0.0,
            'average_quality_improvement': 0.0
        }
        
        # Adaptive parameters
        self._session_audio_profile = None
        self._optimal_params_cache = {}
        
        logger.info(f"Whisper Preprocessor initialized - "
                   f"Educational: {educational_mode}, "
                   f"Aggressive: {aggressive_preprocessing}, "
                   f"Preserve Dynamics: {preserve_dynamics}")
    
    async def preprocess_for_whisper(
        self,
        pcm_data: bytes,
        session_id: str,
        chunk_index: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete preprocessing pipeline for Whisper transcription
        
        Args:
            pcm_data: Raw PCM16 audio data
            session_id: Session identifier
            chunk_index: Index of chunk in session
            context: Additional context for processing decisions
            
        Returns:
            Dict containing preprocessed audio and metadata
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not pcm_data or len(pcm_data) < 64:
                return self._create_preprocessing_result(
                    pcm_data, session_id, {'error': 'insufficient_audio_data'}
                )
            
            # Calculate initial audio characteristics
            initial_stats = self.basic_processor.calculate_audio_levels(pcm_data)
            
            # Stage 1: Format validation and conversion
            processed_pcm, format_metadata = await self._ensure_whisper_format(
                pcm_data, session_id
            )
            
            # Stage 2: Advanced audio processing
            enhanced_pcm, enhancement_metadata = await self.advanced_processor.process_educational_audio(
                processed_pcm, session_id, initial_stats
            )
            
            # Stage 3: Whisper-specific optimizations
            optimized_pcm, optimization_metadata = await self._apply_whisper_optimizations(
                enhanced_pcm, session_id, chunk_index
            )
            
            # Stage 4: Quality validation and final adjustments
            final_pcm, validation_metadata = await self._validate_and_finalize(
                optimized_pcm, session_id
            )
            
            # Calculate final statistics
            final_stats = self.basic_processor.calculate_audio_levels(final_pcm)
            
            # Compile comprehensive metadata
            preprocessing_metadata = {
                'session_id': session_id,
                'chunk_index': chunk_index,
                'initial_stats': initial_stats,
                'final_stats': final_stats,
                'processing_stages': {
                    'format_conversion': format_metadata,
                    'audio_enhancement': enhancement_metadata,
                    'whisper_optimization': optimization_metadata,
                    'quality_validation': validation_metadata
                },
                'preprocessing_time': time.time() - start_time,
                'quality_improvement': self._calculate_quality_improvement(initial_stats, final_stats),
                'whisper_compatibility': self._assess_whisper_compatibility(final_pcm)
            }
            
            # Update statistics
            self._update_preprocessing_stats(preprocessing_metadata)
            
            # Log significant improvements
            if preprocessing_metadata['quality_improvement'] > 2.0:  # > 2dB improvement
                logger.info(f"Significant audio improvement for {session_id}:{chunk_index} - "
                           f"{preprocessing_metadata['quality_improvement']:.2f}dB improvement")
            
            return self._create_preprocessing_result(final_pcm, session_id, preprocessing_metadata)
            
        except Exception as e:
            logger.error(f"Preprocessing failed for {session_id}:{chunk_index}: {e}")
            return self._create_preprocessing_result(
                pcm_data, session_id, {'error': str(e), 'preprocessing_time': time.time() - start_time}
            )
    
    async def _ensure_whisper_format(
        self,
        pcm_data: bytes,
        session_id: str
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Ensure audio is in the correct format for Whisper"""
        try:
            # Convert to float array for processing
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            metadata = {
                'original_sample_rate': 'assumed_16000',  # Assuming input is already 16kHz
                'resampling_required': False,
                'format_validated': True
            }
            
            # Validate sample rate (if we had this information, we'd resample here)
            # For now, assume input is already at 16kHz as per the existing codebase
            
            # Ensure mono (if stereo, convert to mono)
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
                metadata['stereo_to_mono_conversion'] = True
            
            # Convert back to PCM16
            processed_pcm16 = np.clip(audio_array * 32768.0, -32768, 32767).astype(np.int16)
            processed_pcm = processed_pcm16.tobytes()
            
            return processed_pcm, metadata
            
        except Exception as e:
            logger.warning(f"Format validation failed for {session_id}: {e}")
            return pcm_data, {'error': str(e)}
    
    async def _apply_whisper_optimizations(
        self,
        pcm_data: bytes,
        session_id: str,
        chunk_index: int
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Apply Whisper-specific optimizations"""
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            optimized_audio = audio_array.copy()
            metadata = {'optimizations_applied': []}
            
            # 1. Loudness normalization for consistent Whisper input levels
            if self.educational_mode:
                optimized_audio, loudness_meta = await self._apply_loudness_normalization(
                    optimized_audio, session_id
                )
                metadata['optimizations_applied'].append('loudness_normalization')
                metadata['loudness_normalization'] = loudness_meta
            
            # 2. Optimal windowing for Whisper's attention mechanism
            if len(optimized_audio) > self.WHISPER_SAMPLE_RATE * 2:  # > 2 seconds
                optimized_audio, windowing_meta = await self._apply_optimal_windowing(
                    optimized_audio, session_id
                )
                metadata['optimizations_applied'].append('optimal_windowing')
                metadata['optimal_windowing'] = windowing_meta
            
            # 3. Educational content specific adjustments
            if self.educational_mode:
                optimized_audio, edu_meta = await self._apply_educational_adjustments(
                    optimized_audio, session_id, chunk_index
                )
                metadata['optimizations_applied'].append('educational_adjustments')
                metadata['educational_adjustments'] = edu_meta
            
            # Convert back to PCM16
            optimized_pcm16 = np.clip(optimized_audio * 32768.0, -32768, 32767).astype(np.int16)
            optimized_pcm = optimized_pcm16.tobytes()
            
            return optimized_pcm, metadata
            
        except Exception as e:
            logger.warning(f"Whisper optimizations failed for {session_id}: {e}")
            return pcm_data, {'error': str(e)}
    
    async def _apply_loudness_normalization(
        self,
        audio: np.ndarray,
        session_id: str
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply LUFS-based loudness normalization for consistent Whisper input"""
        try:
            # Calculate current RMS level as proxy for loudness
            current_rms = np.sqrt(np.mean(audio**2))
            if current_rms < 1e-6:
                return audio, {'skipped': 'signal_too_quiet'}
            
            current_lufs = -23 + 20 * np.log10(current_rms)  # Rough LUFS estimate
            target_lufs = self.EDUCATIONAL_PREPROCESS_PARAMS['target_lufs']
            
            # Calculate required gain
            gain_db = target_lufs - current_lufs
            gain_linear = 10**(gain_db / 20)
            
            # Apply safety limits
            max_gain = 20.0  # 26dB max boost
            min_gain = 0.1   # -20dB max cut
            gain_linear = np.clip(gain_linear, min_gain, max_gain)
            
            # Apply gain
            normalized_audio = audio * gain_linear
            
            # Soft limiting to prevent clipping
            normalized_audio = np.tanh(normalized_audio * 0.9) * 0.95
            
            self.preprocessing_stats['loudness_normalization_applied'] += 1
            
            return normalized_audio, {
                'original_lufs': current_lufs,
                'target_lufs': target_lufs,
                'gain_applied_db': 20 * np.log10(gain_linear),
                'soft_limiting_applied': True,
                'success': True
            }
            
        except Exception as e:
            logger.warning(f"Loudness normalization failed for {session_id}: {e}")
            return audio, {'error': str(e)}
    
    async def _apply_optimal_windowing(
        self,
        audio: np.ndarray,
        session_id: str
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply optimal windowing for Whisper's attention mechanism"""
        try:
            # Apply gentle fade-in/fade-out to reduce edge artifacts
            fade_samples = int(0.01 * self.WHISPER_SAMPLE_RATE)  # 10ms fade
            
            windowed_audio = audio.copy()
            
            if len(windowed_audio) > fade_samples * 2:
                # Fade in
                fade_in = np.linspace(0, 1, fade_samples)
                windowed_audio[:fade_samples] *= fade_in
                
                # Fade out
                fade_out = np.linspace(1, 0, fade_samples)
                windowed_audio[-fade_samples:] *= fade_out
            
            # Apply gentle high-pass filter to remove DC offset and very low frequencies
            if SCIPY_AVAILABLE:
                cutoff = self.EDUCATIONAL_PREPROCESS_PARAMS['high_pass_cutoff']
                sos = sp_signal.butter(
                    2, cutoff, btype='high', fs=self.WHISPER_SAMPLE_RATE, output='sos'
                )
                windowed_audio = sp_signal.sosfilt(sos, windowed_audio)
            
            return windowed_audio, {
                'fade_duration_ms': fade_samples / self.WHISPER_SAMPLE_RATE * 1000,
                'high_pass_applied': SCIPY_AVAILABLE,
                'success': True
            }
            
        except Exception as e:
            logger.warning(f"Optimal windowing failed for {session_id}: {e}")
            return audio, {'error': str(e)}
    
    async def _apply_educational_adjustments(
        self,
        audio: np.ndarray,
        session_id: str,
        chunk_index: int
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply educational content specific adjustments"""
        try:
            adjusted_audio = audio.copy()
            metadata = {'adjustments': []}
            
            # 1. Noise gate for classroom environments
            gate_threshold = self.EDUCATIONAL_PREPROCESS_PARAMS['noise_gate_threshold']
            gate_threshold_linear = 10**(gate_threshold / 20)
            
            # Simple noise gate
            gate_mask = np.abs(adjusted_audio) > gate_threshold_linear
            if np.any(~gate_mask):  # If there are samples below threshold
                # Apply gentle gating (don't completely silence, just reduce)
                adjusted_audio[~gate_mask] *= 0.1
                metadata['adjustments'].append('noise_gate')
            
            # 2. Enhance speech frequencies for educational content
            if SCIPY_AVAILABLE:
                # Gentle boost in 1-4kHz range (important for speech clarity)
                sos = sp_signal.butter(
                    2, [1000, 4000], btype='band', 
                    fs=self.WHISPER_SAMPLE_RATE, output='sos'
                )
                speech_band = sp_signal.sosfilt(sos, adjusted_audio)
                adjusted_audio += speech_band * 0.1  # 10% boost
                metadata['adjustments'].append('speech_enhancement')
            
            # 3. Adaptive processing based on chunk characteristics
            if chunk_index > 0:  # Use previous chunk information for adaptation
                # Simple adaptation: if previous chunks were quiet, be more sensitive
                chunk_energy = np.mean(adjusted_audio**2)
                if chunk_energy < 0.001:  # Very quiet chunk
                    # Apply gentle boost
                    adjusted_audio *= 2.0
                    adjusted_audio = np.clip(adjusted_audio, -0.95, 0.95)
                    metadata['adjustments'].append('quiet_chunk_boost')
            
            return adjusted_audio, metadata
            
        except Exception as e:
            logger.warning(f"Educational adjustments failed for {session_id}: {e}")
            return audio, {'error': str(e)}
    
    async def _validate_and_finalize(
        self,
        pcm_data: bytes,
        session_id: str
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Validate processed audio and apply final adjustments"""
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            validation_metadata = {
                'checks_performed': [],
                'issues_found': [],
                'corrections_applied': []
            }
            
            # Check 1: Audio levels
            peak_level = np.max(np.abs(audio_array))
            rms_level = np.sqrt(np.mean(audio_array**2))
            
            validation_metadata['checks_performed'].append('level_check')
            validation_metadata['peak_level'] = peak_level
            validation_metadata['rms_level'] = rms_level
            
            # Correction: Prevent clipping
            if peak_level > 0.95:
                audio_array = audio_array * (0.95 / peak_level)
                validation_metadata['issues_found'].append('near_clipping')
                validation_metadata['corrections_applied'].append('peak_limiting')
            
            # Check 2: Dynamic range
            dynamic_range = np.max(audio_array) - np.min(audio_array)
            validation_metadata['checks_performed'].append('dynamic_range_check')
            validation_metadata['dynamic_range'] = dynamic_range
            
            if dynamic_range < 0.01:  # Very low dynamic range
                validation_metadata['issues_found'].append('low_dynamic_range')
                # No correction applied - let Whisper handle low dynamic range audio
            
            # Check 3: DC offset
            dc_offset = np.mean(audio_array)
            validation_metadata['checks_performed'].append('dc_offset_check')
            validation_metadata['dc_offset'] = dc_offset
            
            if abs(dc_offset) > 0.01:  # Significant DC offset
                audio_array -= dc_offset
                validation_metadata['issues_found'].append('dc_offset')
                validation_metadata['corrections_applied'].append('dc_removal')
            
            # Convert back to PCM16
            final_pcm16 = np.clip(audio_array * 32768.0, -32768, 32767).astype(np.int16)
            final_pcm = final_pcm16.tobytes()
            
            validation_metadata['validation_passed'] = len(validation_metadata['issues_found']) == 0
            
            return final_pcm, validation_metadata
            
        except Exception as e:
            logger.warning(f"Validation failed for {session_id}: {e}")
            return pcm_data, {'error': str(e)}
    
    def _calculate_quality_improvement(
        self,
        initial_stats: Dict[str, Any],
        final_stats: Dict[str, Any]
    ) -> float:
        """Calculate overall quality improvement in dB"""
        try:
            initial_dbfs = initial_stats.get('dbfs', -100)
            final_dbfs = final_stats.get('dbfs', -100)
            
            # Simple quality metric based on signal level improvement
            if initial_dbfs > -100 and final_dbfs > -100:
                # Improvement is positive when final level is higher (less negative dBFS)
                # but capped to avoid rewarding over-amplification
                improvement = min(10, max(0, final_dbfs - initial_dbfs))
                return improvement
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _assess_whisper_compatibility(self, pcm_data: bytes) -> Dict[str, Any]:
        """Assess how well the audio is suited for Whisper processing"""
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Calculate various compatibility metrics
            compatibility = {
                'sample_rate_correct': True,  # Assumed 16kHz
                'mono_audio': True,           # We ensure mono
                'appropriate_level': False,
                'good_dynamic_range': False,
                'speech_frequency_present': False,
                'overall_score': 0.0
            }
            
            # Check signal level (Whisper works best with moderate levels)
            rms = np.sqrt(np.mean(audio_array**2))
            compatibility['appropriate_level'] = 0.01 < rms < 0.5
            
            # Check dynamic range
            dynamic_range = np.max(audio_array) - np.min(audio_array)
            compatibility['good_dynamic_range'] = dynamic_range > 0.1
            
            # Check for speech-like frequency content
            if len(audio_array) >= 512:
                fft = np.fft.fft(audio_array[:512])
                magnitude = np.abs(fft[:256])
                freqs = np.fft.fftfreq(512, 1/self.WHISPER_SAMPLE_RATE)[:256]
                
                # Check for energy in speech frequency range (300-3400 Hz)
                speech_indices = (freqs >= 300) & (freqs <= 3400)
                speech_energy = np.sum(magnitude[speech_indices])
                total_energy = np.sum(magnitude)
                
                speech_ratio = speech_energy / max(total_energy, 1e-10)
                compatibility['speech_frequency_present'] = speech_ratio > 0.3
            
            # Calculate overall score
            score_components = [
                compatibility['sample_rate_correct'],
                compatibility['mono_audio'],
                compatibility['appropriate_level'],
                compatibility['good_dynamic_range'],
                compatibility['speech_frequency_present']
            ]
            compatibility['overall_score'] = sum(score_components) / len(score_components)
            
            return compatibility
            
        except Exception as e:
            logger.warning(f"Whisper compatibility assessment failed: {e}")
            return {'error': str(e), 'overall_score': 0.5}
    
    def _create_preprocessing_result(
        self,
        pcm_data: bytes,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create standardized preprocessing result"""
        return {
            'preprocessed_audio': pcm_data,
            'session_id': session_id,
            'metadata': metadata,
            'ready_for_whisper': not metadata.get('error'),
            'preprocessing_applied': self.educational_mode or self.aggressive_preprocessing
        }
    
    def _update_preprocessing_stats(self, metadata: Dict[str, Any]):
        """Update preprocessing statistics"""
        try:
            self.preprocessing_stats['chunks_preprocessed'] += 1
            
            if 'preprocessing_time' in metadata:
                current_avg = self.preprocessing_stats['average_preprocessing_time']
                count = self.preprocessing_stats['chunks_preprocessed']
                self.preprocessing_stats['average_preprocessing_time'] = (
                    (current_avg * (count - 1) + metadata['preprocessing_time']) / count
                )
            
            if 'quality_improvement' in metadata:
                current_avg = self.preprocessing_stats['average_quality_improvement']
                count = self.preprocessing_stats['chunks_preprocessed']
                self.preprocessing_stats['average_quality_improvement'] = (
                    (current_avg * (count - 1) + metadata['quality_improvement']) / count
                )
            
            # Track specific optimizations applied
            processing_stages = metadata.get('processing_stages', {})
            
            if 'audio_enhancement' in processing_stages:
                # Track enhancements from advanced processor
                pass
            
            if 'whisper_optimization' in processing_stages:
                opt_data = processing_stages['whisper_optimization']
                if 'loudness_normalization' in opt_data:
                    self.preprocessing_stats['loudness_normalization_applied'] += 1
                    
        except Exception as e:
            logger.warning(f"Failed to update preprocessing stats: {e}")
    
    def get_preprocessing_stats(self) -> Dict[str, Any]:
        """Get comprehensive preprocessing statistics"""
        stats = self.preprocessing_stats.copy()
        
        # Add advanced processor stats
        if hasattr(self.advanced_processor, 'get_processing_stats'):
            stats['advanced_processing'] = self.advanced_processor.get_processing_stats()
        
        return stats
    
    def reset_session_state(self, session_id: str):
        """Reset preprocessing state for new session"""
        self._session_audio_profile = None
        
        if hasattr(self.advanced_processor, 'reset_adaptive_filters'):
            self.advanced_processor.reset_adaptive_filters()
        
        logger.debug(f"Preprocessing state reset for session {session_id}")
    
    async def cleanup(self):
        """Cleanup preprocessing resources"""
        # No specific cleanup needed for current implementation
        logger.info("Whisper preprocessor cleanup completed")