/**
 * Main Application Component
 * 
 * Root component that manages the overall layout and navigation
 * for the NeuroBridge EDU application.
 */

import React from 'react';
import { Menu, X, Mic, Settings as SettingsIcon, AlertCircle } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import AudioRecorder from '@/components/AudioRecorder';
import TranscriptionDisplay from '@/components/TranscriptionDisplay';
import SummaryEditor from '@/components/SummaryEditor';
import Settings from '@/components/Settings';
import ErrorBoundary from '@/components/ErrorBoundary';
import { cn } from '@/utils/cn';
import NeuroBridgeEDULogo from './logo/NeuroBridgeEDU.jpg';
import { FlickeringGrid } from '@/components/ui/FlickeringGrid';

const App: React.FC = () => {
  // Use selector functions instead of object destructuring for reactive updates
  const activeTab = useAppStore((state) => state.activeTab);
  const sidebarOpen = useAppStore((state) => state.sidebarOpen);
  const errors = useAppStore((state) => state.errors);
  const setActiveTab = useAppStore((state) => state.setActiveTab);
  const toggleSidebar = useAppStore((state) => state.toggleSidebar);
  const clearError = useAppStore((state) => state.clearError);


  const navigationItems = [
    { id: 'record' as const, label: 'Record & Transcribe', icon: Mic },
    { id: 'settings' as const, label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <ErrorBoundary>
      <div className="h-screen bg-gray-50 flex overflow-hidden">
        {/* Sidebar */}
        <div
          className={cn(
            'fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0 flex flex-col h-screen',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
            <div className="flex items-center">
              <h1 className="text-lg font-semibold text-gray-900">
                NeuroBridge EDU
              </h1>
            </div>
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="mt-4 px-3">
            <div className="space-y-1">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={cn(
                      'w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors duration-200',
                      isActive
                        ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-600'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="w-5 h-5 mr-3" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          </nav>

          {/* FlickeringGrid fills the middle space */}
          <div className="flex-1 relative overflow-hidden mt-5">
            <FlickeringGrid 
              squareSize={4}
              gridGap={6}
              color="rgb(96, 165, 250)"
              maxOpacity={0.6}
              flickerChance={0.4}
              className="h-full w-full"
            />
          </div>

          {/* Logo Section - moved down with more spacing */}
          <div className="flex justify-center px-6 py-8 mb-4">
            <div className="logo-container group relative">
              {/* Glow effect behind logo */}
              <div className="absolute inset-0 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 rounded-2xl blur-xl opacity-50 group-hover:opacity-75 transition-opacity duration-500"></div>
              
              {/* Logo with enhanced styling */}
              <div className="relative bg-gradient-to-br from-white to-gray-50 p-3 rounded-2xl shadow-xl border-2 border-gray-200 group-hover:border-purple-300 transition-all duration-300 group-hover:scale-105">
                <img 
                  src={NeuroBridgeEDULogo} 
                  alt="NeuroBridge EDU - Education 4 All" 
                  className="w-40 h-auto object-contain rounded-xl shadow-inner"
                />
              </div>
              
              {/* Decorative elements */}
              <div className="absolute -top-2 -right-2 w-4 h-4 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full animate-pulse"></div>
              <div className="absolute -bottom-2 -left-2 w-3 h-3 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-pulse animation-delay-300"></div>
            </div>
          </div>

          {/* Sidebar footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              AI-Powered Educational Transcription
            </div>
            <div className="text-xs text-gray-400 text-center mt-2">
              Designed & Built by{' '}
              <a 
                href="https://emmi.zone" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700 transition-colors"
              >
                Emmi C.
              </a>
            </div>
          </div>
        </div>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
            onClick={toggleSidebar}
            aria-hidden="true"
          />
        )}

        {/* Main content */}
        <div className="flex-1 lg:ml-0 flex flex-col h-screen">
          {/* Header */}
          <header className="bg-white shadow-sm border-b border-gray-200">
            <div className="flex items-center justify-between h-16 px-6">
              <div className="flex items-center">
                <button
                  onClick={toggleSidebar}
                  className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
                  aria-label="Open sidebar"
                >
                  <Menu className="w-5 h-5" />
                </button>
                <h2 className="ml-4 lg:ml-0 text-xl font-semibold text-gray-900">
                  {navigationItems.find(item => item.id === activeTab)?.label}
                </h2>
              </div>
            </div>
          </header>

          {/* Error notifications */}
          {errors.length > 0 && (
            <div className="bg-red-50 border-l-4 border-red-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                </div>
                <div className="ml-3 flex-1">
                  {errors.map((error, index) => (
                    <div key={error.id || `${error.code}-${error.timestamp}-${index}`} className="flex items-center justify-between">
                      <p className="text-sm text-red-700">{error.message}</p>
                      <button
                        onClick={() => clearError(error.id || error.code)}
                        className="ml-4 text-red-400 hover:text-red-500"
                        aria-label="Dismiss error"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Main content area */}
          <main className="flex-1 overflow-auto min-h-0">
            <div className="max-w-7xl mx-auto py-4 px-6 h-full">
              {activeTab === 'record' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* Recording Section */}
                    <div className="space-y-4">
                      <AudioRecorder />
                      <TranscriptionDisplay />
                    </div>
                    
                    {/* Summary Section */}
                    <div>
                      <SummaryEditor />
                    </div>
                  </div>
                </div>
              )}

              
              {activeTab === 'settings' && <Settings />}
            </div>
          </main>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;