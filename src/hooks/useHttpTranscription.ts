/**
 * HTTP + SSE Transcription Hook (Production-Ready)
 * 
 * Replaces WebSocket with HTTP chunk uploads + Server-Sent Events
 * Based on research findings from meeting-minutes analysis and industry best practices
 * Used by Rev.ai, Otter.ai, and other production transcription services
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useAppStore } from '@/stores/appStore';

// Get API base URL from environment
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';

interface UseHttpTranscriptionOptions {
  chunkDuration?: number; // Duration in ms for each chunk (default: 2000ms)
  overlapDuration?: number; // Overlap duration in ms (default: 200ms)
}

interface ChunkUploadResponse {
  sessionId: string;
  buffered: boolean;
  processed: boolean;
  sequence: number;
  bufferDurationMs: number;
  status: string;
}

// HTTP + SSE Transcription Manager (Production Architecture)
class HttpTranscriptionManager {
  private static instance: HttpTranscriptionManager | null = null;
  private eventSource: EventSource | null = null;
  private sessionId: string | null = null;
  private listeners: Set<(data: any) => void> = new Set();
  private connectionCallbacks: Set<(connected: boolean) => void> = new Set();
  private isConnected = false;
  private chunkSequence = 0;
  private chunkDuration = 2000; // 2 seconds (meeting-minutes proven optimal)
  private audioBuffer: Float32Array = new Float32Array(0);
  private sampleRate = 16000;
  private overlapBuffer: Float32Array = new Float32Array(0);
  private overlapDuration = 200; // 200ms overlap for context preservation
  private accumulatedTranscript = ''; // Store all transcribed text

  static getInstance(): HttpTranscriptionManager {
    if (!HttpTranscriptionManager.instance) {
      HttpTranscriptionManager.instance = new HttpTranscriptionManager();
    }
    return HttpTranscriptionManager.instance;
  }

  async startSession(sessionId: string, options: UseHttpTranscriptionOptions = {}) {
    this.sessionId = sessionId;
    this.chunkSequence = 0;
    this.chunkDuration = options.chunkDuration || 2000;
    this.overlapDuration = options.overlapDuration || 200;
    this.audioBuffer = new Float32Array(0);
    this.overlapBuffer = new Float32Array(0);
    this.accumulatedTranscript = ''; // Reset accumulated transcript

    console.log('🚀 Starting HTTP + SSE transcription session:', {
      sessionId: sessionId.substring(0, 8),
      chunkDuration: this.chunkDuration,
      overlapDuration: this.overlapDuration
    });

    try {
      // Start transcription session via HTTP
      const response = await fetch(`${API_BASE_URL}/api/transcribe/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          language: 'en'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to start session: ${response.statusText}`);
      }

      // Connect to SSE stream for real-time results
      await this.connectSSE();
      
      console.log('✅ HTTP + SSE session started successfully');
      this.notifyConnectionChange(true);

    } catch (error) {
      console.error('❌ Failed to start HTTP + SSE session:', error);
      throw error;
    }
  }

  private async connectSSE() {
    if (!this.sessionId) {
      throw new Error('No session ID available for SSE connection');
    }

    const sseUrl = `${API_BASE_URL}/api/transcribe/stream/${this.sessionId}`;
    console.log('📡 Connecting to SSE stream:', sseUrl);

    this.eventSource = new EventSource(sseUrl);

    this.eventSource.onopen = () => {
      console.log('✅ SSE connection established');
      this.isConnected = true;
      this.notifyConnectionChange(true);
    };
    
    // Add listeners for specific event types from backend
    this.eventSource.addEventListener('connected', (event) => {
      console.log('🔗 SSE connected event:', event.data);
    });
    
    this.eventSource.addEventListener('keepalive', (event) => {
      console.log('💚 SSE keepalive:', event.data);
    });
    
    this.eventSource.addEventListener('error', (event) => {
      console.error('❌ SSE error event:', event);
    });

    // Add listener for transcription events from backend
    this.eventSource.addEventListener('transcription', (event) => {
      try {
        console.log('🎯 TRANSCRIPTION EVENT received:', event.data);
        const data = JSON.parse(event.data);
        console.log('📝 Transcription data:', {
          text: data.text,
          confidence: data.confidence,
          chunkIndex: data.chunkIndex,
          totalDuration: data.totalDuration
        });
        
        // Accumulate the transcript
        if (data.text && data.text.trim()) {
          // Add space between chunks if needed
          if (this.accumulatedTranscript && !this.accumulatedTranscript.endsWith(' ')) {
            this.accumulatedTranscript += ' ';
          }
          this.accumulatedTranscript += data.text;
          
          console.log('📑 Accumulated transcript:', {
            newText: data.text,
            totalLength: this.accumulatedTranscript.length,
            preview: this.accumulatedTranscript.substring(0, 100) + '...'
          });
        }
        
        // Notify listeners with transcription
        this.listeners.forEach(listener => listener({
          type: 'transcription_update',
          data: {
            transcript: data.text,
            accumulatedTranscript: this.accumulatedTranscript,
            confidence: data.confidence,
            chunkIndex: data.chunkIndex
          }
        }));
      } catch (error) {
        console.error('Error processing transcription event:', error);
      }
    });

    this.eventSource.onmessage = (event) => {
      try {
        console.log('📨 RAW SSE message received:', event.data);
        const data = JSON.parse(event.data);
        console.log('📨 SSE message parsed:', data.type, data);
        
        // Handle different message types
        switch (data.type) {
          case 'connection':
            console.log('🤝 SSE connection confirmed:', data.message);
            break;
            
          case 'heartbeat':
            console.log('💓 SSE heartbeat received:', {
              sessionId: data.sessionId?.substring(0, 8),
              uptime: data.uptime,
              message: data.message
            });
            break;
            
          case 'transcription_update':
            console.log('📝 Transcription update via SSE:', {
              hasTranscript: !!data.data?.transcript,
              hasAccumulated: !!data.data?.accumulatedTranscript,
              transcriptLength: data.data?.transcript?.length || 0,
              accumulatedLength: data.data?.accumulatedTranscript?.length || 0
            });
            
            // Notify listeners with transcription data
            this.listeners.forEach(listener => listener({
              type: 'transcription_update',
              data: {
                transcript: data.data?.transcript,
                accumulatedTranscript: data.data?.accumulatedTranscript,
                confidence: data.data?.confidence,
                language: data.data?.language,
                chunks: data.data?.chunks
              }
            }));
            break;
            
          case 'session_ended':
            console.log('🔚 Session ended via SSE:', {
              sessionId: data.sessionId?.substring(0, 8),
              totalChunks: data.data?.totalChunks,
              duration: data.data?.duration,
              status: data.data?.status
            });
            
            // Notify listeners that session has ended
            this.listeners.forEach(listener => listener({
              type: 'session_ended',
              data: data.data
            }));
            break;
            
          default:
            console.log('❓ Unknown SSE message type:', data.type);
        }

      } catch (error) {
        console.error('❌ Error parsing SSE message:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('❌ SSE connection error:', error);
      console.error('❌ SSE readyState:', this.eventSource?.readyState);
      console.error('❌ SSE url:', this.eventSource?.url);
      this.isConnected = false;
      this.notifyConnectionChange(false);
    };
  }

  async addAudioData(audioData: Float32Array) {
    if (!this.sessionId) {
      console.warn('⚠️ No active session for audio data');
      return;
    }

    // Combine with existing buffer
    const combined = new Float32Array(this.audioBuffer.length + audioData.length);
    combined.set(this.audioBuffer);
    combined.set(audioData, this.audioBuffer.length);
    this.audioBuffer = combined;

    // Calculate duration in ms
    const durationMs = (this.audioBuffer.length / this.sampleRate) * 1000;

    console.log('🎵 Audio buffer updated:', {
      sessionId: this.sessionId ? this.sessionId.substring(0, 8) : 'no-session',
      newSamples: audioData.length,
      totalSamples: this.audioBuffer.length,
      durationMs: durationMs.toFixed(0)
    });

    // Check if we have enough audio for a chunk (2 seconds)
    if (durationMs >= this.chunkDuration) {
      await this.processChunk();
    }
  }

  private async processChunk() {
    if (!this.sessionId || this.audioBuffer.length === 0) {
      return;
    }

    // Calculate overlap in samples
    const overlapSamples = Math.floor((this.overlapDuration / 1000) * this.sampleRate);
    const chunkSamples = Math.floor((this.chunkDuration / 1000) * this.sampleRate);
    
    // Extract chunk to process (with any previous overlap)
    const totalChunkSamples = this.overlapBuffer.length + Math.min(chunkSamples, this.audioBuffer.length);
    const chunkToProcess = new Float32Array(totalChunkSamples);
    
    // Combine overlap buffer with new audio
    chunkToProcess.set(this.overlapBuffer);
    chunkToProcess.set(this.audioBuffer.slice(0, totalChunkSamples - this.overlapBuffer.length), this.overlapBuffer.length);
    
    // Save overlap for next chunk (last 200ms)
    const keepSamples = Math.min(overlapSamples, this.audioBuffer.length);
    this.overlapBuffer = this.audioBuffer.slice(-keepSamples);
    
    // Remove processed audio from buffer (keeping overlap)
    const remainingSamples = Math.max(0, this.audioBuffer.length - (totalChunkSamples - this.overlapBuffer.length));
    this.audioBuffer = this.audioBuffer.slice(-remainingSamples);

    console.log('🎯 Processing chunk with overlap strategy:', {
      sessionId: this.sessionId ? this.sessionId.substring(0, 8) : 'no-session',
      chunkSamples: chunkToProcess.length,
      overlapSamples: this.overlapBuffer.length,
      remainingBufferSamples: this.audioBuffer.length,
      sequence: this.chunkSequence
    });

    try {
      // Convert to PCM 16-bit for backend
      const pcmData = this.convertToPCM16(chunkToProcess);
      
      // Audio quality check before sending to backend
      let maxLevel = 0;
      let rmsSum = 0;
      for (let i = 0; i < chunkToProcess.length; i++) {
        const sample = Math.abs(chunkToProcess[i]);
        maxLevel = Math.max(maxLevel, sample);
        rmsSum += chunkToProcess[i] * chunkToProcess[i];
      }
      const rms = Math.sqrt(rmsSum / chunkToProcess.length);
      const hasSignificantAudio = maxLevel > 0.01 && rms > 0.005;
      
      console.log('🔊 Audio quality check before upload:', {
        sessionId: this.sessionId ? this.sessionId.substring(0, 8) : 'no-session',
        maxLevel: maxLevel.toFixed(4),
        rms: rms.toFixed(4),
        hasSignificantAudio,
        samples: chunkToProcess.length,
        pcmBytes: pcmData.byteLength
      });
      
      // TEMPORARILY DISABLED: Always send audio to backend for debugging  
      console.log('🎯 SILENCE DETECTION DISABLED - sending all audio for debugging');
      // if (!hasSignificantAudio) {
      //   console.warn('⚠️ Skipping silent audio chunk - insufficient signal for transcription');
      //   return;
      // }
      
      // Upload chunk via HTTP - FIXED: Send raw ArrayBuffer for proper binary transfer
      const response = await fetch(`${API_BASE_URL}/api/transcribe/chunk`, {
        method: 'POST',
        headers: {
          'x-session-id': this.sessionId,  // FIXED: Backend expects x-session-id not Session-ID
          'Chunk-Size': pcmData.byteLength.toString(),
          'Content-Type': 'application/octet-stream'
        },
        body: pcmData  // FIXED: Send raw ArrayBuffer directly (not Uint8Array wrapper)
      });

      if (!response.ok) {
        throw new Error(`Chunk upload failed: ${response.statusText}`);
      }

      const result: ChunkUploadResponse = await response.json();
      console.log('✅ Chunk uploaded successfully:', {
        sequence: result.sequence,
        processed: result.processed,
        status: result.status,
        bufferDuration: result.bufferDurationMs
      });

      this.chunkSequence++;

    } catch (error) {
      console.error('❌ Failed to upload audio chunk:', error);
    }
  }

  private convertToPCM16(audioData: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(audioData.length * 2);
    const view = new DataView(buffer);
    
    // Debug: Check audio levels before conversion
    let maxLevel = 0;
    let rmsSum = 0;
    let nonZeroSamples = 0;
    let maxPcmValue = 0;
    let minPcmValue = 0;
    const pcmSamples = [];
    
    for (let i = 0; i < audioData.length; i++) {
      const sample = Math.max(-1, Math.min(1, audioData[i]));
      const absValue = Math.abs(sample);
      
      if (absValue > 0.001) { // Count non-trivial samples
        nonZeroSamples++;
      }
      
      maxLevel = Math.max(maxLevel, absValue);
      rmsSum += sample * sample;
      
      // Convert to 16-bit signed integer (-32768 to 32767)
      const pcmValue = Math.round(sample * 32767);
      view.setInt16(i * 2, pcmValue, true); // Little endian
      
      // Track PCM values for debugging
      if (i < 10) pcmSamples.push(pcmValue);
      maxPcmValue = Math.max(maxPcmValue, Math.abs(pcmValue));
      minPcmValue = Math.min(minPcmValue, pcmValue);
    }
    
    const rms = Math.sqrt(rmsSum / audioData.length);
    const silencePercentage = ((audioData.length - nonZeroSamples) / audioData.length * 100).toFixed(1);
    
    // CRITICAL: Check if audio has sufficient signal for transcription
    const hasSignificantAudio = maxLevel > 0.01 && rms > 0.005 && nonZeroSamples > (audioData.length * 0.1);
    
    console.log('🎧 Audio conversion analysis:', {
      sessionId: this.sessionId?.substring(0, 8),
      samples: audioData.length,
      maxLevel: maxLevel.toFixed(4),
      rms: rms.toFixed(4),
      hasSignificantAudio,
      nonZeroSamples,
      silencePercentage: silencePercentage + '%',
      avgPcmValue: Math.round(rms * 32767),
      maxPcmValue,
      minPcmValue,
      firstFewFloat32: Array.from(audioData.slice(0, 10)).map(x => x.toFixed(6)),
      firstFewPCM16: pcmSamples,
      bufferSize: buffer.byteLength,
      expectedRange: '[-32768, 32767]'
    });
    
    return buffer;
  }

  async endSession() {
    if (!this.sessionId) {
      console.warn('⚠️ No active session to end');
      return;
    }

    console.log('🔄 Ending HTTP + SSE session:', this.sessionId ? this.sessionId.substring(0, 8) : 'no-session');

    try {
      // Process any remaining audio
      if (this.audioBuffer.length > 0 || this.overlapBuffer.length > 0) {
        console.log('🔄 Processing final audio chunk');
        // Combine remaining audio with overlap
        const finalChunk = new Float32Array(this.audioBuffer.length + this.overlapBuffer.length);
        finalChunk.set(this.overlapBuffer);
        finalChunk.set(this.audioBuffer, this.overlapBuffer.length);
        
        if (finalChunk.length > 0) {
          const pcmData = this.convertToPCM16(finalChunk);
          await fetch(`${API_BASE_URL}/api/transcribe/chunk`, {
            method: 'POST',
            headers: {
              'x-session-id': this.sessionId,  // Fixed: Use lowercase x-session-id
              'Chunk-Size': pcmData.byteLength.toString(),
              'Content-Type': 'application/octet-stream'
            },
            body: pcmData  // Raw ArrayBuffer for proper binary transfer
          });
        }
      }

      // End session via HTTP
      const response = await fetch(`${API_BASE_URL}/api/transcribe/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: this.sessionId
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Session ended successfully:', result);
      }

    } catch (error) {
      console.error('❌ Failed to end session cleanly:', error);
    } finally {
      this.cleanup();
    }
  }

  private cleanup() {
    console.log('🧹 Cleaning up HTTP + SSE session');
    
    // Log final accumulated transcript
    if (this.accumulatedTranscript) {
      console.log('📜 Final accumulated transcript:', {
        length: this.accumulatedTranscript.length,
        wordCount: this.accumulatedTranscript.split(' ').length,
        text: this.accumulatedTranscript
      });
    }
    
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    
    this.sessionId = null;
    this.chunkSequence = 0;
    this.audioBuffer = new Float32Array(0);
    this.overlapBuffer = new Float32Array(0);
    this.accumulatedTranscript = '';
    
    // Reset session connection but keep overall connectivity if backend is reachable
    // This allows isConnectedToSession() to work properly for new sessions
    this.isConnected = false;
    
    console.log('🧹 Cleanup complete - session ended, ready for new sessions');
  }

  addMessageListener(listener: (data: any) => void) {
    this.listeners.add(listener);
  }

  removeMessageListener(listener: (data: any) => void) {
    this.listeners.delete(listener);
  }

  addConnectionListener(callback: (connected: boolean) => void) {
    this.connectionCallbacks.add(callback);
  }

  removeConnectionListener(callback: (connected: boolean) => void) {
    this.connectionCallbacks.delete(callback);
  }

  private notifyConnectionChange(connected: boolean) {
    this.isConnected = connected;
    this.connectionCallbacks.forEach(callback => callback(connected));
  }

  isConnectedToSession(): boolean {
    return this.isConnected && !!this.sessionId;
  }
}

export const useHttpTranscription = (options: UseHttpTranscriptionOptions = {}) => {
  const manager = useRef<HttpTranscriptionManager>(HttpTranscriptionManager.getInstance());
  const mountedRef = useRef(true);
  const [isConnected, setIsConnected] = useState(false);

  const {
    setConnection,
    setTranscriptionSessionReady,
    updateTranscription,
    addError,
    setRecording,
  } = useAppStore();

  // Store refs to avoid useCallback dependency issues
  const storeRef = useRef({
    setConnection,
    setTranscriptionSessionReady,
    updateTranscription,
    addError,
    setRecording,
  });

  // Update refs when store functions change
  useEffect(() => {
    storeRef.current = {
      setConnection,
      setTranscriptionSessionReady,
      updateTranscription,
      addError,
      setRecording,
    };
  }, [setConnection, setTranscriptionSessionReady, updateTranscription, addError, setRecording]);

  // Message handler for SSE events - memoized to prevent effect loops
  const handleMessage = useCallback((message: any) => {
    if (!mountedRef.current) return;

    switch (message.type) {
      case 'transcription_update':
        console.log('🔍 HTTP + SSE transcription update:', {
          hasAccumulated: !!message.data?.accumulatedTranscript,
          hasTranscript: !!message.data?.transcript,
          accumulatedLength: message.data?.accumulatedTranscript?.length || 0,
          transcriptLength: message.data?.transcript?.length || 0
        });
        
        // Use accumulated transcript for complete growing text
        if (message.data?.accumulatedTranscript) {
          console.log('📝 Using accumulated transcript:', message.data.accumulatedTranscript.length, 'chars');
          storeRef.current.updateTranscription(message.data.accumulatedTranscript);
        } else if (message.data?.transcript) {
          console.log('📝 Fallback to individual transcript:', message.data.transcript.length, 'chars');
          storeRef.current.updateTranscription(message.data.transcript);
        }
        break;
        
      case 'session_ended':
        console.log('🔚 Session ended via SSE:', message);
        // Keep connection state as true since SSE is still working
        // The cleanup will happen when endSession() is called
        break;

      case 'heartbeat':
        // Heartbeat messages are handled by the manager for logging
        // No action needed in the hook
        break;
        
      default:
        console.log('❓ Unknown message type:', message.type);
    }
  }, []); // Stable callback - no dependencies

  // Connection state handler - memoized to prevent effect loops
  const handleConnectionChange = useCallback((connected: boolean) => {
    if (!mountedRef.current) return;
    
    console.log('🔗 HTTP + SSE connection state changed:', connected);
    setIsConnected(connected); // Update local React state
    storeRef.current.setConnection(connected);
    storeRef.current.setTranscriptionSessionReady(connected);
  }, []); // Stable callback - no dependencies

  const startSession = useCallback(async (sessionId: string) => {
    try {
      await manager.current.startSession(sessionId, options);
      console.log('✅ HTTP + SSE session started successfully');
    } catch (error) {
      console.error('❌ Failed to start HTTP + SSE session:', error);
      storeRef.current.addError({
        code: `HTTP_SESSION_ERROR_${Date.now()}`,
        message: `Failed to start transcription session: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      });
    }
  }, [options]);

  const endSession = useCallback(async () => {
    try {
      await manager.current.endSession();
      
      // Reset session ready state
      storeRef.current.setTranscriptionSessionReady(false);
      
      // Reset recording state
      storeRef.current.setRecording(false);
      
      // Check if backend is still reachable after session ends
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          // Backend is still available - keep connection as true
          storeRef.current.setConnection(true);
          console.log('✅ HTTP + SSE session ended successfully, backend still available');
        } else {
          // Backend responded with error - set disconnected
          storeRef.current.setConnection(false);
          console.log('⚠️ Backend responded with error after session end');
        }
      } catch (healthError) {
        // Backend not reachable - set disconnected
        storeRef.current.setConnection(false);
        console.log('❌ Backend not reachable after session end');
      }
      
    } catch (error) {
      console.error('❌ Failed to end HTTP + SSE session:', error);
      
      // Session end failed - set connection to false
      storeRef.current.setConnection(false);
      storeRef.current.setTranscriptionSessionReady(false);
      storeRef.current.setRecording(false);
    }
  }, []);

  const sendAudioData = useCallback(async (audioData: Float32Array) => {
    if (manager.current.isConnectedToSession()) {
      await manager.current.addAudioData(audioData);
    } else {
      console.warn('⚠️ Cannot send audio data - session not active');
    }
  }, []);

  // Set up listeners - run only once on mount
  useEffect(() => {
    console.log('🔧 Setting up HTTP + SSE listeners');
    
    manager.current.addMessageListener(handleMessage);
    manager.current.addConnectionListener(handleConnectionChange);
    
    return () => {
      console.log('🧹 Cleaning up HTTP + SSE listeners');
      mountedRef.current = false;
      
      manager.current.removeMessageListener(handleMessage);
      manager.current.removeConnectionListener(handleConnectionChange);
    };
  }, []); // No dependencies - run only once

  // Track mount state and check backend connectivity
  useEffect(() => {
    mountedRef.current = true;
    
    // Check if backend is reachable on mount
    const checkBackendConnectivity = async () => {
      try {
        console.log('🔍 Checking backend connectivity...');
        const response = await fetch(`${API_BASE_URL}/api/transcribe/test`);
        if (response.ok) {
          console.log('✅ Backend is reachable - showing Connected status');
          setIsConnected(true);
          storeRef.current.setConnection(true);
          // Don't set transcriptionSessionReady here - only when session starts
        } else {
          console.log('❌ Backend responded with error:', response.status);
          setIsConnected(false);
        }
      } catch (error) {
        console.log('❌ Backend not reachable:', error instanceof Error ? error.message : 'Unknown error');
        setIsConnected(false);
      }
    };
    
    // Check connectivity on mount
    checkBackendConnectivity();
    
    return () => {
      mountedRef.current = false;
    };
  }, []); // Run only once on mount

  return {
    isConnected,
    startSession,
    endSession,
    sendAudioData,
  };
};