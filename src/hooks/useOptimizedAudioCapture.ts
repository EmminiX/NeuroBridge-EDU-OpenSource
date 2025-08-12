/**
 * Optimized Audio Capture Hook for Educational Content
 * Enhanced WebAudio processing with classroom acoustics optimization
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface AudioCaptureConfig {
  sampleRate?: number;
  channelCount?: number;
  bufferSize?: number;
  enablePreprocessing?: boolean;
  educationalMode?: boolean;
  autoGainControl?: boolean;
  noiseSuppression?: boolean;
  echoCancellation?: boolean;
}

interface AudioStats {
  inputLevel: number;
  outputLevel: number;
  gainAdjustment: number;
  currentGain: number;
  processedSamples: number;
  processingTime: number;
  isProcessing: boolean;
}

interface ClassroomParams {
  hvacFreqLow?: number;
  hvacFreqHigh?: number;
  speechFreqLow?: number;
  speechFreqHigh?: number;
  preEmphasisAlpha?: number;
  noiseGateThreshold?: number;
  adaptiveGainTarget?: number;
}

interface UseOptimizedAudioCaptureReturn {
  isRecording: boolean;
  audioLevel: number;
  audioStats: AudioStats;
  error: string | null;
  isSupported: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  updateConfig: (config: Partial<AudioCaptureConfig>) => void;
  updateClassroomParams: (params: ClassroomParams) => void;
  resetFilters: () => void;
  onAudioChunk?: (chunk: ArrayBuffer, timestamp: number, stats: AudioStats) => void;
}

const defaultConfig: AudioCaptureConfig = {
  sampleRate: 16000,
  channelCount: 1,
  bufferSize: 4096,
  enablePreprocessing: true,
  educationalMode: true,
  autoGainControl: false,    // Disable browser AGC to use our own
  noiseSuppression: false,   // Disable browser NS to use our own
  echoCancellation: true     // Keep echo cancellation enabled
};

const defaultClassroomParams: ClassroomParams = {
  hvacFreqLow: 40,
  hvacFreqHigh: 120,
  speechFreqLow: 300,
  speechFreqHigh: 3400,
  preEmphasisAlpha: 0.97,
  noiseGateThreshold: 0.01,
  adaptiveGainTarget: 0.3
};

export const useOptimizedAudioCapture = (
  initialConfig: Partial<AudioCaptureConfig> = {},
  onAudioChunk?: (chunk: ArrayBuffer, timestamp: number, stats: AudioStats) => void
): UseOptimizedAudioCaptureReturn => {
  // State
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioStats, setAudioStats] = useState<AudioStats>({
    inputLevel: 0,
    outputLevel: 0,
    gainAdjustment: 1.0,
    currentGain: 1.0,
    processedSamples: 0,
    processingTime: 0,
    isProcessing: false
  });
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [config, setConfig] = useState<AudioCaptureConfig>({
    ...defaultConfig,
    ...initialConfig
  });
  
  // Refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const analyserNodeRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const classroomParamsRef = useRef<ClassroomParams>(defaultClassroomParams);
  
  // Check browser support
  useEffect(() => {
    const checkSupport = () => {
      const hasWebAudio = !!(window.AudioContext || (window as any).webkitAudioContext);
      const hasMediaDevices = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      const hasAudioWorklet = !!(AudioContext.prototype.audioWorklet);
      
      const supported = hasWebAudio && hasMediaDevices && hasAudioWorklet;
      setIsSupported(supported);
      
      if (!supported) {
        setError('Browser does not support required audio features');
      }
    };
    
    checkSupport();
  }, []);
  
  // Initialize audio context and worklet
  const initializeAudioContext = useCallback(async (): Promise<AudioContext> => {
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      return audioContextRef.current;
    }
    
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({
        sampleRate: config.sampleRate,
        latencyHint: 'interactive'
      });
      
      // Load optimized audio worklet
      await audioContext.audioWorklet.addModule('/optimized-audio-worklet.js');
      
      audioContextRef.current = audioContext;
      return audioContext;
      
    } catch (err) {
      throw new Error(`Failed to initialize audio context: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [config.sampleRate]);
  
  // Create audio processing chain
  const createAudioChain = useCallback(async (
    audioContext: AudioContext,
    mediaStream: MediaStream
  ): Promise<{
    workletNode: AudioWorkletNode;
    analyserNode: AnalyserNode;
  }> => {
    try {
      // Create source node from media stream
      const sourceNode = audioContext.createMediaStreamSource(mediaStream);
      
      // Create optimized audio worklet processor
      const workletNode = new AudioWorkletNode(audioContext, 'optimized-audio-processor', {
        processorOptions: {
          bufferSize: config.bufferSize,
          enablePreprocessing: config.enablePreprocessing,
          educationalMode: config.educationalMode,
          classroomParams: classroomParamsRef.current
        },
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [config.channelCount || 1]
      });
      
      // Create analyser for level monitoring
      const analyserNode = audioContext.createAnalyser();
      analyserNode.fftSize = 512;
      analyserNode.smoothingTimeConstant = 0.8;
      
      // Connect the audio chain: Source -> Worklet -> Analyser
      sourceNode.connect(workletNode);
      workletNode.connect(analyserNode);
      
      // Handle messages from worklet
      workletNode.port.onmessage = (event) => {
        handleWorkletMessage(event.data);
      };
      
      return { workletNode, analyserNode };
      
    } catch (err) {
      throw new Error(`Failed to create audio chain: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  }, [config.bufferSize, config.enablePreprocessing, config.educationalMode, config.channelCount]);
  
  // Handle messages from audio worklet
  const handleWorkletMessage = useCallback((message: any) => {
    switch (message.type) {
      case 'worklet-initialized':
        console.log('Optimized audio worklet initialized:', message.config);
        break;
        
      case 'audio-chunk':
        if (onAudioChunk && message.data) {
          // Convert Int16Array back to ArrayBuffer
          const arrayBuffer = message.data.buffer.slice(
            message.data.byteOffset,
            message.data.byteOffset + message.data.byteLength
          );
          
          const stats: AudioStats = {
            ...message.processingStats,
            isProcessing: true
          };
          
          onAudioChunk(arrayBuffer, message.timestamp, stats);
          setAudioStats(stats);
        }
        break;
        
      case 'stats-response':
        setAudioStats({
          ...message.data,
          isProcessing: isRecording
        });
        break;
        
      case 'config-updated':
        console.log('Audio worklet configuration updated:', message.config);
        break;
        
      case 'error':
        console.error('Audio worklet error:', message.error);
        setError(`Audio processing error: ${message.error}`);
        break;
        
      default:
        console.debug('Unknown worklet message:', message);
    }
  }, [onAudioChunk, isRecording]);
  
  // Audio level monitoring
  const updateAudioLevel = useCallback(() => {
    if (!analyserNodeRef.current || !isRecording) {
      return;
    }
    
    const analyser = analyserNodeRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);
    
    // Calculate average level
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    const normalizedLevel = average / 255;
    
    setAudioLevel(normalizedLevel);
    
    // Schedule next update
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  }, [isRecording]);
  
  // Start recording
  const startRecording = useCallback(async (): Promise<void> => {
    if (!isSupported) {
      throw new Error('Audio capture not supported in this browser');
    }
    
    if (isRecording) {
      return;
    }
    
    try {
      setError(null);
      
      // Get user media with educational optimizations
      const constraints: MediaStreamConstraints = {
        audio: {
          sampleRate: config.sampleRate,
          channelCount: config.channelCount,
          autoGainControl: config.autoGainControl,
          noiseSuppression: config.noiseSuppression,
          echoCancellation: config.echoCancellation,
          // Additional constraints for educational environments
          ...(config.educationalMode && {
            googExperimentalNoiseSuppression: false,  // Use our own noise suppression
            googExperimentalAutoGainControl: false,   // Use our own AGC
            googHighpassFilter: false,                 // Use our own high-pass filter
          })
        },
        video: false
      };
      
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      mediaStreamRef.current = mediaStream;
      
      // Initialize audio context
      const audioContext = await initializeAudioContext();
      
      // Resume audio context if suspended
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
      
      // Create audio processing chain
      const { workletNode, analyserNode } = await createAudioChain(audioContext, mediaStream);
      
      workletNodeRef.current = workletNode;
      analyserNodeRef.current = analyserNode;
      
      setIsRecording(true);
      
      // Start audio level monitoring
      updateAudioLevel();
      
      console.log('Optimized audio capture started with educational processing');
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error starting recording';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [isSupported, isRecording, config, initializeAudioContext, createAudioChain, updateAudioLevel]);
  
  // Stop recording
  const stopRecording = useCallback((): void => {
    setIsRecording(false);
    
    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    
    // Disconnect audio nodes
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    
    if (analyserNodeRef.current) {
      analyserNodeRef.current.disconnect();
      analyserNodeRef.current = null;
    }
    
    // Close audio context
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    // Reset state
    setAudioLevel(0);
    setAudioStats(prev => ({ ...prev, isProcessing: false }));
    setError(null);
    
    console.log('Optimized audio capture stopped');
  }, []);
  
  // Update configuration
  const updateConfig = useCallback((newConfig: Partial<AudioCaptureConfig>): void => {
    setConfig(prev => ({ ...prev, ...newConfig }));
    
    // Send configuration update to worklet if active
    if (workletNodeRef.current && isRecording) {
      workletNodeRef.current.port.postMessage({
        type: 'update-config',
        data: newConfig
      });
    }
  }, [isRecording]);
  
  // Update classroom parameters
  const updateClassroomParams = useCallback((params: ClassroomParams): void => {
    classroomParamsRef.current = { ...classroomParamsRef.current, ...params };
    
    // Send parameter update to worklet if active
    if (workletNodeRef.current && isRecording) {
      workletNodeRef.current.port.postMessage({
        type: 'update-config',
        data: {
          classroomParams: classroomParamsRef.current
        }
      });
    }
  }, [isRecording]);
  
  // Reset filters
  const resetFilters = useCallback((): void => {
    if (workletNodeRef.current) {
      workletNodeRef.current.port.postMessage({
        type: 'reset-filters'
      });
    }
    
    // Reset state
    setAudioStats(prev => ({
      ...prev,
      inputLevel: 0,
      outputLevel: 0,
      gainAdjustment: 1.0,
      currentGain: 1.0,
      processedSamples: 0,
      processingTime: 0
    }));
  }, []);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isRecording) {
        stopRecording();
      }
    };
  }, [isRecording, stopRecording]);
  
  // Periodic stats update
  useEffect(() => {
    if (!isRecording || !workletNodeRef.current) {
      return;
    }
    
    const interval = setInterval(() => {
      workletNodeRef.current?.port.postMessage({
        type: 'get-stats'
      });
    }, 1000); // Update stats every second
    
    return () => clearInterval(interval);
  }, [isRecording]);
  
  return {
    isRecording,
    audioLevel,
    audioStats,
    error,
    isSupported,
    startRecording,
    stopRecording,
    updateConfig,
    updateClassroomParams,
    resetFilters,
    onAudioChunk
  };
};