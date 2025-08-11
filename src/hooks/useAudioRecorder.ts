/**
 * Audio Recorder Hook
 * 
 * Manages audio recording using Web Audio API with real-time
 * audio level monitoring and streaming to WebSocket.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useAppStore } from '@/stores/appStore';
import type { AudioRecorderState } from '@/types';

interface UseAudioRecorderOptions {
  sampleRate?: number;
  bufferSize?: number;
  audioDeviceId?: string;
}

export const useAudioRecorder = (
  sendAudioData: (data: Float32Array) => void,
  options: UseAudioRecorderOptions = {}
) => {
  const {
    sampleRate = 16000,
    bufferSize = 4096,
    audioDeviceId,
  } = options;

  const [state, setState] = useState<AudioRecorderState>({
    isRecording: false,
    isPaused: false,
    duration: 0,
    audioLevel: 0,
    deviceId: audioDeviceId,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);

  const { setRecording, setAudioLevel, addError } = useAppStore();

  // Get available audio devices
  const getAudioDevices = useCallback(async (): Promise<MediaDeviceInfo[]> => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('Error getting audio devices:', error);
      return [];
    }
  }, []);

  // Initialize audio context with AudioWorklet
  const initializeAudioContext = useCallback(async (stream: MediaStream) => {
    try {
      // CRITICAL FIX: Don't force sample rate - let browser use its native rate
      // The forced 16kHz was causing audio distortion/buzzing
      // Explicitly request microphone permission first to ensure proper audio context
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Ensure audio context is running (required for Chrome)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      console.log('🎤 Audio context created:', {
        requestedSampleRate: sampleRate,
        actualSampleRate: audioContextRef.current.sampleRate,
        state: audioContextRef.current.state
      });

      // Load AudioWorklet processor
      await audioContextRef.current.audioWorklet.addModule('/audio-worklet-processor.js');

      const source = audioContextRef.current.createMediaStreamSource(stream);
      
      // Create analyzer for audio level monitoring
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;
      
      // Create AudioWorklet node
      workletNodeRef.current = new AudioWorkletNode(
        audioContextRef.current, 
        'audio-recorder-worklet-processor'
      );
      
      // Handle messages from worklet
      workletNodeRef.current.port.onmessage = (event) => {
        const { type, data } = event.data;
        
        if (type === 'audioData') {
          // Update audio level in both local state and global store
          setState(prev => ({ ...prev, audioLevel: data.audioLevel }));
          setAudioLevel(data.audioLevel);
          
          // Get current state from store to avoid stale closures
          const currentState = useAppStore.getState();
          const isCurrentlyRecording = currentState.isRecording;
          const isSessionReady = currentState.transcriptionSessionReady;
          
          console.log('🎤 Audio worklet data received:', {
            isRecording: isCurrentlyRecording,
            isPaused: state.isPaused,
            sessionReady: isSessionReady,
            audioLevel: data.audioLevel,
            audioBufferSize: data.audioBuffer?.length || 0, // Now Float32Array, so use .length
            sampleRate: data.sampleRate,
            actualContextRate: audioContextRef.current?.sampleRate,
            audioBufferType: data.audioBuffer?.constructor?.name || 'unknown',
            // ADDED: Sample a few values to check if real audio data
            sampleValues: data.audioBuffer ? Array.from(data.audioBuffer.slice(0, 5) as Float32Array).map(x => x.toFixed(6)) : []
          });
          
          // Send audio data if recording AND session is ready (HTTP + SSE architecture)
          if (isCurrentlyRecording && !state.isPaused && isSessionReady) {
            console.log('🚀 Sending audio data via HTTP + SSE');
            // CRITICAL FIX: data.audioBuffer is now Float32Array, not ArrayBuffer
            sendAudioData(data.audioBuffer);
          } else {
            console.log('⚠️ Audio data not sent - requirements not met:', {
              recording: isCurrentlyRecording,
              notPaused: !state.isPaused,
              sessionReady: isSessionReady
            });
          }
        }
      };
      
      // Connect nodes - FIXED: Connect source to worklet to receive audio!
      source.connect(analyserRef.current);
      source.connect(workletNodeRef.current);  // CRITICAL: Connect source directly to worklet
      // analyserRef.current.connect(workletNodeRef.current); // This was wrong - analyser doesn't pass audio through
      // Note: Don't connect worklet to destination to avoid feedback

      // Start the worklet processing
      workletNodeRef.current.port.postMessage({ 
        type: 'start',
        data: { sampleRate: audioContextRef.current.sampleRate }
      });

      return true;
    } catch (error) {
      console.error('Error initializing audio context:', error);
      addError({
        code: 'AUDIO_CONTEXT_ERROR',
        message: 'Failed to initialize audio context',
        timestamp: new Date().toISOString(),
      });
      return false;
    }
  }, [sampleRate, bufferSize, sendAudioData, addError, state.isRecording, state.isPaused]);

  // Audio level monitoring is now handled by the AudioWorklet processor
  // This provides more accurate real-time audio levels without interference

  // Start recording
  const startRecording = useCallback(async (): Promise<boolean> => {
    try {
      // Request microphone access with optimal settings for speech recognition
      // IMPORTANT: Disable audio processing to get raw audio data
      const constraints: MediaStreamConstraints = {
        audio: {
          deviceId: state.deviceId ? { exact: state.deviceId } : undefined,
          // Don't force sampleRate here - let the system choose optimal rate
          channelCount: 1,
          echoCancellation: false,  // CHANGED: Disable to get raw audio
          noiseSuppression: false,  // CHANGED: Disable to get raw audio
          autoGainControl: false    // CHANGED: Disable to get raw audio
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      // Initialize audio processing (now async)
      if (!(await initializeAudioContext(stream))) {
        return false;
      }

      // Create MediaRecorder for fallback
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
          ? 'audio/webm;codecs=opus' 
          : 'audio/webm',
      });

      // Update state
      setState(prev => ({
        ...prev,
        isRecording: true,
        duration: 0,
      }));
      
      setRecording(true);

      // Start duration tracking
      durationIntervalRef.current = setInterval(() => {
        setState(prev => ({
          ...prev,
          duration: prev.duration + 1,
        }));
      }, 1000);

      // Start AudioWorklet processing
      if (workletNodeRef.current && audioContextRef.current) {
        workletNodeRef.current.port.postMessage({
          type: 'start',
          data: { 
            sampleRate: audioContextRef.current.sampleRate, // Use actual context rate (48000)
            targetSampleRate: sampleRate, // Target rate for transcription (16000)
            bufferSize 
          }
        });
      }

      console.log('Recording started successfully');
      return true;

    } catch (error) {
      console.error('Error starting recording:', error);
      
      let errorMessage = 'Failed to start recording';
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone access denied. Please allow microphone access and try again.';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found. Please connect a microphone and try again.';
        } else {
          errorMessage = error.message;
        }
      }

      addError({
        code: 'RECORDING_START_ERROR',
        message: errorMessage,
        timestamp: new Date().toISOString(),
      });

      return false;
    }
  }, [state.deviceId, sampleRate, bufferSize, initializeAudioContext, setRecording, addError]);

  // Stop recording
  const stopRecording = useCallback(() => {
    try {
      // Clear duration interval
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }

      // Stop media recorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }

      // Stop AudioWorklet processing
      if (workletNodeRef.current) {
        workletNodeRef.current.port.postMessage({ type: 'stop' });
        workletNodeRef.current.disconnect();
        workletNodeRef.current = null;
      }
      
      if (analyserRef.current) {
        analyserRef.current.disconnect();
        analyserRef.current = null;
      }
      
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }

      // Stop media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      // Update state
      setState(prev => ({
        ...prev,
        isRecording: false,
        isPaused: false,
        audioLevel: 0,
      }));
      
      setRecording(false);
      setAudioLevel(0);

      console.log('Recording stopped successfully');

    } catch (error) {
      console.error('Error stopping recording:', error);
      addError({
        code: 'RECORDING_STOP_ERROR',
        message: 'Error occurred while stopping recording',
        timestamp: new Date().toISOString(),
      });
    }
  }, [setRecording, setAudioLevel, addError]);

  // Pause/resume recording
  const togglePause = useCallback(() => {
    setState(prev => ({ ...prev, isPaused: !prev.isPaused }));
  }, []);

  // Change audio device
  const changeAudioDevice = useCallback(async (deviceId: string): Promise<boolean> => {
    if (state.isRecording) {
      stopRecording();
    }
    
    setState(prev => ({ ...prev, deviceId }));
    return true;
  }, [state.isRecording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (state.isRecording) {
        stopRecording();
      }
    };
  }, [state.isRecording, stopRecording]);

  return {
    ...state,
    startRecording,
    stopRecording,
    togglePause,
    changeAudioDevice,
    getAudioDevices,
  };
};