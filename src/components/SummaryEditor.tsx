/**
 * Summary Editor Component
 * 
 * Provides functionality to generate AI summaries from transcription text,
 * edit the generated content, and save summaries for later use.
 */

import React, { useState, useRef } from 'react';
import { Brain, FileText, Loader, Sparkles, BarChart3, CheckCircle } from 'lucide-react';
import { VictoryPie } from 'victory';
import * as Tooltip from '@radix-ui/react-tooltip';
import * as Separator from '@radix-ui/react-separator';
import ReactMarkdown from 'react-markdown';
import { useAppStore } from '@/stores/appStore';
import { cn } from '@/utils/cn';
import TetrisLoading from './ui/TetrisLoading';

// Import PNG icons
import EditIcon from '@/icons/EDIT.png';
import PDFIcon from '@/icons/PDF.png';
import MDIcon from '@/icons/MD.png';

const SummaryEditor: React.FC = () => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Use selector functions instead of object destructuring for reactive updates
  const transcriptionText = useAppStore((state) => state.transcriptionText);
  const summaryContent = useAppStore((state) => state.summaryContent);
  const isGeneratingSummary = useAppStore((state) => state.isGeneratingSummary);
  const generateSummary = useAppStore((state) => state.generateSummary);

  // Start editing mode
  const startEditing = () => {
    setIsEditing(true);
    setEditedContent(summaryContent);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  // Save edited content
  const saveEdits = () => {
    useAppStore.getState().updateTranscription(''); // Clear to trigger summary update
    useAppStore.setState({ summaryContent: editedContent });
    setIsEditing(false);
  };

  // Cancel editing
  const cancelEditing = () => {
    setIsEditing(false);
    setEditedContent('');
  };

  // Handle summary generation
  const handleGenerateSummary = async () => {
    if (!transcriptionText.trim()) return;
    await generateSummary();
  };


  // Export summary as PDF using backend API
  const exportAsPDF = async () => {
    const content = isEditing ? editedContent : summaryContent;
    const currentSummary = useAppStore.getState().currentSummary;
    
    if (!content.trim() || !currentSummary) return;

    try {
      const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
      const response = await fetch(`${API_BASE_URL}/api/summaries/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: currentSummary.title || 'Summary',
          content: content,
          format: 'pdf'
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to export PDF');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `summary-${timestamp}.pdf`;
      
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export PDF:', error);
      useAppStore.getState().addError({
        code: 'EXPORT_ERROR',
        message: 'Failed to export summary as PDF. PDF export is not yet implemented - please use Markdown format.',
        timestamp: new Date().toISOString()
      });
    }
  };

  // Export summary as Markdown using backend API
  const exportAsMarkdown = async () => {
    const content = isEditing ? editedContent : summaryContent;
    const currentSummary = useAppStore.getState().currentSummary;
    
    if (!content.trim() || !currentSummary) return;

    try {
      const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:3939';
      const response = await fetch(`${API_BASE_URL}/api/summaries/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: currentSummary.title || 'Summary',
          content: content,
          format: 'markdown'
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to export Markdown');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `summary-${timestamp}.md`;
      
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export Markdown:', error);
      useAppStore.getState().addError({
        code: 'EXPORT_ERROR',
        message: 'Failed to export summary as Markdown',
        timestamp: new Date().toISOString()
      });
    }
  };



  const hasTranscription = transcriptionText && transcriptionText.length > 0;
  const hasSummary = summaryContent && summaryContent.length > 0;
  const canGenerate = hasTranscription && !isGeneratingSummary;

  // Calculate summary metrics - only if we have both transcript and summary
  const summaryStats = (hasSummary && hasTranscription) ? {
    originalWords: transcriptionText.split(/\s+/).filter(word => word.length > 0).length,
    summaryWords: summaryContent.split(/\s+/).filter(word => word.length > 0).length,
    compressionRatio: 0,
  } : null;

  if (summaryStats && summaryStats.originalWords > 0 && summaryStats.summaryWords > 0) {
    // Calculate compression ratio
    if (summaryStats.summaryWords < summaryStats.originalWords) {
      // Summary is shorter - show compression percentage
      summaryStats.compressionRatio = Math.round((1 - summaryStats.summaryWords / summaryStats.originalWords) * 100);
    } else if (summaryStats.summaryWords > summaryStats.originalWords) {
      // Summary is longer - show expansion as negative (will display differently)
      summaryStats.compressionRatio = -Math.round((summaryStats.summaryWords / summaryStats.originalWords - 1) * 100);
    } else {
      // Same length
      summaryStats.compressionRatio = 0;
    }
  }

  return (
    <Tooltip.Provider>
      <div className="card-accent h-full flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">AI Summary</h3>
              <p className="text-sm text-gray-500">OpenAI-powered content summarization</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Summary Quality Indicator */}
            {hasSummary && summaryStats && (
              <Tooltip.Root>
                <Tooltip.Trigger asChild>
                  <div className={`flex items-center px-3 py-1.5 rounded-full ${
                    summaryStats.compressionRatio >= 0 ? 'bg-green-100' : 'bg-yellow-100'
                  }`}>
                    <CheckCircle className={`w-3 h-3 mr-1 ${
                      summaryStats.compressionRatio >= 0 ? 'text-green-600' : 'text-yellow-600'
                    }`} />
                    <span className={`text-sm font-medium ${
                      summaryStats.compressionRatio >= 0 ? 'text-green-700' : 'text-yellow-700'
                    }`}>
                      {Math.abs(summaryStats.compressionRatio)}% {summaryStats.compressionRatio >= 0 ? 'compressed' : 'expanded'}
                    </span>
                  </div>
                </Tooltip.Trigger>
                <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                  {summaryStats.compressionRatio >= 0 ? 'Summary compression ratio' : 'Summary expanded from original'}
                </Tooltip.Content>
              </Tooltip.Root>
            )}

            {/* Generate Summary Button */}
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={handleGenerateSummary}
                  disabled={!canGenerate}
                  className={cn(
                    'flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 shadow-sm',
                    canGenerate
                      ? 'bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white shadow-lg'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  )}
                  aria-label="Generate AI summary"
                >
                  {isGeneratingSummary ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  <span>
                    {isGeneratingSummary ? 'Generating...' : 'Generate Summary'}
                  </span>
                </button>
              </Tooltip.Trigger>
              <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                Create AI-powered summary
              </Tooltip.Content>
            </Tooltip.Root>
          </div>
        </div>

        {/* Summary Content Area */}
        <div className="flex-1 flex flex-col">
          {isGeneratingSummary ? (
            // Show Tetris loader while generating
            <div className="flex-1 flex items-center justify-center p-8">
              <TetrisLoading 
                size="md" 
                speed="normal" 
                showLoadingText={true}
                loadingText="NeuroBridgeEDU is thinking..."
              />
            </div>
          ) : hasSummary ? (
            <div className="flex-1 flex flex-col">
              {/* Enhanced Action Bar */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-green-100 to-green-200 rounded-lg flex items-center justify-center">
                      <FileText className="w-4 h-4 text-green-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {isEditing ? 'Editing Summary' : 'Generated Summary'}
                    </span>
                  </div>
                  
                  {/* Summary Stats */}
                  {summaryStats && (
                    <div className="flex items-center space-x-3">
                      <Separator.Root orientation="vertical" className="h-4 w-px bg-gray-300" />
                      <div className="text-xs text-gray-500">
                        {summaryStats.summaryWords} words (from {summaryStats.originalWords})
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="flex items-center space-x-2">
                  {!isEditing ? (
                    <>
                      <Tooltip.Root>
                        <Tooltip.Trigger asChild>
                          <button
                            onClick={startEditing}
                            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                            aria-label="Edit summary"
                          >
                            <img src={EditIcon} alt="Edit" className="w-7 h-7" />
                          </button>
                        </Tooltip.Trigger>
                        <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                          Edit summary
                        </Tooltip.Content>
                      </Tooltip.Root>
                      
                      <Tooltip.Root>
                        <Tooltip.Trigger asChild>
                          <button
                            onClick={exportAsPDF}
                            className="p-2 rounded-lg hover:bg-red-50 transition-colors"
                            aria-label="Save as PDF"
                          >
                            <img src={PDFIcon} alt="PDF" className="w-7 h-7" />
                          </button>
                        </Tooltip.Trigger>
                        <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                          Save as PDF
                        </Tooltip.Content>
                      </Tooltip.Root>
                      
                      <Tooltip.Root>
                        <Tooltip.Trigger asChild>
                          <button
                            onClick={exportAsMarkdown}
                            className="p-2 rounded-lg hover:bg-blue-50 transition-colors"
                            aria-label="Save as Markdown"
                          >
                            <img src={MDIcon} alt="Markdown" className="w-7 h-7" />
                          </button>
                        </Tooltip.Trigger>
                        <Tooltip.Content className="bg-gray-900 text-white px-2 py-1 rounded text-xs">
                          Save as Markdown
                        </Tooltip.Content>
                      </Tooltip.Root>
                      
                    </>
                  ) : (
                    <>
                      <button
                        onClick={saveEdits}
                        className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors font-medium"
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Enhanced Summary Display */}
              <div className="flex-1 flex flex-col gap-6">
                {/* Summary Text - Fixed height with scroll */}
                <div className="flex-1">
                  {isEditing ? (
                    <textarea
                      ref={textareaRef}
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="w-full h-96 p-4 border border-gray-300 rounded-xl resize-none focus:ring-primary-500 focus:border-primary-500 transition-colors"
                      placeholder="Edit your summary here..."
                      aria-label="Edit summary content"
                    />
                  ) : (
                    <div className="h-96 p-6 bg-gradient-to-br from-gray-50 to-white border border-gray-200 rounded-xl shadow-sm overflow-auto">
                      <div className="prose prose-sm prose-gray max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-ul:text-gray-700 prose-ol:text-gray-700 prose-li:text-gray-700">
                        <ReactMarkdown
                          components={{
                            h1: ({children}) => <h1 className="text-2xl font-bold mb-4 text-gray-900">{children}</h1>,
                            h2: ({children}) => <h2 className="text-xl font-semibold mb-3 mt-6 text-gray-800">{children}</h2>,
                            h3: ({children}) => <h3 className="text-lg font-medium mb-2 mt-4 text-gray-800">{children}</h3>,
                            p: ({children}) => <p className="mb-4 text-gray-700 leading-relaxed">{children}</p>,
                            ul: ({children}) => <ul className="list-disc pl-5 mb-4 space-y-2">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-5 mb-4 space-y-2">{children}</ol>,
                            li: ({children}) => <li className="text-gray-700">{children}</li>,
                            strong: ({children}) => <strong className="font-semibold text-gray-900">{children}</strong>,
                            em: ({children}) => <em className="italic">{children}</em>,
                            blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 my-4 italic text-gray-600">{children}</blockquote>,
                            code: ({children, className}) => {
                              const isInline = !className?.includes('language-');
                              return isInline 
                                ? <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>
                                : <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto"><code className="text-sm font-mono">{children}</code></pre>;
                            },
                            hr: () => <hr className="my-6 border-gray-200" />,
                          }}
                        >
                          {summaryContent}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>

                {/* Summary Analytics - Show when we have both transcript and summary */}
                {!isEditing && summaryStats && (
                  <div className="flex flex-col lg:flex-row gap-4">
                    {/* Compression Visualization */}
                    <div className="flex-1 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-medium text-gray-700 flex items-center">
                          <BarChart3 className="w-4 h-4 mr-2" />
                          Compression Analysis
                        </h4>
                      </div>
                      <div className="flex items-center justify-center">
                        <div className="h-32">
                          <VictoryPie
                            data={
                              summaryStats.compressionRatio >= 0 
                                ? [
                                    { x: 'Summary', y: summaryStats.summaryWords },
                                    { x: 'Reduced', y: summaryStats.originalWords - summaryStats.summaryWords }
                                  ]
                                : [
                                    { x: 'Original', y: summaryStats.originalWords },
                                    { x: 'Added', y: summaryStats.summaryWords - summaryStats.originalWords }
                                  ]
                            }
                            innerRadius={40}
                            colorScale={summaryStats.compressionRatio >= 0 ? ['#3b82f6', '#e5e7eb'] : ['#8b5cf6', '#fde68a']}
                            labelComponent={<></>}
                            width={200}
                            height={130}
                            padding={20}
                          />
                        </div>
                        <div className="text-center ml-8">
                          <div className="text-3xl font-bold text-primary-600">
                            {Math.abs(summaryStats.compressionRatio)}%
                          </div>
                          <div className="text-sm text-gray-500">
                            {summaryStats.compressionRatio >= 0 ? 'Compression achieved' : 'Expansion occurred'}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex gap-3">
                      <div className="bg-gradient-to-br from-blue-50 to-blue-100 px-3 py-2 rounded-lg border border-blue-200 min-w-[90px] flex flex-col items-center justify-center">
                        <div className="text-xl font-bold text-blue-700 leading-tight">
                          {summaryStats.originalWords}
                        </div>
                        <div className="text-xs text-blue-600 font-medium mt-0.5">Original</div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-purple-50 to-purple-100 px-3 py-2 rounded-lg border border-purple-200 min-w-[90px] flex flex-col items-center justify-center">
                        <div className="text-xl font-bold text-purple-700 leading-tight">
                          {summaryStats.summaryWords}
                        </div>
                        <div className="text-xs text-purple-600 font-medium mt-0.5">Summary</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

          </div>
        ) : (
          // Empty State
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Brain className="w-8 h-8 text-gray-400" />
              </div>
              <h4 className="text-lg font-medium text-gray-900 mb-2">
                Ready to Generate Summary
              </h4>
              <p className="text-gray-600 max-w-sm mx-auto mb-6">
                {hasTranscription 
                  ? "Click 'Generate Summary' to create an AI-powered summary of your transcription."
                  : "Start recording to capture speech, then generate an AI summary of the content."
                }
              </p>
              
              {hasTranscription && (
                <div className="text-sm text-gray-500">
                  <span className="font-medium">
                    {(transcriptionText || '').split(/\s+/).filter(word => word.length > 0).length} words
                  </span>
                  {' '}ready for summarization
                </div>
              )}
            </div>
          </div>
        )}
        </div>
      </div>
    </Tooltip.Provider>
  );
};

export default SummaryEditor;