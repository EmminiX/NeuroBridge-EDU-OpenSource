"""
Optimized Whisper Model Parameters for Educational Content
Dynamic parameter selection and optimization for maximum performance
"""

import asyncio
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger("whisper.optimized_params")


class ContentType(Enum):
    """Educational content types with different optimization needs"""
    LECTURE = "lecture"           # Long-form presentations
    DISCUSSION = "discussion"     # Interactive classroom discussion  
    QA_SESSION = "qa_session"     # Question and answer periods
    PRESENTATION = "presentation" # Student presentations
    LAB_SESSION = "lab_session"   # Hands-on laboratory work
    SEMINAR = "seminar"          # Small group discussions
    UNKNOWN = "unknown"          # Undetermined content type


class AudioQuality(Enum):
    """Audio quality levels for parameter optimization"""
    HIGH = "high"         # Clear, close-mic recording
    MEDIUM = "medium"     # Typical classroom recording
    LOW = "low"          # Distant, noisy, or poor recording
    VERY_LOW = "very_low" # Challenging audio conditions


@dataclass
class OptimizedWhisperParams:
    """Container for optimized Whisper parameters"""
    # Core transcription parameters
    beam_size: int = 5
    best_of: int = 5
    temperature: Union[float, Tuple[float, ...]] = 0.0
    
    # Quality control parameters
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_captions_threshold: float = 0.6
    
    # Processing parameters
    condition_on_previous_text: bool = False
    word_timestamps: bool = False
    prepend_punctuations: str = "\"'"¿([{-"
    append_punctuations: str = "\"'.。,，!！?？:：")]}、"
    
    # Educational-specific parameters
    initial_prompt: Optional[str] = None
    language: str = "en"
    suppress_tokens: List[int] = None
    
    # Performance metadata
    expected_rtf: float = 1.0  # Real-time factor
    memory_usage_mb: float = 0.0
    optimization_reason: str = ""


class WhisperParameterOptimizer:
    """
    Dynamic Whisper parameter optimizer for educational content
    Selects optimal parameters based on content type, audio quality, and performance requirements
    """
    
    # Educational content parameter profiles
    EDUCATIONAL_PROFILES = {
        ContentType.LECTURE: {
            "beam_size": 5,
            "best_of": 3,
            "temperature": (0.0, 0.2, 0.4),  # Temperature fallback for long content
            "compression_ratio_threshold": 2.2,  # More lenient for educational jargon
            "log_prob_threshold": -0.8,
            "condition_on_previous_text": True,  # Better context for long-form content
            "word_timestamps": True,  # Useful for lecture navigation
            "expected_rtf": 8.0
        },
        ContentType.DISCUSSION: {
            "beam_size": 3,
            "best_of": 2,
            "temperature": 0.0,  # Deterministic for overlapping speech
            "compression_ratio_threshold": 2.6,
            "log_prob_threshold": -1.0,
            "condition_on_previous_text": False,  # Reduce cross-talk artifacts
            "word_timestamps": False,  # Faster for real-time
            "expected_rtf": 12.0
        },
        ContentType.QA_SESSION: {
            "beam_size": 1,  # Fast inference for real-time
            "best_of": 1,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.8,  # Lenient for short questions
            "log_prob_threshold": -1.2,
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "expected_rtf": 20.0
        },
        ContentType.PRESENTATION: {
            "beam_size": 5,
            "best_of": 5,
            "temperature": (0.0, 0.2),
            "compression_ratio_threshold": 2.0,  # High quality for presentations
            "log_prob_threshold": -0.6,
            "condition_on_previous_text": True,
            "word_timestamps": True,
            "expected_rtf": 6.0
        },
        ContentType.UNKNOWN: {
            "beam_size": 3,
            "best_of": 2,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "expected_rtf": 10.0
        }
    }
    
    # Quality-based adjustments
    QUALITY_ADJUSTMENTS = {
        AudioQuality.HIGH: {
            "beam_size_multiplier": 1.0,
            "temperature_adjustment": 0.0,
            "threshold_adjustment": 0.0,
            "rtf_multiplier": 1.0
        },
        AudioQuality.MEDIUM: {
            "beam_size_multiplier": 1.2,
            "temperature_adjustment": 0.1,
            "threshold_adjustment": -0.2,
            "rtf_multiplier": 0.8
        },
        AudioQuality.LOW: {
            "beam_size_multiplier": 1.5,
            "temperature_adjustment": 0.2,
            "threshold_adjustment": -0.5,
            "rtf_multiplier": 0.6
        },
        AudioQuality.VERY_LOW: {
            "beam_size_multiplier": 2.0,
            "temperature_adjustment": 0.4,
            "threshold_adjustment": -0.8,
            "rtf_multiplier": 0.4
        }
    }
    
    # Educational prompts for different contexts
    EDUCATIONAL_PROMPTS = {
        ContentType.LECTURE: [
            "University lecture with technical terminology, proper nouns, and academic concepts.",
            "Educational presentation covering course material with student questions.",
            "Professor explaining complex topics with examples and detailed explanations."
        ],
        ContentType.DISCUSSION: [
            "Classroom discussion with multiple speakers and interactive dialogue.",
            "Student and instructor conversation covering academic topics.",
            "Group discussion with questions, answers, and collaborative learning."
        ],
        ContentType.QA_SESSION: [
            "Question and answer session with brief exchanges.",
            "Student questions with instructor responses in educational setting.",
            "Interactive Q&A covering course concepts and clarifications."
        ],
        ContentType.PRESENTATION: [
            "Student presentation with academic content and structured delivery.",
            "Formal presentation covering research topics and scholarly material.",
            "Educational presentation with technical terms and proper citations."
        ]
    }
    
    def __init__(self):
        """Initialize parameter optimizer"""
        self.optimization_history: List[Dict[str, Any]] = []
        self.performance_cache: Dict[str, Dict[str, Any]] = {}
        self.adaptive_learning_enabled = True
        
        logger.info("Whisper Parameter Optimizer initialized")
    
    async def get_optimized_parameters(
        self,
        content_type: ContentType = ContentType.UNKNOWN,
        audio_quality: AudioQuality = AudioQuality.MEDIUM,
        audio_duration_s: float = 0.0,
        session_id: str = "",
        real_time_requirement: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> OptimizedWhisperParams:
        """
        Get optimized Whisper parameters for specific educational content
        
        Args:
            content_type: Type of educational content
            audio_quality: Assessed audio quality level
            audio_duration_s: Duration of audio segment
            session_id: Session identifier for tracking
            real_time_requirement: Whether real-time processing is needed
            context: Additional context information
            
        Returns:
            Optimized Whisper parameters
        """
        try:
            # Start with base profile for content type
            base_params = self.EDUCATIONAL_PROFILES.get(
                content_type, self.EDUCATIONAL_PROFILES[ContentType.UNKNOWN]
            ).copy()
            
            # Apply quality adjustments
            quality_adjustments = self.QUALITY_ADJUSTMENTS[audio_quality]
            
            # Adjust beam size based on quality
            base_params["beam_size"] = max(
                1, int(base_params["beam_size"] * quality_adjustments["beam_size_multiplier"])
            )
            
            # Adjust temperature
            if isinstance(base_params["temperature"], tuple):
                adjusted_temps = tuple(
                    max(0.0, min(1.0, temp + quality_adjustments["temperature_adjustment"]))
                    for temp in base_params["temperature"]
                )
                base_params["temperature"] = adjusted_temps
            else:
                base_params["temperature"] = max(
                    0.0, min(1.0, base_params["temperature"] + quality_adjustments["temperature_adjustment"])
                )
            
            # Adjust thresholds
            base_params["log_prob_threshold"] += quality_adjustments["threshold_adjustment"]
            
            # Real-time optimizations
            if real_time_requirement:
                base_params = self._apply_realtime_optimizations(base_params)
            
            # Duration-based optimizations
            if audio_duration_s > 0:
                base_params = self._apply_duration_optimizations(base_params, audio_duration_s)
            
            # Create optimized parameters object
            optimized_params = OptimizedWhisperParams(
                beam_size=base_params["beam_size"],
                best_of=base_params.get("best_of", 1),
                temperature=base_params["temperature"],
                compression_ratio_threshold=base_params["compression_ratio_threshold"],
                log_prob_threshold=base_params["log_prob_threshold"],
                no_captions_threshold=base_params.get("no_captions_threshold", 0.6),
                condition_on_previous_text=base_params["condition_on_previous_text"],
                word_timestamps=base_params["word_timestamps"],
                initial_prompt=self._generate_educational_prompt(content_type),
                language="en",
                suppress_tokens=self._get_educational_suppress_tokens(),
                expected_rtf=base_params["expected_rtf"] * quality_adjustments["rtf_multiplier"],
                optimization_reason=f"content_type={content_type.value}, quality={audio_quality.value}, realtime={real_time_requirement}"
            )
            
            # Apply adaptive learning if enabled
            if self.adaptive_learning_enabled and session_id:
                optimized_params = await self._apply_adaptive_learning(
                    optimized_params, session_id, context
                )
            
            # Log optimization decision
            logger.debug(f"Optimized parameters for {session_id}: "
                        f"beam_size={optimized_params.beam_size}, "
                        f"temperature={optimized_params.temperature}, "
                        f"expected_rtf={optimized_params.expected_rtf:.1f}x")
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return self._get_fallback_parameters()
    
    def _apply_realtime_optimizations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply optimizations for real-time processing requirements"""
        optimized = params.copy()
        
        # Prioritize speed over quality for real-time
        optimized["beam_size"] = min(optimized["beam_size"], 3)
        optimized["best_of"] = min(optimized.get("best_of", 1), 2)
        optimized["word_timestamps"] = False  # Disable for speed
        optimized["condition_on_previous_text"] = False  # Reduce processing overhead
        
        # Use single temperature for consistency
        if isinstance(optimized["temperature"], tuple):
            optimized["temperature"] = optimized["temperature"][0]
        
        return optimized
    
    def _apply_duration_optimizations(
        self, 
        params: Dict[str, Any], 
        duration_s: float
    ) -> Dict[str, Any]:
        """Apply optimizations based on audio segment duration"""
        optimized = params.copy()
        
        if duration_s < 2.0:  # Short segments
            # Use faster parameters for short audio
            optimized["beam_size"] = max(1, optimized["beam_size"] - 1)
            optimized["best_of"] = 1
            optimized["condition_on_previous_text"] = False
            
        elif duration_s > 30.0:  # Long segments
            # Use higher quality parameters for long content
            optimized["beam_size"] = min(optimized["beam_size"] + 1, 8)
            optimized["condition_on_previous_text"] = True
            optimized["word_timestamps"] = True
            
            # Use temperature fallback for long content
            if isinstance(optimized["temperature"], (int, float)):
                optimized["temperature"] = (optimized["temperature"], 0.2, 0.4)
        
        return optimized
    
    def _generate_educational_prompt(self, content_type: ContentType) -> str:
        """Generate context-appropriate prompt for educational content"""
        prompts = self.EDUCATIONAL_PROMPTS.get(content_type, [])
        
        if not prompts:
            return None
        
        # Rotate through different prompts to avoid bias
        import random
        return random.choice(prompts)
    
    def _get_educational_suppress_tokens(self) -> List[int]:
        """Get tokens to suppress for educational content"""
        # Common suppression tokens for educational settings
        # These token IDs are approximate and would need to be verified
        # for the specific Whisper tokenizer
        suppress_tokens = [
            # Social media related tokens
            50257,  # <|endoftext|>
            # Common YouTube/video patterns
            # Would need actual token IDs for "thanks for watching", etc.
        ]
        return suppress_tokens
    
    async def _apply_adaptive_learning(
        self,
        params: OptimizedWhisperParams,
        session_id: str,
        context: Optional[Dict[str, Any]]
    ) -> OptimizedWhisperParams:
        """Apply adaptive learning based on historical performance"""
        try:
            # Check if we have performance history for similar contexts
            cache_key = self._generate_cache_key(params, context)
            
            if cache_key in self.performance_cache:
                cached_data = self.performance_cache[cache_key]
                
                # Adjust parameters based on historical performance
                if cached_data.get("avg_rtf", 0) < params.expected_rtf * 0.8:
                    # Historical performance was better than expected - can increase quality
                    params.beam_size = min(params.beam_size + 1, 8)
                elif cached_data.get("avg_rtf", 0) > params.expected_rtf * 1.2:
                    # Historical performance was worse - reduce quality for speed
                    params.beam_size = max(params.beam_size - 1, 1)
                
                params.optimization_reason += f", adaptive_learning_applied"
            
            return params
            
        except Exception as e:
            logger.warning(f"Adaptive learning failed for {session_id}: {e}")
            return params
    
    def record_performance(
        self,
        params: OptimizedWhisperParams,
        actual_rtf: float,
        accuracy_metrics: Optional[Dict[str, float]] = None,
        session_id: str = "",
        context: Optional[Dict[str, Any]] = None
    ):
        """Record performance data for adaptive learning"""
        try:
            performance_record = {
                "timestamp": time.time(),
                "session_id": session_id,
                "params": params,
                "actual_rtf": actual_rtf,
                "accuracy_metrics": accuracy_metrics or {},
                "context": context or {}
            }
            
            self.optimization_history.append(performance_record)
            
            # Update performance cache
            cache_key = self._generate_cache_key(params, context)
            
            if cache_key not in self.performance_cache:
                self.performance_cache[cache_key] = {
                    "count": 0,
                    "avg_rtf": 0.0,
                    "avg_accuracy": 0.0
                }
            
            cache_data = self.performance_cache[cache_key]
            cache_data["count"] += 1
            
            # Update running averages
            alpha = 0.1  # Exponential moving average factor
            cache_data["avg_rtf"] = (
                alpha * actual_rtf + (1 - alpha) * cache_data["avg_rtf"]
                if cache_data["avg_rtf"] > 0 else actual_rtf
            )
            
            if accuracy_metrics and "overall_accuracy" in accuracy_metrics:
                cache_data["avg_accuracy"] = (
                    alpha * accuracy_metrics["overall_accuracy"] + 
                    (1 - alpha) * cache_data["avg_accuracy"]
                    if cache_data["avg_accuracy"] > 0 else accuracy_metrics["overall_accuracy"]
                )
            
            # Limit history size
            if len(self.optimization_history) > 1000:
                self.optimization_history = self.optimization_history[-500:]
            
        except Exception as e:
            logger.error(f"Failed to record performance: {e}")
    
    def _generate_cache_key(
        self, 
        params: OptimizedWhisperParams, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for performance tracking"""
        try:
            key_components = [
                f"beam_{params.beam_size}",
                f"temp_{str(params.temperature)[:10]}",  # Truncate for key length
                f"cond_{params.condition_on_previous_text}",
                f"words_{params.word_timestamps}"
            ]
            
            if context:
                key_components.extend([
                    f"content_{context.get('content_type', 'unknown')}",
                    f"quality_{context.get('audio_quality', 'medium')}"
                ])
            
            return "_".join(key_components)
            
        except Exception:
            return "default"
    
    def _get_fallback_parameters(self) -> OptimizedWhisperParams:
        """Get safe fallback parameters"""
        return OptimizedWhisperParams(
            beam_size=1,
            best_of=1,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_captions_threshold=0.6,
            condition_on_previous_text=False,
            word_timestamps=False,
            initial_prompt=None,
            language="en",
            expected_rtf=15.0,
            optimization_reason="fallback_safe_parameters"
        )
    
    def detect_content_type(
        self, 
        audio_characteristics: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None
    ) -> ContentType:
        """Automatically detect educational content type from audio characteristics"""
        try:
            # Simple heuristics for content type detection
            duration = audio_characteristics.get("duration_ms", 0) / 1000.0
            
            # Long duration suggests lecture
            if duration > 300:  # > 5 minutes
                return ContentType.LECTURE
            
            # Short duration suggests Q&A
            elif duration < 30:  # < 30 seconds
                return ContentType.QA_SESSION
            
            # Medium duration could be discussion or presentation
            else:
                # Could add more sophisticated detection here
                # For now, default to discussion for interactive content
                return ContentType.DISCUSSION
                
        except Exception as e:
            logger.warning(f"Content type detection failed: {e}")
            return ContentType.UNKNOWN
    
    def assess_audio_quality(
        self, 
        audio_characteristics: Dict[str, Any]
    ) -> AudioQuality:
        """Assess audio quality from characteristics"""
        try:
            # Use audio statistics to determine quality
            snr = audio_characteristics.get("snr", 0)
            dbfs = audio_characteristics.get("dbfs", -100)
            speech_probability = audio_characteristics.get("speech_probability", 0)
            
            # Quality assessment based on multiple factors
            quality_score = 0
            
            # SNR contribution
            if snr > 20:
                quality_score += 3
            elif snr > 10:
                quality_score += 2
            elif snr > 5:
                quality_score += 1
            
            # Level contribution
            if -12 <= dbfs <= -6:  # Good level
                quality_score += 2
            elif -20 <= dbfs <= -12:  # Acceptable level
                quality_score += 1
            
            # Speech presence contribution
            if speech_probability > 0.8:
                quality_score += 2
            elif speech_probability > 0.6:
                quality_score += 1
            
            # Map score to quality level
            if quality_score >= 6:
                return AudioQuality.HIGH
            elif quality_score >= 4:
                return AudioQuality.MEDIUM
            elif quality_score >= 2:
                return AudioQuality.LOW
            else:
                return AudioQuality.VERY_LOW
                
        except Exception as e:
            logger.warning(f"Audio quality assessment failed: {e}")
            return AudioQuality.MEDIUM
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization performance statistics"""
        try:
            if not self.optimization_history:
                return {"message": "No optimization history available"}
            
            recent_history = self.optimization_history[-100:]  # Last 100 optimizations
            
            rtfs = [record["actual_rtf"] for record in recent_history if record["actual_rtf"] > 0]
            avg_rtf = np.mean(rtfs) if rtfs else 0.0
            
            return {
                "total_optimizations": len(self.optimization_history),
                "recent_optimizations": len(recent_history),
                "average_rtf": avg_rtf,
                "cache_entries": len(self.performance_cache),
                "adaptive_learning_enabled": self.adaptive_learning_enabled
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimization stats: {e}")
            return {"error": str(e)}