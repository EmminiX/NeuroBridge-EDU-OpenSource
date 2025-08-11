/**
 * Application State Store using Zustand
 * 
 * Centralized state management for all application features including
 * recording, transcription, summaries, API key management, and UI state.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
// @ts-ignore: ApiKeyValidationStatus is used in Record<string, ApiKeyValidationStatus>
import type { 
  AppState, 
  ApiKey,
  ApiKeyCreateRequest,
  ApiKeyValidationStatus,
  TranscriptionConfigRequest,
  AppError
} from '@/types';

export const useAppStore = create<AppState>()(
  devtools(
    immer((set, get) => ({
      // Recording & Transcription State
      isRecording: false,
      recordingDuration: 0,
      audioLevel: 0,
      transcriptionText: '',
      isTranscribing: false,
      transcriptionSession: null,
      transcriptionSessionReady: false,
      
      // HTTP + SSE Connection
      isConnected: false,
      sessionId: null,
      
      // Summary Management
      summaryContent: '',
      isGeneratingSummary: false,
      currentSummary: null,
      
      // API Key Management
      apiKeys: [],
      validationStatuses: {} as Record<string, ApiKeyValidationStatus>,
      
      // Transcription Configuration
      transcriptionConfig: null,
      isLoadingTranscriptionConfig: false,
      
      // UI State
      activeTab: 'record',
      sidebarOpen: false,
      errors: [],

      // Actions
      setRecording: (recording: boolean) => {
        set((state) => {
          state.isRecording = recording;
          if (recording) {
            state.transcriptionText = '';
            state.transcriptionSession = {
              id: crypto.randomUUID(),
              text: '',
              isActive: true,
              startTime: new Date().toISOString(),
              duration: 0,
              audioLevel: 0,
            };
          } else if (state.transcriptionSession) {
            state.transcriptionSession.isActive = false;
            state.transcriptionSession.endTime = new Date().toISOString();
          }
        });
      },

      updateTranscription: (text: string) => {
        console.log('🔄 Store updateTranscription called:', {
          newTextLength: text.length,
          newTextPreview: text.substring(0, 100),
          currentTextLength: get().transcriptionText.length
        });
        
        set((state) => {
          state.transcriptionText = text;
          if (state.transcriptionSession) {
            state.transcriptionSession.text = text;
          }
          
          console.log('📊 Store state updated - transcriptionText length:', state.transcriptionText.length);
        });
      },

      setAudioLevel: (level: number) => {
        set((state) => {
          state.audioLevel = level;
          if (state.transcriptionSession) {
            state.transcriptionSession.audioLevel = level;
          }
        });
      },

      setConnection: (connected: boolean) => {
        set((state) => {
          state.isConnected = connected;
          // Reset session ready state when disconnected
          if (!connected) {
            state.transcriptionSessionReady = false;
            state.sessionId = null;
          }
        });
      },

      setSessionId: (sessionId: string | null) => {
        set((state) => {
          console.log('🆔 Setting session ID:', sessionId);
          state.sessionId = sessionId;
        });
      },

      setTranscriptionSessionReady: (ready: boolean) => {
        set((state) => {
          console.log('🎯 Setting transcription session ready:', ready);
          console.log('📊 Current state before update:', {
            isConnected: state.isConnected,
            sessionId: state.sessionId,
            transcriptionSessionReady: state.transcriptionSessionReady,
            isRecording: state.isRecording
          });
          state.transcriptionSessionReady = ready;
          console.log('📊 State updated - transcriptionSessionReady:', state.transcriptionSessionReady);
        });
      },

      generateSummary: async () => {
        const { transcriptionText, addError } = get();
        
        if (!transcriptionText.trim()) {
          addError({
            code: 'NO_TRANSCRIPTION',
            message: 'No transcription text available to summarize',
            timestamp: new Date().toISOString(),
          });
          return;
        }

        set((state) => {
          state.isGeneratingSummary = true;
          state.summaryContent = ''; // Clear previous summary
        });

        try {
          // Use regular generate endpoint without database saving
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          
          const response = await fetch(`${API_BASE_URL}/api/summaries/generate`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              transcript: transcriptionText,
              title: `Summary - ${new Date().toLocaleDateString()}`,
              subject: 'general education',
              saveToDatabase: false,
              options: {
                length: 'detailed',
                focus: ['key_points', 'action_items'],
              },
            }),
          });

          if (!response.ok) {
            throw new Error(`Failed to generate summary: ${response.status}`);
          }

          const data = await response.json();
          
          if (data.success) {
            set((state) => {
              state.summaryContent = data.data.content;
              state.currentSummary = {
                id: crypto.randomUUID(), // Generate client-side ID for temporary use
                title: data.data.title,
                content: data.data.content,
                raw_transcript: state.transcriptionText,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                metadata: {
                  aiGenerated: true,
                  subject: 'general education'
                }
              };
              state.isGeneratingSummary = false;
            });
          } else {
            throw new Error(data.message || 'Failed to generate summary');
          }

        } catch (error) {
          set((state) => {
            state.isGeneratingSummary = false;
          });
          
          addError({
            code: 'SUMMARY_GENERATION_FAILED',
            message: error instanceof Error ? error.message : 'Failed to generate summary',
            timestamp: new Date().toISOString(),
          });
        }
      },

      // API Key Management Functions
      addApiKey: async (keyData: ApiKeyCreateRequest) => {
        const { addError } = get();
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/api-keys/store`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(keyData),
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            // Reload API keys to get the updated list
            await get().loadApiKeys();
          } else {
            throw new Error(data.message || 'Failed to add API key');
          }
        } catch (error) {
          addError({
            code: 'API_KEY_ADD_FAILED',
            message: error instanceof Error ? error.message : 'Failed to add API key',
            timestamp: new Date().toISOString(),
          });
        }
      },

      validateApiKey: async (keyId: string) => {
        const { addError } = get();
        
        // Set validating status
        set((state) => {
          state.validationStatuses[keyId] = {
            keyId,
            status: 'validating',
            timestamp: new Date().toISOString(),
          };
        });
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/api-keys/validate/${keyId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            set((state) => {
              state.validationStatuses[keyId] = {
                keyId,
                status: data.data.valid ? 'valid' : 'invalid',
                message: data.data.message,
                timestamp: new Date().toISOString(),
              };
            });
            
            // Update the key status in the list
            await get().loadApiKeys();
          } else {
            throw new Error(data.message || 'Failed to validate API key');
          }
        } catch (error) {
          set((state) => {
            state.validationStatuses[keyId] = {
              keyId,
              status: 'error',
              message: error instanceof Error ? error.message : 'Validation failed',
              timestamp: new Date().toISOString(),
            };
          });
          
          addError({
            code: 'API_KEY_VALIDATION_FAILED',
            message: error instanceof Error ? error.message : 'Failed to validate API key',
            timestamp: new Date().toISOString(),
          });
        }
      },

      deleteApiKey: async (keyId: string) => {
        const { addError } = get();
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/api-keys/delete/${keyId}`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            set((state) => {
              state.apiKeys = state.apiKeys.filter((key: ApiKey) => key.id !== keyId);
              delete state.validationStatuses[keyId];
            });
          } else {
            throw new Error(data.message || 'Failed to delete API key');
          }
        } catch (error) {
          addError({
            code: 'API_KEY_DELETE_FAILED',
            message: error instanceof Error ? error.message : 'Failed to delete API key',
            timestamp: new Date().toISOString(),
          });
        }
      },

      loadApiKeys: async () => {
        const { addError } = get();
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/api-keys/list`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            set((state) => {
              state.apiKeys = data.data.keys.map((key: any) => ({
                id: key.id,
                provider: key.provider,
                label: key.label,
                created_at: key.created_at,
                last_used_at: key.last_used_at,
                status: key.status,
                last_four_chars: key.last_four_chars || 'N/A',
              }));
            });
          } else {
            throw new Error(data.message || 'Failed to load API keys');
          }
        } catch (error) {
          addError({
            code: 'API_KEYS_LOAD_FAILED',
            message: error instanceof Error ? error.message : 'Failed to load API keys',
            timestamp: new Date().toISOString(),
          });
        }
      },

      // Transcription Configuration Functions
      loadTranscriptionConfig: async () => {
        const { addError } = get();
        
        set((state) => {
          state.isLoadingTranscriptionConfig = true;
        });
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/transcription/config`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            set((state) => {
              state.transcriptionConfig = {
                method: data.current_method,
                local_model_size: data.local_model_size,
                local_model_loaded: data.local_model_loaded,
                performance_stats: data.performance_stats,
              };
              state.isLoadingTranscriptionConfig = false;
            });
          } else {
            throw new Error(data.message || 'Failed to load transcription configuration');
          }
        } catch (error) {
          set((state) => {
            state.isLoadingTranscriptionConfig = false;
          });
          
          addError({
            code: 'TRANSCRIPTION_CONFIG_LOAD_FAILED',
            message: error instanceof Error ? error.message : 'Failed to load transcription configuration',
            timestamp: new Date().toISOString(),
          });
        }
      },

      updateTranscriptionConfig: async (config: TranscriptionConfigRequest) => {
        const { addError } = get();
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/transcription/config`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(config),
          });

          const data = await response.json();
          
          if (response.ok && data.success) {
            // Reload configuration to get updated state
            await get().loadTranscriptionConfig();
          } else {
            throw new Error(data.message || 'Failed to update transcription configuration');
          }
        } catch (error) {
          addError({
            code: 'TRANSCRIPTION_CONFIG_UPDATE_FAILED',
            message: error instanceof Error ? error.message : 'Failed to update transcription configuration',
            timestamp: new Date().toISOString(),
          });
        }
      },

      testLocalTranscription: async () => {
        const { addError } = get();
        
        try {
          const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
          const response = await fetch(`${API_BASE_URL}/api/transcription/test-local`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const data = await response.json();
          
          if (response.ok) {
            // Test completed - show results in a way that makes sense for the UI
            // You might want to add a notification or toast here
            console.log('Local transcription test result:', data);
          } else {
            throw new Error(data.message || 'Local transcription test failed');
          }
        } catch (error) {
          addError({
            code: 'LOCAL_TRANSCRIPTION_TEST_FAILED',
            message: error instanceof Error ? error.message : 'Failed to test local transcription',
            timestamp: new Date().toISOString(),
          });
        }
      },

      setActiveTab: (tab: 'record' | 'settings') => {
        set((state) => {
          state.activeTab = tab;
        });
      },

      toggleSidebar: () => {
        set((state) => {
          state.sidebarOpen = !state.sidebarOpen;
        });
      },

      addError: (error: AppError) => {
        set((state) => {
          // Add unique ID to error to prevent React key conflicts
          const errorWithId = {
            ...error,
            id: `${error.code}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
          };
          state.errors.push(errorWithId);
        });
      },

      clearError: (errorId: string) => {
        set((state) => {
          state.errors = state.errors.filter((e: AppError) => e.id !== errorId);
        });
      },

      clearAllErrors: () => {
        set((state) => {
          state.errors = [];
        });
      },

      clearErrors: () => {
        set((state) => {
          state.errors = [];
        });
      },
    })),
    {
      name: 'neurobridge-store',
    }
  )
);