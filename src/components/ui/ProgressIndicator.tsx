import React from 'react';
import { Loader2 } from 'lucide-react';

interface ProgressIndicatorProps {
  message?: string;
  progress?: number;
  isIndeterminate?: boolean;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  message = 'Processing...',
  progress,
  isIndeterminate = true,
}) => {
  return (
    <div className="w-full p-6 bg-gradient-to-br from-purple-50 to-white border border-purple-200 rounded-xl">
      <div className="flex items-center justify-center mb-4">
        <Loader2 className="w-6 h-6 text-purple-600 animate-spin mr-3" />
        <span className="text-sm font-medium text-gray-700">{message}</span>
      </div>
      
      <div className="relative w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        {isIndeterminate ? (
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-purple-600 animate-pulse" />
        ) : (
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-purple-600 transition-all duration-300 ease-out"
            style={{ width: `${progress || 0}%` }}
          />
        )}
      </div>
      
      {!isIndeterminate && progress !== undefined && (
        <div className="mt-2 text-center">
          <span className="text-xs text-gray-500">{Math.round(progress)}% complete</span>
        </div>
      )}
    </div>
  );
};