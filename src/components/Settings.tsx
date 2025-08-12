/**
 * Settings Component - Secure API Key Management
 * 
 * Provides secure interface for managing OpenAI API keys with:
 * - React Hook Form for validation
 * - In-memory only key handling (no localStorage)
 * - Masked key display with secure reveal
 * - Accessible form patterns
 * - Comprehensive error handling
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { 
  Key, 
  Plus, 
  Eye, 
  EyeOff, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader,
  Shield,
  Info
} from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { cn } from '@/utils/cn';
import { decodeError, toAppError } from '@/utils/errorHandler';
import type { ApiKeyCreateRequest, ApiKey } from '@/types';

interface ApiKeyFormData {
  api_key: string;
  label: string;
}

const Settings: React.FC = () => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [deletingKeys, setDeletingKeys] = useState<Set<string>>(new Set());
  
  // Store selectors
  const apiKeys = useAppStore((state) => state.apiKeys);
  const validationStatuses = useAppStore((state) => state.validationStatuses);
  const addApiKey = useAppStore((state) => state.addApiKey);
  const validateApiKey = useAppStore((state) => state.validateApiKey);
  const deleteApiKey = useAppStore((state) => state.deleteApiKey);
  const loadApiKeys = useAppStore((state) => state.loadApiKeys);

  // React Hook Form setup with security-focused validation
  const {
    register,
    handleSubmit,
    formState: { errors: formErrors, isSubmitting },
    reset,
    watch,
    clearErrors
  } = useForm<ApiKeyFormData>({
    mode: 'onBlur',
    defaultValues: {
      api_key: '',
      label: ''
    }
  });

  const watchedKey = watch('api_key');

  // Load API keys on mount
  useEffect(() => {
    loadApiKeys();
  }, [loadApiKeys]);

  // Clear form when closing
  useEffect(() => {
    if (!showAddForm) {
      reset();
      clearErrors();
    }
  }, [showAddForm, reset, clearErrors]);

  // Security: Auto-hide revealed keys after timeout
  useEffect(() => {
    const timers = Array.from(revealedKeys).map(keyId => 
      setTimeout(() => {
        setRevealedKeys(prev => {
          const next = new Set(prev);
          next.delete(keyId);
          return next;
        });
      }, 10000) // 10 second reveal timeout
    );

    return () => timers.forEach(clearTimeout);
  }, [revealedKeys]);

  // Validation functions
  const validateApiKeyFormat = (value: string): string | boolean => {
    if (!value) return 'API key is required';
    if (!/^sk-[A-Za-z0-9_\-]{20,}$/.test(value)) {
      return 'Invalid OpenAI API key format (should start with sk-)';
    }
    if (value.length > 200) return 'API key is too long';
    return true;
  };

  const validateLabel = (value: string): string | boolean => {
    if (!value.trim()) return 'Label is required';
    if (value.length > 50) return 'Label must be 50 characters or less';
    return true;
  };

  // Form submission handler with enhanced error handling
  const onSubmit = async (data: ApiKeyFormData) => {
    try {
      const keyData: ApiKeyCreateRequest = {
        provider: 'openai',
        api_key: data.api_key.trim(),
        label: data.label.trim()
      };

      await addApiKey(keyData);
      
      // Clear form immediately after successful submission
      reset();
      setShowAddForm(false);
      
    } catch (error) {
      // Enhanced error handling with user-friendly messages
      const apiError = decodeError(error);
      const appError = toAppError(apiError, 'Adding API key');
      
      // Log technical details for debugging
      console.error('Failed to add API key:', {
        original: error,
        decoded: apiError,
        userMessage: appError.message
      });
      
      // The error is already added to the store by addApiKey, 
      // but we could show additional UI feedback here if needed
    }
  };

  // Toggle key visibility with security timeout
  const toggleKeyVisibility = (keyId: string) => {
    setRevealedKeys(prev => {
      const next = new Set(prev);
      if (next.has(keyId)) {
        next.delete(keyId);
      } else {
        next.add(keyId);
      }
      return next;
    });
  };

  // Delete API key with confirmation
  const handleDeleteKey = async (keyId: string, label: string) => {
    if (!confirm(`Are you sure you want to delete the API key "${label}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingKeys(prev => new Set(prev.add(keyId)));
    
    try {
      await deleteApiKey(keyId);
    } finally {
      setDeletingKeys(prev => {
        const next = new Set(prev);
        next.delete(keyId);
        return next;
      });
    }
  };

  // Mask API key for display
  const maskApiKey = (lastFourChars: string): string => {
    return `sk-••••••••••••••••••••••••••••••••••••••••••${lastFourChars}`;
  };

  // Get status icon for API key
  const getStatusIcon = (key: ApiKey) => {
    const validation = validationStatuses[key.id];
    
    if (validation?.status === 'validating') {
      return <Loader className="w-4 h-4 animate-spin text-blue-500" />;
    }
    
    switch (key.status) {
      case 'active':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'invalid':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'expired':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">API Key Management</h2>
            <p className="text-gray-600">Securely manage your OpenAI API keys</p>
          </div>
        </div>
        
        {!showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            aria-label="Add new API key"
          >
            <Plus className="w-4 h-4" />
            <span>Add API Key</span>
          </button>
        )}
      </div>

      {/* Security Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="text-blue-800 font-medium mb-1">Security Information</p>
            <p className="text-blue-700">
              Your API keys are encrypted and stored securely on the server. They are never stored in your browser's local storage. 
              Keys are only transmitted over HTTPS and are masked in the interface for your security.
            </p>
          </div>
        </div>
      </div>

      {/* Add API Key Form */}
      {showAddForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Add OpenAI API Key</h3>
            <button
              onClick={() => setShowAddForm(false)}
              className="text-gray-400 hover:text-gray-600 p-1"
              aria-label="Cancel adding API key"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label htmlFor="label" className="block text-sm font-medium text-gray-700 mb-1">
                Label *
              </label>
              <input
                id="label"
                type="text"
                placeholder="e.g., Personal OpenAI Key"
                className={cn(
                  'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                  formErrors.label ? 'border-red-500' : 'border-gray-300'
                )}
                aria-invalid={!!formErrors.label}
                aria-describedby={formErrors.label ? 'label-error' : undefined}
                {...register('label', { validate: validateLabel })}
              />
              {formErrors.label && (
                <p id="label-error" role="alert" className="mt-1 text-sm text-red-600">
                  {formErrors.label.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 mb-1">
                OpenAI API Key *
              </label>
              <input
                id="api_key"
                type="password"
                inputMode="text"
                autoComplete="off"
                spellCheck={false}
                placeholder="sk-..."
                className={cn(
                  'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors font-mono text-sm',
                  formErrors.api_key ? 'border-red-500' : 'border-gray-300'
                )}
                aria-invalid={!!formErrors.api_key}
                aria-describedby={formErrors.api_key ? 'api-key-error api-key-help' : 'api-key-help'}
                {...register('api_key', { validate: validateApiKeyFormat })}
              />
              <p id="api-key-help" className="mt-1 text-sm text-gray-500">
                Your API key will be encrypted and stored securely
              </p>
              {formErrors.api_key && (
                <p id="api-key-error" role="alert" className="mt-1 text-sm text-red-600">
                  {formErrors.api_key.message}
                </p>
              )}
            </div>

            <div className="flex items-center space-x-3 pt-2">
              <button
                type="submit"
                disabled={isSubmitting || !watchedKey}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {isSubmitting ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    <span>Adding...</span>
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    <span>Add Key</span>
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* API Keys List */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Stored API Keys</h3>
          <p className="text-sm text-gray-600 mt-1">
            {apiKeys.length === 0 ? 'No API keys stored' : `${apiKeys.length} key${apiKeys.length === 1 ? '' : 's'} stored`}
          </p>
        </div>

        {apiKeys.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <Key className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-2">No API keys configured</p>
            <p className="text-sm text-gray-400">Add an OpenAI API key to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {apiKeys.map((key) => (
              <div key={key.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(key)}
                        <span className="font-medium text-gray-900">{key.label}</span>
                      </div>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {key.provider.toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono">
                          {revealedKeys.has(key.id) 
                            ? `sk-${'•'.repeat(48)}${key.last_four_chars}`
                            : maskApiKey(key.last_four_chars)
                          }
                        </span>
                        <button
                          onClick={() => toggleKeyVisibility(key.id)}
                          className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                          aria-label={revealedKeys.has(key.id) ? 'Hide API key' : 'Reveal API key'}
                          title={revealedKeys.has(key.id) ? 'Hide key' : 'Reveal key (10s timeout)'}
                        >
                          {revealedKeys.has(key.id) ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      
                      <div>
                        Created: {new Date(key.created_at).toLocaleDateString()}
                      </div>
                      
                      {key.last_used_at && (
                        <div>
                          Last used: {new Date(key.last_used_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>

                    {validationStatuses[key.id]?.message && (
                      <p className={cn(
                        'mt-2 text-sm',
                        validationStatuses[key.id].status === 'valid' ? 'text-green-600' : 
                        validationStatuses[key.id].status === 'invalid' ? 'text-red-600' : 'text-gray-600'
                      )}>
                        {validationStatuses[key.id].message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => validateApiKey(key.id)}
                      disabled={validationStatuses[key.id]?.status === 'validating'}
                      className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                      aria-label={`Validate ${key.label} API key`}
                    >
                      {validationStatuses[key.id]?.status === 'validating' ? 'Validating...' : 'Test'}
                    </button>
                    
                    <button
                      onClick={() => handleDeleteKey(key.id, key.label)}
                      disabled={deletingKeys.has(key.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      aria-label={`Delete ${key.label} API key`}
                    >
                      {deletingKeys.has(key.id) ? (
                        <Loader className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-3">How to get an OpenAI API Key</h4>
        <div className="space-y-2 text-sm text-gray-700">
          <p>1. Go to <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">platform.openai.com/api-keys</a></p>
          <p>2. Sign in to your OpenAI account</p>
          <p>3. Click "Create new secret key"</p>
          <p>4. Copy the key and paste it above</p>
          <p className="text-yellow-700 bg-yellow-50 p-2 rounded border border-yellow-200 mt-3">
            <strong>Important:</strong> Keep your API key secure and never share it publicly. 
            Your key provides access to your OpenAI account and usage will be charged to you.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Settings;