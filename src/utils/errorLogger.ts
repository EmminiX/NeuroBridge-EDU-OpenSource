/**
 * Comprehensive Error Logging System for NeuroBridge EDU
 * 
 * Provides centralized error tracking, reporting, and monitoring
 * for both frontend and backend integration.
 */

interface ErrorContext {
  userId?: string;
  sessionId?: string;
  component?: string;
  action?: string;
  timestamp?: string;
  userAgent?: string;
  url?: string;
  stackTrace?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  tags?: string[];
  metadata?: Record<string, any>;
}

interface ErrorReport {
  id: string;
  message: string;
  type: 'javascript' | 'network' | 'api' | 'transcription' | 'audio' | 'ui' | 'validation';
  context: ErrorContext;
  resolved: boolean;
  reportedAt: string;
}

class ErrorLogger {
  private errors: ErrorReport[] = [];
  private maxErrors = 100; // Keep last 100 errors in memory
  private isDevelopment = (import.meta as any).env?.DEV || false;

  /**
   * Log an error with context
   */
  logError(
    error: Error | string, 
    type: ErrorReport['type'] = 'javascript',
    context: Partial<ErrorContext> = {}
  ): void {
    const errorMessage = error instanceof Error ? error.message : error;
    const stackTrace = error instanceof Error ? error.stack : undefined;

    const errorReport: ErrorReport = {
      id: this.generateErrorId(),
      message: errorMessage,
      type,
      context: {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        stackTrace,
        severity: context.severity || 'medium',
        ...context
      },
      resolved: false,
      reportedAt: new Date().toISOString()
    };

    // Add to memory store
    this.errors.unshift(errorReport);
    if (this.errors.length > this.maxErrors) {
      this.errors = this.errors.slice(0, this.maxErrors);
    }

    // Console logging in development
    if (this.isDevelopment) {
      console.group(`🚨 Error [${type.toUpperCase()}]`);
      console.error('Message:', errorMessage);
      console.error('Context:', context);
      if (stackTrace) {
        console.error('Stack:', stackTrace);
      }
      console.groupEnd();
    }

    // Send to backend for persistence (non-blocking)
    this.sendToBackend(errorReport).catch(err => {
      console.warn('Failed to send error to backend:', err);
    });
  }

  /**
   * Log transcription-specific errors
   */
  logTranscriptionError(
    error: Error | string,
    sessionId?: string,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'transcription', {
      sessionId,
      component: 'TranscriptionService',
      severity: 'high',
      tags: ['transcription', 'real-time'],
      ...additionalContext
    });
  }

  /**
   * Log API errors with request details
   */
  logApiError(
    error: Error | string,
    endpoint: string,
    method: string = 'GET',
    statusCode?: number,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'api', {
      action: `${method} ${endpoint}`,
      severity: statusCode && statusCode >= 500 ? 'high' : 'medium',
      tags: ['api', 'network'],
      metadata: {
        endpoint,
        method,
        statusCode
      },
      ...additionalContext
    });
  }

  /**
   * Log network connectivity errors
   */
  logNetworkError(
    error: Error | string,
    url?: string,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'network', {
      action: `Network request to ${url}`,
      severity: 'high',
      tags: ['network', 'connectivity'],
      metadata: {
        targetUrl: url
      },
      ...additionalContext
    });
  }

  /**
   * Log audio-related errors
   */
  logAudioError(
    error: Error | string,
    deviceInfo?: MediaDeviceInfo,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'audio', {
      component: 'AudioRecorder',
      severity: 'high',
      tags: ['audio', 'microphone'],
      metadata: {
        deviceId: deviceInfo?.deviceId,
        deviceLabel: deviceInfo?.label,
        deviceKind: deviceInfo?.kind
      },
      ...additionalContext
    });
  }

  /**
   * Log UI component errors
   */
  logUIError(
    error: Error | string,
    component: string,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'ui', {
      component,
      severity: 'low',
      tags: ['ui', 'component', 'react'],
      ...additionalContext
    });
  }

  /**
   * Log validation errors
   */
  logValidationError(
    error: Error | string,
    fieldName: string,
    value: any,
    additionalContext: Partial<ErrorContext> = {}
  ): void {
    this.logError(error, 'validation', {
      action: `Validation failed for ${fieldName}`,
      severity: 'low',
      tags: ['validation', 'form'],
      metadata: {
        fieldName,
        value: typeof value === 'string' ? value : JSON.stringify(value)
      },
      ...additionalContext
    });
  }

  /**
   * Get recent errors for debugging
   */
  getRecentErrors(limit = 20): ErrorReport[] {
    return this.errors.slice(0, limit);
  }

  /**
   * Get errors by type
   */
  getErrorsByType(type: ErrorReport['type']): ErrorReport[] {
    return this.errors.filter(error => error.type === type);
  }

  /**
   * Get unresolved errors
   */
  getUnresolvedErrors(): ErrorReport[] {
    return this.errors.filter(error => !error.resolved);
  }

  /**
   * Mark error as resolved
   */
  markAsResolved(errorId: string): void {
    const error = this.errors.find(e => e.id === errorId);
    if (error) {
      error.resolved = true;
    }
  }

  /**
   * Clear all errors (for testing/debugging)
   */
  clearErrors(): void {
    this.errors = [];
  }

  /**
   * Get error statistics
   */
  getErrorStats(): {
    total: number;
    unresolved: number;
    byType: Record<string, number>;
    bySeverity: Record<string, number>;
  } {
    const byType: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};

    this.errors.forEach(error => {
      byType[error.type] = (byType[error.type] || 0) + 1;
      const severity = error.context.severity || 'medium';
      bySeverity[severity] = (bySeverity[severity] || 0) + 1;
    });

    return {
      total: this.errors.length,
      unresolved: this.getUnresolvedErrors().length,
      byType,
      bySeverity
    };
  }

  /**
   * Generate unique error ID
   */
  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Send error to backend for persistence
   */
  private async sendToBackend(errorReport: ErrorReport): Promise<void> {
    try {
      // Use the correct backend URL - avoid infinite loops by using backend port
      const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
      const response = await fetch(`${API_BASE_URL}/api/errors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorReport),
      });

      if (!response.ok) {
        throw new Error(`Failed to log error: ${response.statusText}`);
      }
    } catch (error) {
      // Silently fail - don't create infinite error loops
      if (this.isDevelopment) {
        console.warn('Could not send error to backend:', error);
      }
    }
  }
}

// Global error handlers
const setupGlobalErrorHandlers = (errorLogger: ErrorLogger) => {
  // Unhandled JavaScript errors
  window.addEventListener('error', (event) => {
    errorLogger.logError(
      event.error || event.message,
      'javascript',
      {
        component: 'GlobalErrorHandler',
        severity: 'high',
        metadata: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        }
      }
    );
  });

  // Unhandled Promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    errorLogger.logError(
      event.reason?.message || event.reason || 'Unhandled promise rejection',
      'javascript',
      {
        component: 'GlobalErrorHandler',
        severity: 'high',
        tags: ['promise', 'async']
      }
    );
  });

  // Network errors (fetch)
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    try {
      const response = await originalFetch(...args);
      
      // Log API errors
      if (!response.ok) {
        const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request).url;
        const method = args[1]?.method || 'GET';
        
        errorLogger.logApiError(
          `HTTP ${response.status}: ${response.statusText}`,
          url,
          method,
          response.status
        );
      }
      
      return response;
    } catch (error) {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request).url;
      errorLogger.logNetworkError(error as Error, url);
      throw error;
    }
  };
};

// Singleton instance
export const errorLogger = new ErrorLogger();

// Initialize global error handlers
setupGlobalErrorHandlers(errorLogger);

// React Error Boundary Hook
export const useErrorHandler = () => {
  return {
    logError: errorLogger.logError.bind(errorLogger),
    logTranscriptionError: errorLogger.logTranscriptionError.bind(errorLogger),
    logApiError: errorLogger.logApiError.bind(errorLogger),
    logNetworkError: errorLogger.logNetworkError.bind(errorLogger),
    logAudioError: errorLogger.logAudioError.bind(errorLogger),
    logUIError: errorLogger.logUIError.bind(errorLogger),
    logValidationError: errorLogger.logValidationError.bind(errorLogger),
    getErrorStats: errorLogger.getErrorStats.bind(errorLogger),
    getRecentErrors: errorLogger.getRecentErrors.bind(errorLogger),
    clearErrors: errorLogger.clearErrors.bind(errorLogger)
  };
};

export default errorLogger;