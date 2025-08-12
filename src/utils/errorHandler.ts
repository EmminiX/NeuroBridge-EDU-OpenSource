/**
 * Enhanced Error Handling Utility
 * 
 * Based on FastAPI + React integration best practices from MCP research.
 * Provides typed error classification, recovery actions, and accessible error messages.
 */

import type { AppError } from '@/types';

// Discriminated union for different error types (based on MCP research)
export type ApiError =
  | { kind: "http"; status: number; code?: string; detail: string; path?: string }
  | { kind: "network"; message: string; retriable: boolean }
  | { kind: "abort" }
  | { kind: "validation"; field: string; message: string; code?: string }
  | { kind: "unknown"; message: string };

// Accessible error response structure
export interface AccessibleErrorResponse {
  errors: {
    field?: string;
    message: string;
    ariaLabel: string;
    recoveryAction: string;
  }[];
  timestamp: string;
  supportContact?: string;
}

// Error classification based on status codes (FastAPI standard)
export const ErrorClassification = {
  // 4xx Client errors
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  METHOD_NOT_ALLOWED: 405,
  TIMEOUT: 408,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422, // Validation errors
  TOO_MANY_REQUESTS: 429,
  
  // 5xx Server errors
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
} as const;

/**
 * Decode various error types into standardized ApiError format
 * Based on MCP research for FastAPI + React integration
 */
export function decodeError(error: any): ApiError {
  // Handle AbortController cancellation
  if (error?.name === "AbortError") {
    return { kind: "abort" };
  }

  // Handle fetch/network errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return { 
      kind: "network", 
      message: "Network connection failed", 
      retriable: true 
    };
  }

  // Handle HTTP Response errors
  if (error?.response) {
    const { status, data } = error.response;
    return { 
      kind: "http", 
      status, 
      detail: data?.detail ?? "HTTP error occurred", 
      path: data?.path,
      code: data?.code 
    };
  }

  // Handle Response object (from fetch)
  if (error instanceof Response) {
    return {
      kind: "http",
      status: error.status,
      detail: error.statusText || "HTTP error occurred",
      path: error.url
    };
  }

  // Handle validation errors (422 responses)
  if (error?.status === ErrorClassification.UNPROCESSABLE_ENTITY || error?.field) {
    return {
      kind: "validation",
      field: error.field || "unknown",
      message: error.message || "Validation failed",
      code: error.code
    };
  }

  // Default to unknown error
  return { 
    kind: "unknown", 
    message: error?.message || String(error) || "An unexpected error occurred" 
  };
}

/**
 * Check if an error is retriable based on type and status code
 */
export function isRetriable(error: ApiError): boolean {
  switch (error.kind) {
    case "network":
      return error.retriable;
    case "http":
      // Retry on certain status codes
      return [
        ErrorClassification.TIMEOUT,
        ErrorClassification.TOO_MANY_REQUESTS,
        ErrorClassification.BAD_GATEWAY,
        ErrorClassification.SERVICE_UNAVAILABLE,
        ErrorClassification.GATEWAY_TIMEOUT
      ].includes(error.status as any);
    case "abort":
    case "validation":
    case "unknown":
    default:
      return false;
  }
}

/**
 * Convert ApiError to user-friendly AppError for store/UI
 */
export function toAppError(error: ApiError, context?: string): AppError {
  const timestamp = new Date().toISOString();
  
  switch (error.kind) {
    case "http":
      return {
        code: `HTTP_${error.status}`,
        message: getHttpErrorMessage(error.status, error.detail),
        details: error.path ? `Path: ${error.path}` : undefined,
        timestamp
      };
      
    case "network":
      return {
        code: "NETWORK_ERROR",
        message: "Network connection failed. Please check your internet connection and try again.",
        details: error.message,
        timestamp
      };
      
    case "abort":
      return {
        code: "REQUEST_CANCELLED",
        message: "Request was cancelled",
        timestamp
      };
      
    case "validation":
      return {
        code: "VALIDATION_ERROR",
        message: `${error.field}: ${error.message}`,
        details: context,
        timestamp
      };
      
    case "unknown":
    default:
      return {
        code: "UNKNOWN_ERROR",
        message: error.message || "An unexpected error occurred",
        details: context,
        timestamp
      };
  }
}

/**
 * Get user-friendly error messages for HTTP status codes
 */
function getHttpErrorMessage(status: number, detail?: string): string {
  switch (status) {
    case ErrorClassification.BAD_REQUEST:
      return detail || "Invalid request. Please check your input and try again.";
    case ErrorClassification.UNAUTHORIZED:
      return "Authentication required. Please check your API key and try again.";
    case ErrorClassification.FORBIDDEN:
      return "Access denied. You don't have permission to perform this action.";
    case ErrorClassification.NOT_FOUND:
      return detail || "The requested resource was not found.";
    case ErrorClassification.METHOD_NOT_ALLOWED:
      return "This operation is not supported.";
    case ErrorClassification.TIMEOUT:
      return "Request timed out. Please try again.";
    case ErrorClassification.CONFLICT:
      return detail || "There was a conflict with the current state.";
    case ErrorClassification.UNPROCESSABLE_ENTITY:
      return detail || "Invalid data provided. Please check your input.";
    case ErrorClassification.TOO_MANY_REQUESTS:
      return "Too many requests. Please wait a moment and try again.";
    case ErrorClassification.INTERNAL_SERVER_ERROR:
      return "Server error occurred. Please try again later.";
    case ErrorClassification.BAD_GATEWAY:
      return "Gateway error. Please try again.";
    case ErrorClassification.SERVICE_UNAVAILABLE:
      return "Service temporarily unavailable. Please try again later.";
    case ErrorClassification.GATEWAY_TIMEOUT:
      return "Request timed out. Please try again.";
    default:
      return detail || `HTTP error ${status}. Please try again.`;
  }
}

/**
 * Create accessible error message with recovery actions
 */
export function createAccessibleError(
  error: ApiError, 
  field?: string
): AccessibleErrorResponse {
  const recoveryAction = getRecoveryAction(error);
  const ariaLabel = getAriaLabel(error, field);
  
  return {
    errors: [{
      field,
      message: error.kind === "http" ? error.detail : 
               error.kind === "validation" ? error.message :
               error.kind === "network" ? error.message :
               "An error occurred",
      ariaLabel,
      recoveryAction
    }],
    timestamp: new Date().toISOString(),
    supportContact: "support@neurobridge.edu"
  };
}

function getRecoveryAction(error: ApiError): string {
  switch (error.kind) {
    case "http":
      switch (error.status) {
        case ErrorClassification.UNAUTHORIZED:
          return "Please check your API key and try again.";
        case ErrorClassification.TOO_MANY_REQUESTS:
          return "Please wait a moment before trying again.";
        case ErrorClassification.UNPROCESSABLE_ENTITY:
          return "Please check your input and correct any errors.";
        default:
          return isRetriable(error) ? "Please try again." : "Please contact support if this continues.";
      }
    case "network":
      return "Please check your internet connection and try again.";
    case "validation":
      return "Please correct the highlighted field and try again.";
    case "abort":
      return "The request was cancelled. You can try again if needed.";
    default:
      return "Please refresh the page or contact support if the problem persists.";
  }
}

function getAriaLabel(error: ApiError, field?: string): string {
  const fieldPrefix = field ? `Error in ${field}: ` : "Error: ";
  
  switch (error.kind) {
    case "http":
      return `${fieldPrefix}HTTP ${error.status} error occurred`;
    case "network":
      return `${fieldPrefix}Network connection error`;
    case "validation":
      return `${fieldPrefix}Validation error in ${error.field}`;
    case "abort":
      return `${fieldPrefix}Request was cancelled`;
    default:
      return `${fieldPrefix}An unexpected error occurred`;
  }
}

/**
 * Exponential backoff retry utility
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>, 
  options: {
    retries?: number;
    minDelay?: number;
    maxDelay?: number;
    onRetry?: (attempt: number, error: any) => void;
  } = {}
): Promise<T> {
  const { retries = 3, minDelay = 300, maxDelay = 4000, onRetry } = options;
  
  let attempt = 0;
  
  while (true) {
    try {
      return await fn();
    } catch (error) {
      attempt++;
      const apiError = decodeError(error);
      
      if (!isRetriable(apiError) || attempt > retries) {
        throw error;
      }
      
      if (onRetry) {
        onRetry(attempt, error);
      }
      
      // Exponential backoff with jitter
      const baseDelay = Math.min(minDelay * Math.pow(2, attempt - 1), maxDelay);
      const jitter = Math.random() * 0.5; // ±25% jitter
      const delay = baseDelay * (1 + jitter);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

/**
 * Enhanced fetch wrapper with error handling and retries
 */
export async function enhancedFetch<T>(
  url: string, 
  options: RequestInit & { 
    retries?: number;
    timeout?: number;
  } = {}
): Promise<T> {
  const { retries = 1, timeout = 30000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await retryWithBackoff(
      async () => {
        const res = await fetch(url, {
          ...fetchOptions,
          signal: controller.signal
        });
        
        if (!res.ok) {
          let errorData: any = {};
          try {
            errorData = await res.json();
          } catch {
            // Response body isn't JSON
          }
          
          const apiError: ApiError = {
            kind: "http",
            status: res.status,
            detail: errorData.detail || res.statusText,
            path: errorData.path || url,
            code: errorData.code
          };
          
          throw apiError;
        }
        
        return res;
      },
      { retries }
    );
    
    clearTimeout(timeoutId);
    return await response.json();
    
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}