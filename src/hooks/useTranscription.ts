/**
 * Transcription Hook (HTTP + SSE Architecture)
 * 
 * High-level hook that combines HTTP + SSE connection and audio recording
 * for seamless real-time transcription functionality.
 * 
 * UPDATED: Now uses production-ready HTTP chunk upload + SSE streaming
 * instead of problematic WebSocket micro-chunking approach.
 */

import { useCallback, useEffect } from 'react';
import { useHttpTranscription } from './useHttpTranscription';
import { useAudioRecorder } from './useAudioRecorder';
import { useAppStore } from '@/stores/appStore';

interface UseTranscriptionOptions {
  sampleRate?: number;
  bufferSize?: number;
  chunkDuration?: number; // Duration in ms for each HTTP chunk (default: 2000ms)
  overlapDuration?: number; // Overlap duration in ms for context preservation (default: 200ms)
}

export const useTranscription = (options: UseTranscriptionOptions = {}) => {
  const {
    sampleRate = 16000,
    bufferSize = 4096,
    chunkDuration = 2000,
    overlapDuration = 200,
  } = options;

  const {
    isRecording,
    transcriptionText,
    addError,
  } = useAppStore();

  // Initialize HTTP + SSE transcription
  const {
    isConnected,
    startSession,
    endSession,
    sendAudioData,
  } = useHttpTranscription({
    chunkDuration,
    overlapDuration,
  });

  // Create audio data handler for HTTP + SSE architecture
  const handleAudioData = useCallback((audioFloat32: Float32Array) => {
    // Directly pass Float32Array to HTTP + SSE manager (no conversion needed)
    console.log('🎵 Audio data handler (HTTP + SSE):', {
      isConnected,
      samples: audioFloat32.length,
      firstFew: Array.from(audioFloat32.slice(0, 5)).map(x => x.toFixed(6))
    });
    
    if (isConnected) {
      console.log('✅ Sending audio data via HTTP + SSE');
      sendAudioData(audioFloat32);
    } else {
      console.warn('⚠️ Cannot send audio data - HTTP + SSE session not active');
    }
  }, [isConnected, sendAudioData]);

  // Initialize audio recorder
  const audioRecorder = useAudioRecorder(handleAudioData, {
    sampleRate,
    bufferSize,
  });

  // Start transcription session with HTTP + SSE architecture
  const startTranscription = useCallback(async (): Promise<boolean> => {
    try {
      console.log('🎯 Starting HTTP + SSE transcription session...');
      
      // Generate unique session ID
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
      console.log('🆔 Generated session ID:', sessionId.substring(0, 8));
      
      // Start HTTP + SSE session
      await startSession(sessionId);
      
      // Wait a moment for SSE connection to establish
      await new Promise(resolve => setTimeout(resolve, 500));
      
      if (!isConnected) {
        addError({
          code: 'HTTP_SSE_CONNECTION_FAILED',
          message: 'Failed to establish HTTP + SSE connection. Please try again.',
          timestamp: new Date().toISOString(),
        });
        return false;
      }

      // Start audio recording
      console.log('🎤 Starting audio recording...');
      const recordingStarted = await audioRecorder.startRecording();
      if (!recordingStarted) {
        addError({
          code: 'AUDIO_RECORDING_FAILED',
          message: 'Failed to start audio recording. Please check microphone permissions.',
          timestamp: new Date().toISOString(),
        });
        return false;
      }

      console.log('🎯 HTTP + SSE transcription session fully started and ready');
      return true;

    } catch (error) {
      console.error('❌ Error starting HTTP + SSE transcription:', error);
      addError({
        code: 'TRANSCRIPTION_START_ERROR',
        message: error instanceof Error ? error.message : 'Failed to start transcription',
        timestamp: new Date().toISOString(),
      });
      
      return false;
    }
  }, [startSession, isConnected, audioRecorder, addError]);

  // Stop transcription session
  const stopTranscription = useCallback(async () => {
    try {
      console.log('🛑 Stopping HTTP + SSE transcription session...');
      
      // Stop audio recording first
      audioRecorder.stopRecording();

      // End HTTP + SSE session
      await endSession();

      console.log('✅ HTTP + SSE transcription session stopped');

    } catch (error) {
      console.error('❌ Error stopping HTTP + SSE transcription:', error);
      addError({
        code: 'TRANSCRIPTION_STOP_ERROR',
        message: 'Error occurred while stopping transcription',
        timestamp: new Date().toISOString(),
      });
    }
  }, [audioRecorder, endSession, addError]);

  // Toggle transcription (start/stop)
  const toggleTranscription = useCallback(async () => {
    if (isRecording) {
      stopTranscription();
    } else {
      await startTranscription();
    }
  }, [isRecording, startTranscription, stopTranscription]);

  // Clear current transcription
  const clearTranscription = useCallback(() => {
    if (isRecording) {
      addError({
        code: 'CANNOT_CLEAR_WHILE_RECORDING',
        message: 'Cannot clear transcription while recording is active',
        timestamp: new Date().toISOString(),
      });
      return;
    }

    // Clear transcription in store
    useAppStore.getState().updateTranscription('');
  }, [isRecording, addError]);

  // Get recording status
  const getStatus = useCallback(() => {
    return {
      isRecording: audioRecorder.isRecording,
      isPaused: audioRecorder.isPaused,
      duration: audioRecorder.duration,
      audioLevel: audioRecorder.audioLevel,
      isConnected: isConnected,
      hasTranscription: transcriptionText.length > 0,
      canRecord: isConnected && !isRecording,
      canStop: isRecording,
    };
  }, [
    audioRecorder.isRecording,
    audioRecorder.isPaused,
    audioRecorder.duration,
    audioRecorder.audioLevel,
    isConnected,
    transcriptionText.length,
    isRecording,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Only cleanup if we're actually recording when component unmounts
      if (audioRecorder.isRecording) {
        audioRecorder.stopRecording();
        endSession(); // Clean up HTTP + SSE session
      }
    };
  }, []); // Empty dependency array to only run on mount/unmount

  return {
    // State
    isRecording: audioRecorder.isRecording,
    isPaused: audioRecorder.isPaused,
    duration: audioRecorder.duration,
    audioLevel: audioRecorder.audioLevel,
    isConnected: isConnected,
    transcriptionText,
    
    // Actions
    startTranscription,
    stopTranscription,
    toggleTranscription,
    clearTranscription,
    
    // Audio device management
    getAudioDevices: audioRecorder.getAudioDevices,
    changeAudioDevice: audioRecorder.changeAudioDevice,
    
    // Status
    getStatus,
  };
};