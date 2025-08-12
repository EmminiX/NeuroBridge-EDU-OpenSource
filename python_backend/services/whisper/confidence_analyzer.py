"""
Confidence Analysis System for Whisper Transcription
Advanced confidence scoring and reliability assessment for educational content
"""

import asyncio
import time
import math
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from utils.logger import get_logger
from .hallucination_filter import HallucinationType

logger = get_logger("whisper.confidence_analyzer")


class ConfidenceLevel(Enum):
    """Confidence levels for transcription reliability"""
    VERY_HIGH = "very_high"    # > 0.9
    HIGH = "high"              # 0.7 - 0.9
    MEDIUM = "medium"          # 0.5 - 0.7
    LOW = "low"                # 0.3 - 0.5
    VERY_LOW = "very_low"      # < 0.3


@dataclass
class ConfidenceAnalysis:
    """Detailed confidence analysis result"""
    overall_confidence: float
    confidence_level: ConfidenceLevel
    reliability_score: float
    factors: Dict[str, float]
    warnings: List[str]
    recommendations: List[str]
    processing_time: float


class ConfidenceAnalyzer:
    """
    Advanced confidence analyzer for educational Whisper transcription
    Combines multiple confidence indicators for reliable assessment
    """
    
    # Confidence level thresholds
    CONFIDENCE_THRESHOLDS = {
        ConfidenceLevel.VERY_HIGH: 0.9,
        ConfidenceLevel.HIGH: 0.7,
        ConfidenceLevel.MEDIUM: 0.5,
        ConfidenceLevel.LOW: 0.3,
        ConfidenceLevel.VERY_LOW: 0.0
    }
    
    # Weights for different confidence factors
    FACTOR_WEIGHTS = {
        'model_confidence': 0.25,      # Raw model confidence score
        'audio_quality': 0.20,        # Audio signal quality
        'linguistic_coherence': 0.15,  # Text coherence and structure
        'length_consistency': 0.10,   # Expected vs actual transcript length
        'educational_context': 0.10,  # Educational content appropriateness
        'repetition_penalty': 0.10,   # Penalty for repetitive content
        'hallucination_risk': 0.10    # Risk of hallucination
    }
    
    def __init__(self, educational_mode: bool = True):
        """
        Initialize confidence analyzer
        
        Args:
            educational_mode: Enable educational content optimizations
        """
        self.educational_mode = educational_mode
        
        # Analysis statistics
        self.analysis_stats = {
            'total_analyzed': 0,
            'confidence_distribution': {level.value: 0 for level in ConfidenceLevel},
            'average_confidence': 0.0,
            'average_reliability': 0.0,
            'factor_contributions': {factor: 0.0 for factor in self.FACTOR_WEIGHTS.keys()},
            'warning_frequency': {},
            'processing_time_avg': 0.0
        }
        
        logger.info(f"Confidence Analyzer initialized - Educational: {educational_mode}")
    
    async def analyze_confidence(
        self,
        transcript: str,
        model_confidence: float,
        audio_stats: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None,
        hallucination_analysis: Optional[Dict[str, Any]] = None
    ) -> ConfidenceAnalysis:
        """
        Comprehensive confidence analysis
        
        Args:
            transcript: Transcribed text
            model_confidence: Raw model confidence score
            audio_stats: Audio quality statistics
            session_context: Session-specific context
            hallucination_analysis: Results from hallucination detection
            
        Returns:
            Detailed confidence analysis
        """
        start_time = time.time()
        
        try:
            # Calculate individual confidence factors
            factors = {}
            warnings = []
            recommendations = []
            
            # Factor 1: Model confidence (normalized)
            factors['model_confidence'] = await self._analyze_model_confidence(
                model_confidence, transcript
            )
            
            # Factor 2: Audio quality assessment
            factors['audio_quality'], audio_warnings = await self._analyze_audio_quality(
                audio_stats, transcript
            )
            warnings.extend(audio_warnings)
            
            # Factor 3: Linguistic coherence
            factors['linguistic_coherence'], ling_warnings = await self._analyze_linguistic_coherence(
                transcript
            )
            warnings.extend(ling_warnings)
            
            # Factor 4: Length consistency
            factors['length_consistency'] = await self._analyze_length_consistency(
                transcript, audio_stats
            )
            
            # Factor 5: Educational context appropriateness
            if self.educational_mode:
                factors['educational_context'], edu_warnings = await self._analyze_educational_context(
                    transcript, session_context
                )
                warnings.extend(edu_warnings)
            else:
                factors['educational_context'] = 0.8  # Neutral for non-educational
            
            # Factor 6: Repetition penalty
            factors['repetition_penalty'] = await self._analyze_repetition_penalty(transcript)
            
            # Factor 7: Hallucination risk assessment
            factors['hallucination_risk'] = await self._analyze_hallucination_risk(
                hallucination_analysis, model_confidence, audio_stats
            )
            
            # Calculate weighted overall confidence
            overall_confidence = sum(
                factors[factor] * self.FACTOR_WEIGHTS[factor]
                for factor in factors
            )
            
            # Determine confidence level
            confidence_level = self._determine_confidence_level(overall_confidence)
            
            # Calculate reliability score (adjusted confidence accounting for uncertainty)
            reliability_score = await self._calculate_reliability_score(
                overall_confidence, factors, audio_stats
            )
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                factors, confidence_level, warnings
            )
            
            # Create analysis result
            analysis = ConfidenceAnalysis(
                overall_confidence=overall_confidence,
                confidence_level=confidence_level,
                reliability_score=reliability_score,
                factors=factors,
                warnings=warnings,
                recommendations=recommendations,
                processing_time=time.time() - start_time
            )
            
            # Update statistics
            self._update_analysis_stats(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Confidence analysis failed: {e}")
            return ConfidenceAnalysis(
                overall_confidence=0.5,  # Neutral fallback
                confidence_level=ConfidenceLevel.MEDIUM,
                reliability_score=0.5,
                factors={},
                warnings=[f"Analysis error: {str(e)}"],
                recommendations=["Manual review recommended due to analysis error"],
                processing_time=time.time() - start_time
            )
    
    async def _analyze_model_confidence(
        self, 
        model_confidence: float, 
        transcript: str
    ) -> float:
        """Analyze raw model confidence with adjustments"""
        try:
            # Normalize model confidence (assume 0-1 range)
            normalized_confidence = max(0.0, min(1.0, model_confidence))
            
            # Adjust for transcript length (very short transcripts are less reliable)
            length_adjustment = 1.0
            word_count = len(transcript.split()) if transcript else 0
            
            if word_count == 0:
                length_adjustment = 0.0
            elif word_count == 1:
                length_adjustment = 0.7
            elif word_count == 2:
                length_adjustment = 0.8
            elif word_count >= 10:
                length_adjustment = 1.0
            else:
                # Linear interpolation for 3-9 words
                length_adjustment = 0.8 + (word_count - 2) * 0.2 / 8
            
            return normalized_confidence * length_adjustment
            
        except Exception as e:
            logger.warning(f"Model confidence analysis failed: {e}")
            return 0.5
    
    async def _analyze_audio_quality(
        self, 
        audio_stats: Dict[str, Any], 
        transcript: str
    ) -> Tuple[float, List[str]]:
        """Analyze audio quality impact on confidence"""
        quality_score = 1.0
        warnings = []
        
        try:
            # Signal level analysis
            dbfs = audio_stats.get('dbfs', -30)
            max_level = audio_stats.get('max_level', 0.1)
            rms_level = audio_stats.get('rms_level', 0.01)
            
            # Optimal range: -20 to -6 dBFS
            if dbfs < -50:
                quality_score *= 0.3
                warnings.append(f"Very low audio level ({dbfs:.1f}dBFS)")
            elif dbfs < -40:
                quality_score *= 0.6
                warnings.append(f"Low audio level ({dbfs:.1f}dBFS)")
            elif dbfs > -6:
                quality_score *= 0.8
                warnings.append(f"High audio level ({dbfs:.1f}dBFS) - possible clipping")
            
            # Dynamic range check
            if 'peak' in audio_stats and 'rms_level' in audio_stats:
                crest_factor = audio_stats.get('peak', 0.1) / max(rms_level, 0.001)
                
                if crest_factor < 2:  # Very compressed/limited audio
                    quality_score *= 0.8
                    warnings.append("Low dynamic range - compressed audio")
                elif crest_factor > 20:  # Very dynamic or noisy
                    quality_score *= 0.7
                    warnings.append("High dynamic range - possibly noisy")
            
            # SNR estimation (if available)
            snr = audio_stats.get('snr', 15)
            if snr < 10:
                quality_score *= 0.5
                warnings.append(f"Low signal-to-noise ratio ({snr:.1f}dB)")
            elif snr < 15:
                quality_score *= 0.7
                warnings.append(f"Moderate signal-to-noise ratio ({snr:.1f}dB)")
            
            # Silence detection alignment
            is_silent = audio_stats.get('is_silent', False)
            if is_silent and transcript:
                quality_score *= 0.2
                warnings.append("Transcript from silent audio - likely hallucination")
            
            return max(0.0, min(1.0, quality_score)), warnings
            
        except Exception as e:
            logger.warning(f"Audio quality analysis failed: {e}")
            return 0.7, [f"Audio analysis error: {str(e)}"]
    
    async def _analyze_linguistic_coherence(self, transcript: str) -> Tuple[float, List[str]]:
        """Analyze linguistic coherence and structure"""
        coherence_score = 1.0
        warnings = []
        
        try:
            if not transcript or not transcript.strip():
                return 0.0, ["Empty transcript"]
            
            words = transcript.strip().split()
            word_count = len(words)
            
            if word_count == 0:
                return 0.0, ["No words in transcript"]
            
            # Basic structural analysis
            sentences = [s.strip() for s in transcript.replace('!', '.').replace('?', '.').split('.') if s.strip()]
            
            # Check for reasonable sentence structure
            if len(sentences) > 1:
                avg_words_per_sentence = word_count / len(sentences)
                
                if avg_words_per_sentence < 1:
                    coherence_score *= 0.5
                    warnings.append("Very short sentences")
                elif avg_words_per_sentence > 50:
                    coherence_score *= 0.7
                    warnings.append("Unusually long sentences")
            
            # Check for excessive repetition at word level
            unique_words = set(word.lower().rstrip('.,!?') for word in words)
            uniqueness_ratio = len(unique_words) / word_count
            
            if uniqueness_ratio < 0.3:
                coherence_score *= 0.4
                warnings.append(f"High word repetition (uniqueness: {uniqueness_ratio:.1%})")
            elif uniqueness_ratio < 0.5:
                coherence_score *= 0.7
                warnings.append(f"Moderate word repetition (uniqueness: {uniqueness_ratio:.1%})")
            
            # Check for common filler word dominance
            filler_words = {'um', 'uh', 'ah', 'oh', 'okay', 'so', 'like', 'well', 'you', 'know'}
            filler_count = sum(1 for word in words if word.lower().rstrip('.,!?') in filler_words)
            filler_ratio = filler_count / word_count
            
            if filler_ratio > 0.6:
                coherence_score *= 0.3
                warnings.append(f"Excessive filler words ({filler_ratio:.1%})")
            elif filler_ratio > 0.4:
                coherence_score *= 0.6
                warnings.append(f"High filler word ratio ({filler_ratio:.1%})")
            
            # Check for reasonable capitalization and punctuation (basic)
            if len(transcript) > 10:
                capital_count = sum(1 for c in transcript if c.isupper())
                capital_ratio = capital_count / len(transcript)
                
                if capital_ratio > 0.5:  # Too many capitals
                    coherence_score *= 0.8
                    warnings.append("Unusual capitalization pattern")
                elif capital_ratio < 0.01 and len(transcript) > 20:  # Too few capitals
                    coherence_score *= 0.9
                    warnings.append("Very low capitalization")
            
            return max(0.0, min(1.0, coherence_score)), warnings
            
        except Exception as e:
            logger.warning(f"Linguistic coherence analysis failed: {e}")
            return 0.7, [f"Linguistic analysis error: {str(e)}"]
    
    async def _analyze_length_consistency(
        self, 
        transcript: str, 
        audio_stats: Dict[str, Any]
    ) -> float:
        """Analyze consistency between audio duration and transcript length"""
        try:
            if not transcript:
                return 0.0
            
            duration_ms = audio_stats.get('duration_ms', 1000)
            duration_s = duration_ms / 1000.0
            word_count = len(transcript.split())
            
            if duration_s <= 0 or word_count <= 0:
                return 0.5  # Neutral if no data
            
            # Typical speaking rates: 120-180 words per minute (2-3 words per second)
            # For educational content, might be slower: 100-150 WPM (1.7-2.5 WPS)
            expected_wps_min = 1.0   # Slow, careful educational speech
            expected_wps_max = 4.0   # Fast conversational speech
            
            actual_wps = word_count / duration_s
            
            # Calculate consistency score
            if expected_wps_min <= actual_wps <= expected_wps_max:
                consistency_score = 1.0
            elif actual_wps < expected_wps_min:
                # Too few words for duration - might be lots of silence or errors
                consistency_score = max(0.3, actual_wps / expected_wps_min)
            else:
                # Too many words for duration - might be hallucination
                consistency_score = max(0.2, expected_wps_max / actual_wps)
            
            return consistency_score
            
        except Exception as e:
            logger.warning(f"Length consistency analysis failed: {e}")
            return 0.7
    
    async def _analyze_educational_context(
        self, 
        transcript: str, 
        session_context: Optional[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """Analyze appropriateness for educational content"""
        context_score = 1.0
        warnings = []
        
        try:
            if not transcript:
                return 0.0, ["Empty transcript"]
            
            # Check for educational appropriateness
            words = transcript.lower().split()
            
            # Educational vocabulary indicators
            educational_indicators = {
                'academic': {'professor', 'student', 'class', 'course', 'lecture', 'study', 'learn', 'teach'},
                'questioning': {'question', 'answer', 'explain', 'understand', 'clarify', 'discuss'},
                'technical': {'analysis', 'method', 'theory', 'concept', 'principle', 'research'},
                'instructional': {'example', 'demonstrates', 'shows', 'illustrates', 'means', 'definition'}
            }
            
            # Count educational indicators
            edu_score = 0.0
            for category, terms in educational_indicators.items():
                matches = sum(1 for word in words if any(term in word for term in terms))
                edu_score += matches * 0.1  # Each match adds 0.1
            
            # Normalize educational score
            edu_score = min(1.0, edu_score / len(words) * 10) if words else 0.0
            
            # Check for non-educational patterns
            non_edu_patterns = {
                'social_media': {'subscribe', 'like', 'follow', 'channel', 'video'},
                'commercial': {'buy', 'sell', 'price', 'deal', 'offer', 'discount'},
                'gaming': {'player', 'game', 'level', 'score', 'play'}
            }
            
            non_edu_penalty = 0.0
            for category, terms in non_edu_patterns.items():
                matches = sum(1 for word in words if any(term in word for term in terms))
                if matches > 0:
                    non_edu_penalty += 0.3
                    warnings.append(f"Non-educational content detected: {category}")
            
            # Final educational context score
            context_score = max(0.1, min(1.0, 0.7 + edu_score - non_edu_penalty))
            
            return context_score, warnings
            
        except Exception as e:
            logger.warning(f"Educational context analysis failed: {e}")
            return 0.7, [f"Context analysis error: {str(e)}"]
    
    async def _analyze_repetition_penalty(self, transcript: str) -> float:
        """Calculate penalty for repetitive content"""
        try:
            if not transcript:
                return 1.0
            
            words = transcript.lower().split()
            if len(words) <= 1:
                return 1.0
            
            # Calculate repetition metrics
            unique_words = len(set(words))
            total_words = len(words)
            uniqueness_ratio = unique_words / total_words
            
            # Penalty for low uniqueness
            if uniqueness_ratio < 0.3:
                return 0.2  # Heavy penalty
            elif uniqueness_ratio < 0.5:
                return 0.5  # Moderate penalty
            elif uniqueness_ratio < 0.7:
                return 0.8  # Light penalty
            else:
                return 1.0  # No penalty
            
        except Exception as e:
            logger.warning(f"Repetition analysis failed: {e}")
            return 0.8
    
    async def _analyze_hallucination_risk(
        self, 
        hallucination_analysis: Optional[Dict[str, Any]],
        model_confidence: float,
        audio_stats: Dict[str, Any]
    ) -> float:
        """Analyze risk of hallucination affecting confidence"""
        try:
            # If hallucination analysis available, use it
            if hallucination_analysis:
                if hallucination_analysis.get('is_hallucination', False):
                    return 0.1  # Very low confidence if hallucination detected
                
                # Use inverse of hallucination confidence as reliability factor
                hall_confidence = hallucination_analysis.get('confidence_score', 0.0)
                return max(0.1, 1.0 - hall_confidence)
            
            # Fallback: estimate hallucination risk from available data
            risk_factors = []
            
            # High model confidence with poor audio is suspicious
            dbfs = audio_stats.get('dbfs', -30)
            if model_confidence > 0.8 and dbfs < -45:
                risk_factors.append(0.3)
            
            # Very quiet audio is prone to hallucinations
            if dbfs < -50:
                risk_factors.append(0.4)
            
            # Silent audio with any confidence is suspicious
            if audio_stats.get('is_silent', False) and model_confidence > 0.1:
                risk_factors.append(0.6)
            
            # Calculate overall risk
            if not risk_factors:
                return 0.8  # Default low risk
            
            max_risk = max(risk_factors)
            return max(0.1, 1.0 - max_risk)
            
        except Exception as e:
            logger.warning(f"Hallucination risk analysis failed: {e}")
            return 0.7
    
    async def _calculate_reliability_score(
        self, 
        overall_confidence: float,
        factors: Dict[str, float],
        audio_stats: Dict[str, Any]
    ) -> float:
        """Calculate reliability score accounting for uncertainty factors"""
        try:
            reliability = overall_confidence
            
            # Adjust for consistency between factors
            factor_values = list(factors.values())
            if len(factor_values) > 1:
                factor_std = np.std(factor_values)
                if factor_std > 0.3:  # High variance between factors
                    reliability *= 0.8
                elif factor_std > 0.2:
                    reliability *= 0.9
            
            # Audio quality strongly affects reliability
            audio_quality = factors.get('audio_quality', 0.7)
            if audio_quality < 0.5:
                reliability *= 0.7
            
            # Hallucination risk affects reliability
            hall_risk = factors.get('hallucination_risk', 0.8)
            if hall_risk < 0.5:
                reliability *= 0.6
            
            return max(0.0, min(1.0, reliability))
            
        except Exception as e:
            logger.warning(f"Reliability calculation failed: {e}")
            return overall_confidence * 0.8
    
    def _determine_confidence_level(self, overall_confidence: float) -> ConfidenceLevel:
        """Determine confidence level from score"""
        for level in [ConfidenceLevel.VERY_HIGH, ConfidenceLevel.HIGH, 
                     ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]:
            if overall_confidence >= self.CONFIDENCE_THRESHOLDS[level]:
                return level
        return ConfidenceLevel.VERY_LOW
    
    async def _generate_recommendations(
        self, 
        factors: Dict[str, float],
        confidence_level: ConfidenceLevel,
        warnings: List[str]
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        try:
            # Audio quality recommendations
            if factors.get('audio_quality', 1.0) < 0.5:
                recommendations.append("Improve audio quality: check microphone placement and reduce background noise")
            
            # Model confidence recommendations
            if factors.get('model_confidence', 1.0) < 0.4:
                recommendations.append("Low model confidence: consider manual review or re-recording")
            
            # Linguistic coherence recommendations
            if factors.get('linguistic_coherence', 1.0) < 0.5:
                recommendations.append("Poor text coherence: transcript may contain errors or hallucinations")
            
            # Educational context recommendations
            if self.educational_mode and factors.get('educational_context', 1.0) < 0.5:
                recommendations.append("Content may not be educational in nature - verify context")
            
            # Overall confidence recommendations
            if confidence_level == ConfidenceLevel.VERY_LOW:
                recommendations.append("Very low confidence: manual verification strongly recommended")
            elif confidence_level == ConfidenceLevel.LOW:
                recommendations.append("Low confidence: consider manual review")
            elif confidence_level == ConfidenceLevel.MEDIUM:
                recommendations.append("Medium confidence: spot-check recommended for critical applications")
            
            # Hallucination risk recommendations
            if factors.get('hallucination_risk', 1.0) < 0.3:
                recommendations.append("High hallucination risk: transcript likely contains artificial content")
            
            # Length consistency recommendations
            if factors.get('length_consistency', 1.0) < 0.4:
                recommendations.append("Transcript length inconsistent with audio duration - verify accuracy")
            
            if not recommendations:
                recommendations.append("Transcript appears reliable - no specific concerns detected")
            
        except Exception as e:
            logger.warning(f"Recommendation generation failed: {e}")
            recommendations.append("Unable to generate recommendations due to analysis error")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _update_analysis_stats(self, analysis: ConfidenceAnalysis):
        """Update analysis statistics"""
        try:
            self.analysis_stats['total_analyzed'] += 1
            
            # Update confidence level distribution
            self.analysis_stats['confidence_distribution'][analysis.confidence_level.value] += 1
            
            # Update average confidence
            current_avg_conf = self.analysis_stats['average_confidence']
            count = self.analysis_stats['total_analyzed']
            self.analysis_stats['average_confidence'] = (
                (current_avg_conf * (count - 1) + analysis.overall_confidence) / count
            )
            
            # Update average reliability
            current_avg_rel = self.analysis_stats['average_reliability']
            self.analysis_stats['average_reliability'] = (
                (current_avg_rel * (count - 1) + analysis.reliability_score) / count
            )
            
            # Update factor contributions
            for factor, value in analysis.factors.items():
                if factor in self.analysis_stats['factor_contributions']:
                    current_avg = self.analysis_stats['factor_contributions'][factor]
                    self.analysis_stats['factor_contributions'][factor] = (
                        (current_avg * (count - 1) + value) / count
                    )
            
            # Update warning frequency
            for warning in analysis.warnings:
                warning_key = warning[:50]  # Truncate for key
                self.analysis_stats['warning_frequency'][warning_key] = (
                    self.analysis_stats['warning_frequency'].get(warning_key, 0) + 1
                )
            
            # Update processing time
            current_avg_time = self.analysis_stats['processing_time_avg']
            self.analysis_stats['processing_time_avg'] = (
                (current_avg_time * (count - 1) + analysis.processing_time) / count
            )
            
        except Exception as e:
            logger.warning(f"Stats update failed: {e}")
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get comprehensive analysis statistics"""
        return self.analysis_stats.copy()
    
    def get_confidence_summary(self, analyses: List[ConfidenceAnalysis]) -> Dict[str, Any]:
        """Generate summary statistics for a list of confidence analyses"""
        if not analyses:
            return {"message": "No analyses provided"}
        
        try:
            confidences = [a.overall_confidence for a in analyses]
            reliabilities = [a.reliability_score for a in analyses]
            
            summary = {
                'total_analyses': len(analyses),
                'average_confidence': np.mean(confidences),
                'median_confidence': np.median(confidences),
                'confidence_std': np.std(confidences),
                'average_reliability': np.mean(reliabilities),
                'reliability_std': np.std(reliabilities),
                'confidence_levels': {
                    level.value: sum(1 for a in analyses if a.confidence_level == level)
                    for level in ConfidenceLevel
                },
                'high_confidence_ratio': sum(
                    1 for a in analyses 
                    if a.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]
                ) / len(analyses),
                'low_confidence_ratio': sum(
                    1 for a in analyses 
                    if a.confidence_level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
                ) / len(analyses)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Confidence summary generation failed: {e}")
            return {"error": str(e)}