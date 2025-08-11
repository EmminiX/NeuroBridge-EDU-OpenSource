/**
 * Audio Recorder Component
 * 
 * Provides the main recording interface with a large record button,
 * audio level visualization, and recording status display.
 */

import React, { useState, useEffect } from 'react';
import { Mic, MicOff, Settings, Activity, Clock } from 'lucide-react';
import * as Progress from '@radix-ui/react-progress';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useTranscription } from '@/hooks/useTranscription';
import { cn, formatDuration } from '@/utils/cn';

const AudioRecorder: React.FC = () => {
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [showSettings, setShowSettings] = useState(false);
  const [, setAudioHistory] = useState<Array<{ x: number; y: number }>>([]);
  const [recordingProgress, setRecordingProgress] = useState(0);

  const {
    isRecording,
    duration,
    audioLevel,
    isConnected,
    toggleTranscription,
    getAudioDevices,
    changeAudioDevice,
  } = useTranscription();

  // Load available audio devices on mount
  useEffect(() => {
    const loadDevices = async () => {
      const devices = await getAudioDevices();
      setAvailableDevices(devices);
      
      if (devices.length > 0 && !selectedDevice) {
        setSelectedDevice(devices[0].deviceId);
      }
    };

    loadDevices();
  }, [getAudioDevices, selectedDevice]);

  // Handle device change
  const handleDeviceChange = async (deviceId: string) => {
    setSelectedDevice(deviceId);
    await changeAudioDevice(deviceId);
  };

  // Update audio waveform data
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        const timestamp = Date.now();
        const newPoint = { x: timestamp, y: audioLevel };
        
        setAudioHistory(prev => {
          const newHistory = [...prev, newPoint].slice(-50); // Keep last 50 points
          return newHistory;
        });
        
        // Update recording progress (example: 5 minutes max)
        const maxDuration = 5 * 60 * 1000; // 5 minutes in ms
        setRecordingProgress((duration / maxDuration) * 100);
      }, 100);

      return () => clearInterval(interval);
    } else {
      setAudioHistory([]);
      setRecordingProgress(0);
    }
  }, [isRecording, audioLevel, duration]);

  // Audio level visualization
  const audioLevelBars = Array.from({ length: 10 }, (_, i) => {
    const isActive = audioLevel * 10 > i;
    return (
      <div
        key={i}
        className={cn(
          'w-2 bg-gray-300 rounded-full audio-level-bar transition-colors duration-100',
          isActive && isRecording && 'bg-secondary-500',
          i < 3 && 'h-2',
          i >= 3 && i < 7 && 'h-4',
          i >= 7 && 'h-6'
        )}
      />
    );
  });

  // const status = getStatus();

  return (
    <Tooltip.Provider>
      <div className="card-primary">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Audio Recording</h3>
              <p className="text-sm text-gray-500">High-quality speech capture</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Connection Status */}
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <div className="flex items-center px-3 py-1.5 rounded-full bg-gray-100">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full mr-2',
                      isConnected ? 'bg-secondary-500 animate-pulse' : 'bg-red-500'
                    )}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                OpenAI Whisper {isConnected ? 'Active' : 'Inactive'}
              </Tooltip.Content>
            </Tooltip.Root>

            {/* Settings Button */}
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                  aria-label="Audio settings"
                >
                  <Settings className="w-4 h-4" />
                </button>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                Audio Settings
              </Tooltip.Content>
            </Tooltip.Root>
          </div>
        </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="mb-6 p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border-2 border-gray-300 shadow-md">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Audio Settings</h4>
          
          <div className="space-y-3">
            <div>
              <label htmlFor="audio-device" className="block text-sm font-medium text-gray-700 mb-1">
                Microphone Device
              </label>
              <select
                id="audio-device"
                value={selectedDevice}
                onChange={(e) => handleDeviceChange(e.target.value)}
                className="input-field"
                disabled={isRecording}
              >
                {availableDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

        {/* Main Recording Interface */}
        <div className="space-y-8">
          {/* Enhanced Record Button with Progress Ring */}
          <div className="flex flex-col items-center">
            <div className="relative">
              {/* Progress Ring */}
              {isRecording && (
                <div className="absolute inset-0 w-32 h-32">
                  <Progress.Root className="relative overflow-hidden bg-transparent rounded-full w-32 h-32">
                    <Progress.Indicator
                      className="w-full h-full transition-transform duration-300 ease-in-out"
                      style={{
                        background: `conic-gradient(from 0deg, #3b82f6 0deg, #3b82f6 ${recordingProgress * 3.6}deg, transparent ${recordingProgress * 3.6}deg)`,
                        borderRadius: '50%',
                        transform: 'rotate(-90deg)',
                      }}
                    />
                  </Progress.Root>
                </div>
              )}
              
              {/* Record Button */}
              <Tooltip.Root>
                <Tooltip.Trigger asChild>
                  <button
                    onClick={toggleTranscription}
                    disabled={!isConnected}
                    className={cn(
                      'relative w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-4 shadow-xl',
                      isRecording
                        ? 'bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 focus:ring-red-200 recording-pulse'
                        : 'bg-gradient-to-br from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 focus:ring-primary-200'
                    )}
                    aria-label={isRecording ? 'Stop recording' : 'Start recording'}
                    aria-pressed={isRecording}
                  >
                    {isRecording ? (
                      <MicOff className="w-10 h-10 text-white" />
                    ) : (
                      <Mic className="w-10 h-10 text-white" />
                    )}
                  </button>
                </Tooltip.Trigger>
                <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                  {isRecording ? 'Stop Recording' : 'Start Recording'}
                </Tooltip.Content>
              </Tooltip.Root>
            </div>
            
            {/* Recording Duration */}
            {isRecording && (
              <div className="mt-3 flex items-center space-x-2">
                <Clock className="w-4 h-4 text-gray-500" />
                <span className="text-2xl font-mono font-bold text-gray-900">
                  {formatDuration(duration)}
                </span>
              </div>
            )}
          </div>


          {/* Enhanced Audio Level Bars */}
          {isRecording && (
            <div className="flex items-center justify-center space-x-1">
              {audioLevelBars}
            </div>
          )}
          {/* Connection Error - Only show during recording if connection fails */}
          {isRecording && !isConnected && (
            <div className="mt-4 p-3 bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-300 rounded-lg shadow-md">
              <p className="text-sm text-red-700">
                Unable to connect to transcription service. Please check your connection and try again.
              </p>
            </div>
          )}

          {/* Enhanced Recording Stats */}
          {(duration > 0 || audioLevel > 0) && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-3 rounded-xl border-2 border-blue-300 shadow-md hover:shadow-lg transition-all duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-blue-700">
                      {formatDuration(duration)}
                    </div>
                    <div className="text-sm text-blue-600 font-medium">Duration</div>
                  </div>
                  <Clock className="w-8 h-8 text-blue-500" />
                </div>
              </div>

              <div className="bg-gradient-to-br from-green-50 to-green-100 p-3 rounded-xl border-2 border-green-300 shadow-md hover:shadow-lg transition-all duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-green-700">
                      {Math.round(audioLevel * 100)}%
                    </div>
                    <div className="text-sm text-green-600 font-medium">Audio Level</div>
                  </div>
                  <Activity className="w-8 h-8 text-green-500" />
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-3 rounded-xl border-2 border-purple-300 shadow-md hover:shadow-lg transition-all duration-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-purple-700">
                      {isRecording ? 'Live' : 'Ready'}
                    </div>
                    <div className="text-sm text-purple-600 font-medium">Status</div>
                  </div>
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center',
                    isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-400'
                  )}>
                    <div className="w-3 h-3 bg-white rounded-full" />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Tooltip.Provider>
  );
};

export default AudioRecorder;