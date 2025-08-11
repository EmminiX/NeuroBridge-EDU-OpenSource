/**
 * Core Types for NeuroBridge EDU Application
 * 
 * Defines TypeScript interfaces for all data structures used throughout
 * the application for type safety and development assistance.
 */

export interface ApiKey {
  id: string;
  provider: string;
  label: string;
  created_at: string;
  last_used_at?: string;
  status: 'active' | 'invalid' | 'expired';
  last_four_chars: string;
}

export interface Summary {
  id: string;
  title: string;
  content: string;
  raw_transcript: string; // Database field name
  transcriptionText?: string; // Alias for raw_transcript
  created_at: string; // Database field name
  updated_at: string; // Database field name
  createdAt?: string; // Alias for created_at
  updatedAt?: string; // Alias for updated_at
  metadata: {
    tags?: string[];
    sections?: any[];
    subject?: string;
    aiGenerated?: boolean;
    [key: string]: any;
  };
  // Legacy aliases for backward compatibility
  tags?: string[];
}

export interface TranscriptionSession {
  id: string;
  text: string;
  isActive: boolean;
  startTime: string;
  endTime?: string;
  duration: number;
  audioLevel: number;
}

export interface ApiKeyValidationStatus {
  keyId: string;
  status: 'validating' | 'valid' | 'invalid' | 'error';
  message?: string;
  timestamp?: string;
}

export interface SessionEndedData {
  sessionId: string;
  message: string;
  finalTranscription?: {
    transcript: string;
    confidence?: number;
    language?: string;
  };
  fullTranscript: string; // Complete accumulated transcript from entire session
  sessionDuration: number | null;
  endedAt: string;
}

export interface SSEMessage {
  type: 'transcription_update' | 'session_started' | 'session_ended' | 'heartbeat' | 'connection' | 'error';
  data: any;
  timestamp: string;
}

export interface AudioRecorderState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioLevel: number;
  deviceId?: string;
}

export interface ExportOptions {
  format: 'pdf' | 'markdown' | 'text';
  includeTranscription: boolean;
  includeTimestamp: boolean;
  includeSummary: boolean;
}

export interface AppError {
  id?: string;
  code: string;
  message: string;
  details?: string;
  timestamp: string;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: AppError;
}

export interface SummarizeRequest {
  transcriptionText: string;
  options?: {
    length: 'brief' | 'detailed' | 'comprehensive';
    focus: string[];
  };
}

export interface ApiKeyCreateRequest {
  provider: string;
  api_key: string;
  label?: string;
}

export interface ApiKeyResponse {
  id: string;
  provider: string;
  label: string;
  created_at: string;
  last_used_at?: string;
  status: string;
  last_four_chars: string;
}

export interface ApiKeyValidationResponse {
  valid: boolean;
  message: string;
  tested_at: string;
  provider: string;
}

export interface TranscriptionConfig {
  method: 'local_only' | 'api_only' | 'local_first' | 'auto';
  local_model_size: 'tiny' | 'base' | 'small' | 'medium' | 'large-v2' | 'large-v3';
  local_model_loaded: boolean;
  performance_stats: {
    local_success_rate: number;
    api_success_rate: number;
    local_avg_time: number;
    api_avg_time: number;
    total_requests: number;
  };
}

export interface TranscriptionConfigRequest {
  method: string;
  local_model_size: string;
}

export interface ModelInfo {
  parameters: string;
  relative_speed: string;
  vram_required: string;
  accuracy: string;
  recommended_for: string;
}

// Store State Interfaces
export interface AppState {
  // Recording & Transcription
  isRecording: boolean;
  recordingDuration: number;
  audioLevel: number;
  transcriptionText: string;
  isTranscribing: boolean;
  transcriptionSession: TranscriptionSession | null;
  transcriptionSessionReady: boolean;
  
  // HTTP + SSE Connection
  isConnected: boolean;
  sessionId: string | null;
  
  // Summary Management
  summaryContent: string;
  isGeneratingSummary: boolean;
  currentSummary: Summary | null;
  
  // API Key Management
  apiKeys: ApiKey[];
  validationStatuses: Record<string, ApiKeyValidationStatus>;
  
  // Transcription Configuration
  transcriptionConfig: TranscriptionConfig | null;
  isLoadingTranscriptionConfig: boolean;
  
  // UI State
  activeTab: 'record' | 'settings';
  sidebarOpen: boolean;
  errors: AppError[];
  
  // Actions
  setRecording: (recording: boolean) => void;
  updateTranscription: (text: string) => void;
  setAudioLevel: (level: number) => void;
  setConnection: (connected: boolean) => void;
  setSessionId: (sessionId: string | null) => void;
  setTranscriptionSessionReady: (ready: boolean) => void;
  generateSummary: () => Promise<void>;
  addApiKey: (keyData: ApiKeyCreateRequest) => Promise<void>;
  validateApiKey: (keyId: string) => Promise<void>;
  deleteApiKey: (keyId: string) => Promise<void>;
  loadApiKeys: () => Promise<void>;
  loadTranscriptionConfig: () => Promise<void>;
  updateTranscriptionConfig: (config: TranscriptionConfigRequest) => Promise<void>;
  testLocalTranscription: () => Promise<void>;
  setActiveTab: (tab: 'record' | 'settings') => void;
  toggleSidebar: () => void;
  addError: (error: AppError) => void;
  clearError: (errorId: string) => void;
  clearAllErrors: () => void;
  clearErrors: () => void;
}