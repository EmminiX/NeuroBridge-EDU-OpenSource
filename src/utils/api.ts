/**
 * API Client for NeuroBridge EDU Backend
 * 
 * Provides typed functions for core backend API endpoints with proper
 * error handling and response parsing.
 */

import type { 
  ApiResponse, 
  Summary, 
  SummarizeRequest
} from '@/types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: {
            code: `HTTP_${response.status}`,
            message: data.message || `HTTP ${response.status}: ${response.statusText}`,
            details: data.details,
            timestamp: new Date().toISOString(),
          },
        };
      }

      // Handle our API response format which wraps data in response.data
      const responseData = data.success ? data.data : data;
      
      return {
        success: true,
        data: responseData,
      };
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: error instanceof Error ? error.message : 'Network error occurred',
          timestamp: new Date().toISOString(),
        },
      };
    }
  }

  // AI Summarization
  async generateSummary(request: SummarizeRequest): Promise<ApiResponse<Summary>> {
    return this.request<Summary>('/api/summaries/generate', {
      method: 'POST',
      body: JSON.stringify({
        transcript: request.transcriptionText,
        options: request.options
      }),
    });
  }

  // WebSocket URL
  getWebSocketUrl(): string {
    const wsProtocol = this.baseUrl.startsWith('https') ? 'wss' : 'ws';
    const baseWsUrl = this.baseUrl.replace(/^https?/, wsProtocol);
    return `${baseWsUrl}/ws`;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Utility functions
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};