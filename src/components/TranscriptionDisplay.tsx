/**
 * Transcription Display Component
 * 
 * Shows real-time transcription text with smooth streaming updates,
 * auto-scroll functionality, and manual scroll override.
 */

import React, { useRef, useEffect, useState } from 'react';
import { Copy, Download, RotateCcw, ScrollText, TrendingUp, Type, Zap } from 'lucide-react';
import { VictoryLine, VictoryChart, VictoryTheme } from 'victory';
import * as Tooltip from '@radix-ui/react-tooltip';
import * as Separator from '@radix-ui/react-separator';
import { useAppStore } from '@/stores/appStore';
import { cn, formatTimestamp } from '@/utils/cn';
import { copyToClipboard } from '@/utils/api';

const TranscriptionDisplay: React.FC = () => {
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const [lastCopyTime, setLastCopyTime] = useState<number>(0);
  const [transcriptionProgress, setTranscriptionProgress] = useState<Array<{ x: number; y: number }>>([]);
  const [wordsPerMinute, setWordsPerMinute] = useState(0);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Use selector functions instead of object destructuring for reactive updates
  const transcriptionText = useAppStore((state) => state.transcriptionText);
  const isRecording = useAppStore((state) => state.isRecording);
  const transcriptionSession = useAppStore((state) => state.transcriptionSession);
  const clearAllErrors = useAppStore((state) => state.clearAllErrors);

  // Track transcription progress and calculate WPM
  useEffect(() => {
    if (isRecording && transcriptionText) {
      const wordCount = transcriptionText.split(/\s+/).filter(word => word.length > 0).length;
      const timestamp = Date.now();
      
      setTranscriptionProgress(prev => {
        const newProgress = [...prev, { x: timestamp, y: wordCount }].slice(-30);
        return newProgress;
      });

      if (transcriptionSession && transcriptionSession.duration > 0) {
        const minutes = transcriptionSession.duration / 60000;
        setWordsPerMinute(Math.round(wordCount / minutes));
      }
    } else if (!isRecording) {
      setTranscriptionProgress([]);
      setWordsPerMinute(0);
    }
  }, [transcriptionText, isRecording, transcriptionSession]);

  // Auto-scroll to bottom when new text arrives
  useEffect(() => {
    if (isAutoScroll && textAreaRef.current) {
      textAreaRef.current.scrollTop = textAreaRef.current.scrollHeight;
    }
  }, [transcriptionText, isAutoScroll]);

  // Handle manual scroll - disable auto-scroll if user scrolls up
  const handleScroll = () => {
    if (textAreaRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = textAreaRef.current;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setIsAutoScroll(isAtBottom);
    }
  };

  // Enable auto-scroll manually
  const enableAutoScroll = () => {
    setIsAutoScroll(true);
    if (textAreaRef.current) {
      textAreaRef.current.scrollTop = textAreaRef.current.scrollHeight;
    }
  };

  // Copy transcription to clipboard
  const handleCopy = async () => {
    if (transcriptionText.trim()) {
      const success = await copyToClipboard(transcriptionText);
      if (success) {
        setLastCopyTime(Date.now());
        setTimeout(() => setLastCopyTime(0), 2000);
      }
    }
  };

  // Download transcription as text file
  const handleDownload = () => {
    if (!transcriptionText.trim()) return;

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `transcription-${timestamp}.txt`;
    
    const blob = new Blob([transcriptionText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
  };

  // Clear transcription
  const handleClear = () => {
    if (!isRecording) {
      useAppStore.getState().updateTranscription('');
      clearAllErrors();
    }
  };

  const hasText = transcriptionText.length > 0;
  const showCopySuccess = Date.now() - lastCopyTime < 2000;

  return (
    <Tooltip.Provider>
      <div className="card-secondary">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-secondary-500 to-secondary-600 rounded-xl flex items-center justify-center shadow-lg">
              <ScrollText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Live Transcription</h3>
              <p className="text-sm text-gray-500">Real-time speech-to-text with Whisper</p>
            </div>
          </div>
          
          {/* Status and Metrics */}
          <div className="flex items-center space-x-4">
            {isRecording && (
              <div className="flex items-center space-x-3">
                <div className="flex items-center px-3 py-1.5 rounded-full bg-secondary-100">
                  <div className="w-2 h-2 bg-secondary-500 rounded-full animate-pulse mr-2" />
                  <span className="text-sm font-medium text-secondary-700">
                    Transcribing...
                  </span>
                </div>
                {wordsPerMinute > 0 && (
                  <Tooltip.Root>
                    <Tooltip.Trigger asChild>
                      <div className="flex items-center px-3 py-1.5 rounded-full bg-blue-100">
                        <TrendingUp className="w-3 h-3 text-blue-600 mr-1" />
                        <span className="text-sm font-medium text-blue-700">
                          {wordsPerMinute} WPM
                        </span>
                      </div>
                    </Tooltip.Trigger>
                    <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                      Words per minute
                    </Tooltip.Content>
                  </Tooltip.Root>
                )}
              </div>
            )}
            
            {transcriptionSession && (
              <span className="text-xs text-gray-500">
                Started {formatTimestamp(transcriptionSession.startTime)}
              </span>
            )}
          </div>
        </div>

        {/* Enhanced Action Buttons */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {!isAutoScroll && (
              <Tooltip.Root>
                <Tooltip.Trigger asChild>
                  <button
                    onClick={enableAutoScroll}
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                    aria-label="Enable auto-scroll"
                  >
                    <ScrollText className="w-4 h-4" />
                  </button>
                </Tooltip.Trigger>
                <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                  Enable auto-scroll
                </Tooltip.Content>
              </Tooltip.Root>
            )}

            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={handleCopy}
                  disabled={!hasText}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg hover:bg-gray-100 transition-colors"
                  aria-label="Copy transcription to clipboard"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                Copy to clipboard
              </Tooltip.Content>
            </Tooltip.Root>

            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={handleDownload}
                  disabled={!hasText}
                  className="p-2 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg hover:bg-gray-100 transition-colors"
                  aria-label="Download transcription"
                >
                  <Download className="w-4 h-4" />
                </button>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                Download as text file
              </Tooltip.Content>
            </Tooltip.Root>

            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={handleClear}
                  disabled={!hasText || isRecording}
                  className="p-2 text-gray-400 hover:text-red-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg hover:bg-red-50 transition-colors"
                  aria-label="Clear transcription"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                Clear transcription
              </Tooltip.Content>
            </Tooltip.Root>
          </div>

          {/* Real-time Progress Chart */}
          {isRecording && transcriptionProgress.length > 5 && (
            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500">Progress</span>
              <div className="w-24 h-8">
                <VictoryChart
                  theme={VictoryTheme.material}
                  height={40}
                  width={100}
                  padding={{ left: 5, right: 5, top: 5, bottom: 5 }}
                >
                  <VictoryLine
                    data={transcriptionProgress}
                    style={{
                      data: { stroke: "#22c55e", strokeWidth: 2 },
                    }}
                    animate={{ duration: 200 }}
                  />
                </VictoryChart>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Copy Success Notification */}
      {showCopySuccess && (
        <div className="mb-4 p-2 bg-secondary-50 border border-secondary-200 rounded-lg">
          <p className="text-sm text-secondary-700 text-center">
            Transcription copied to clipboard!
          </p>
        </div>
      )}

      {/* Transcription Text Area */}
      <div ref={containerRef} className="relative">
        <textarea
          ref={textAreaRef}
          value={transcriptionText}
          onChange={(e) => useAppStore.getState().updateTranscription(e.target.value)}
          onScroll={handleScroll}
          placeholder={
            isRecording 
              ? "Transcription will appear here as you speak..."
              : "Click the microphone button to start recording and see live transcription here..."
          }
          className={cn(
            'w-full h-48 p-3 border border-gray-300 rounded-lg resize-none font-mono text-sm leading-relaxed',
            'focus:ring-primary-500 focus:border-primary-500',
            'scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100',
            isRecording && 'bg-gray-50'
          )}
          readOnly={isRecording}
          aria-label="Live transcription text"
          aria-live={isRecording ? 'polite' : 'off'}
          aria-atomic="false"
        />

        {/* Auto-scroll indicator */}
        {!isAutoScroll && hasText && (
          <div className="absolute bottom-4 right-4 bg-primary-600 text-white px-3 py-1 rounded-full text-xs shadow-lg">
            Auto-scroll disabled
          </div>
        )}

        {/* Streaming indicator */}
        {isRecording && (
          <div className="absolute top-4 right-4 flex items-center space-x-2 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full shadow-sm">
            <div className="w-2 h-2 bg-secondary-500 rounded-full animate-pulse" />
            <span className="text-xs text-gray-700">Live</span>
          </div>
        )}
      </div>

        {/* Enhanced Stats */}
        {hasText && (
          <>
            <Separator.Root className="my-3 h-px bg-gray-200" />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-2 rounded-lg border border-blue-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xl font-bold text-blue-700">
                      {transcriptionText.split(/\s+/).filter(word => word.length > 0).length}
                    </div>
                    <div className="text-xs text-blue-600 font-medium">Words</div>
                  </div>
                  <Type className="w-5 h-5 text-blue-500" />
                </div>
              </div>

              <div className="bg-gradient-to-br from-green-50 to-green-100 p-2 rounded-lg border border-green-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xl font-bold text-green-700">
                      {transcriptionText.length}
                    </div>
                    <div className="text-xs text-green-600 font-medium">Characters</div>
                  </div>
                  <ScrollText className="w-5 h-5 text-green-500" />
                </div>
              </div>

              {transcriptionSession && transcriptionSession.duration > 0 && (
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-2 rounded-lg border border-purple-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xl font-bold text-purple-700">
                        {wordsPerMinute || Math.round(transcriptionText.split(/\s+/).length / (transcriptionSession.duration / 60000))}
                      </div>
                      <div className="text-xs text-purple-600 font-medium">WPM</div>
                    </div>
                    <TrendingUp className="w-5 h-5 text-purple-500" />
                  </div>
                </div>
              )}

              {isRecording && (
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-2 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xl font-bold text-orange-700">
                        Live
                      </div>
                      <div className="text-xs text-orange-600 font-medium">Status</div>
                    </div>
                    <Zap className="w-5 h-5 text-orange-500 animate-pulse" />
                  </div>
                </div>
              )}
            </div>
          </>
        )}

      {/* Empty State */}
      {!hasText && !isRecording && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ScrollText className="w-8 h-8 text-gray-400" />
          </div>
          <h4 className="text-lg font-medium text-gray-900 mb-2">
            Ready for Transcription
          </h4>
          <p className="text-gray-600 max-w-sm mx-auto">
            Start recording to see live transcription of your speech appear here in real-time.
          </p>
        </div>
      )}
    </Tooltip.Provider>
  );
};

export default TranscriptionDisplay;