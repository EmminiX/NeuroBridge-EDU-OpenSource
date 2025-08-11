# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
NeuroBridge EDU is an open source real-time speech transcription and AI-powered summarization platform for educational content. It features a React frontend with a Python FastAPI backend, providing live audio transcription using OpenAI Whisper and intelligent summary generation with GPT-4.1.

**Architecture**: React + TypeScript frontend with Python FastAPI backend. The application operates statelessly - summaries are generated on-demand and can be exported, but are NOT persisted in the database.

**Key Change**: This is the open source version with all student management features removed and replaced with secure user-configurable API key management.

## Development Commands

### Backend (Python FastAPI - Primary)
```bash
# Start Python backend
cd python_backend && python -m uvicorn main:app --host 0.0.0.0 --port 3939 --reload

# Install Python dependencies
cd python_backend && pip install -r requirements.txt

# For lightweight development (without PyTorch/local Whisper):
cd python_backend && pip install -r requirements-dev.txt

# Run comprehensive test suite (uses run_tests.py custom runner)
cd python_backend && python run_tests.py --suite all --coverage --verbose

# Run specific test suites
cd python_backend && python run_tests.py --suite unit
cd python_backend && python run_tests.py --suite integration
cd python_backend && python run_tests.py --suite security
cd python_backend && python run_tests.py --suite performance
cd python_backend && python run_tests.py --suite quick  # Fast smoke tests

# Test runner options
cd python_backend && python run_tests.py --suite unit --parallel  # Parallel execution
cd python_backend && python run_tests.py --suite all --report     # HTML test report
cd python_backend && python run_tests.py --markers               # Show test markers

# Database migration (automatic on startup, manual if needed)
cd python_backend && python migrations/clean_student_schema.py --dry-run
cd python_backend && python migrations/clean_student_schema.py
```

### Frontend (React + Vite)
```bash
# Start frontend development server
npm run dev:frontend        # Runs on http://localhost:3131

# Build for production
npm run build

# Preview production build
npm run preview

# Test specific component
npm run test -- --testNamePattern="Settings"
npm run test:watch
```

### Code Quality
```bash
# TypeScript compilation check
npx tsc --noEmit

# ESLint with security checks
npm run lint
npm run lint:fix

# Build frontend (includes TypeScript checking)
npm run build
```

### Docker Deployment
```bash
# Standard CPU deployment with local Whisper (base model)
npm run docker:compose

# GPU deployment with CUDA acceleration (requires nvidia-docker2)
docker-compose -f docker-compose.gpu.yml up -d --build

# Development mode with hot reload
npm run docker:compose:dev

# View logs, stop, clean up
npm run docker:logs
npm run docker:stop
npm run docker:clean
```

## System Architecture

### Backend Architecture (Python FastAPI)
The backend follows a layered architecture with secure API key management:

```
python_backend/
├── main.py                 # FastAPI app entry point with lifespan management
├── config.py               # Environment configuration (OpenAI API key now optional)
├── api/                    # API route handlers by domain
│   ├── api_keys.py        # NEW: Secure API key management endpoints
│   ├── transcription/     # Real-time audio transcription endpoints
│   └── summaries/         # Generate + export only (no database storage)
├── services/              # Business logic layer
│   ├── api_key_manager.py # NEW: Encrypted API key storage and management
│   ├── openai/           # OpenAI integration with dynamic API key support
│   ├── whisper/          # Audio transcription session management
│   └── audio/            # Audio processing and analysis
├── models/               # Data models and schemas
│   ├── database/         # Clean database schema (no student tables)
│   └── schemas/          # Pydantic request/response schemas
├── migrations/           # Database migration system for open source conversion
└── tests/               # Comprehensive test suite (unit, integration, security)
```

**Key Components:**
- **API Key Management**: AES-256-GCM encrypted storage with secure key derivation
- **Local Whisper Processing**: faster-whisper with GPU/CPU support and multiple model sizes
- **Hybrid Transcription**: Local-first processing with OpenAI API fallback
- **Audio Pipeline**: Custom AudioWorklet with real-time chunked processing
- **Session Management**: Real-time audio chunking and transcription sessions
- **OpenAI Integration**: Dynamic API key usage from user-provided encrypted storage
- **Stateless Summary Generation**: On-demand generation without database persistence
- **Database Migration**: Automatic migration from previous version to clean schema

### Frontend Architecture (React + TypeScript)
Modern React architecture with secure API key management:

```
src/
├── stores/appStore.ts      # Zustand state with API key management (no student state)
├── hooks/                  # Custom React hooks
│   ├── useAudioRecorder.ts    # Audio capture and processing
│   ├── useHttpTranscription.ts # HTTP + SSE transcription client
│   └── useTranscription.ts    # Transcription orchestration
├── components/             # React components by feature
│   ├── Settings.tsx           # NEW: Secure API key management UI
│   ├── AudioRecorder.tsx      # Real-time audio recording UI
│   ├── TranscriptionDisplay.tsx # Live transcription display
│   ├── SummaryEditor.tsx      # AI summary generation (send features removed)
│   └── ui/                    # Reusable UI components (Radix UI based)
└── utils/                  # Shared utilities and API clients
```

**Navigation**: Two tabs - "Record & Transcribe" and "Settings" (replaces Students tab).

**Key Features:**
- **Secure API Key Management**: React Hook Form with encrypted backend storage
- **Real-time Audio Processing**: WebAudio API with custom AudioWorklet
- **Live Transcription**: HTTP chunked upload with SSE streaming
- **Stateless Operation**: No summary storage, direct export functionality
- **Privacy-Focused**: No user data collection or persistent storage

### Audio Processing Pipeline
1. **Audio Capture**: WebAudio API captures microphone input
2. **Audio Worklet**: Custom processor (`public/audio-worklet-processor.js`)
3. **Chunked Upload**: Audio sent via HTTP to `/api/transcription/chunk`
4. **Whisper Processing**: Backend processes with user's OpenAI API key
5. **SSE Streaming**: Real-time results via Server-Sent Events
6. **State Updates**: Frontend updates transcription display live

### API Key Management Architecture
- **Frontend**: Secure form with validation, masked display, test functionality
- **Backend**: AES-256-GCM encryption with HKDF key derivation
- **Storage**: Local encrypted files in `~/.neurobridge/` with secure permissions
- **Security**: Memory-safe operations, duplicate prevention, audit logging

## State Management
Zustand with Immer middleware for centralized state:

**Core State Domains:**
- **Recording**: `isRecording`, `audioLevel`, `recordingDuration`
- **Transcription**: `transcriptionText`, `isTranscribing`, `sessionId`
- **Summary**: `summaryContent`, `isGeneratingSummary`, `currentSummary`
- **API Keys**: `apiKeys`, `validationStatuses` (NEW)
- **UI**: `activeTab` ('record' | 'settings'), `sidebarOpen`, `errors`

**Important**: Use state selectors: `const transcriptionText = useAppStore((state) => state.transcriptionText)`

## API Endpoints

### API Key Management
- `POST /api/api-keys/store` - Store encrypted API key
- `GET /api/api-keys/list` - List key metadata (no plaintext)
- `POST /api/api-keys/validate/{id}` - Test API key with provider
- `DELETE /api/api-keys/delete/{id}` - Delete stored key

### Transcription Endpoints
- `POST /api/transcription/start` - Start transcription session
- `POST /api/transcription/chunk` - Upload audio chunk
- `GET /api/transcription/stream/{sessionId}` - SSE stream for results
- `POST /api/transcription/stop` - End transcription session
- `GET /api/transcription/config` - Get transcription configuration
- `POST /api/transcription/config` - Update transcription settings
- `POST /api/transcription/test-local` - Test local Whisper capability

### Summary Endpoints (Stateless)
- `POST /api/summaries/generate` - Generate summary without database storage
- `POST /api/summaries/export` - Export summary as PDF/Markdown

### System Endpoints
- `GET /health` - Health check and service status

## Environment Configuration
Copy `.env.example` to `.env`:

```bash
# Core settings
HOST=0.0.0.0
PORT=3939
LOG_LEVEL=INFO
VITE_API_BASE_URL=http://localhost:3939

# AI Services (OPTIONAL - can be set via Settings UI)
# OPENAI_API_KEY=sk-your-key-here

# Local Whisper Configuration (NEW)
LOCAL_WHISPER_ENABLED=true
LOCAL_WHISPER_MODEL_SIZE=base  # tiny|base|small|medium|large-v2|large-v3
LOCAL_WHISPER_DEVICE=auto      # auto|cpu|cuda|mps
TRANSCRIPTION_METHOD=local_first  # local_only|api_only|local_first|auto

# Database (minimal - no summaries stored)
DATABASE_PATH=../data/neurobridge.db

# Security
JWT_SECRET=your-secure-jwt-secret
CORS_ORIGINS=http://localhost:3131,http://localhost:3939
```

**Important Configuration Notes:**
- **OpenAI API key**: Can be configured through Settings UI, eliminating need for environment variables
- **Local Whisper**: Works without any API key - transcription is completely local and private
- **Hybrid Mode**: `local_first` provides best reliability (local with API fallback)
- **Model Selection**: `base` offers best balance of speed/accuracy for most users

### Development vs Production Dependencies

**For Development** (lightweight, API-only transcription):
```bash
cd python_backend && pip install -r requirements-dev.txt
```
- Excludes PyTorch, faster-whisper, and heavy ML dependencies
- Application automatically falls back to OpenAI API for transcription
- Faster installation and startup for development

**For Production** (full local Whisper support):
```bash
cd python_backend && pip install -r requirements.txt
```
- Includes all ML dependencies for local Whisper processing
- Enables hybrid local/API transcription with 90% cost reduction
- Required for Docker containers and full-feature deployment

## Critical Implementation Details

### Secure API Key Management
User-provided OpenAI API keys are stored with AES-256-GCM encryption:

```typescript
// Frontend: Secure form submission
const addApiKey = async (keyData: ApiKeyCreateRequest) => {
  const response = await fetch('/api/api-keys/store', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(keyData)
  });
  // Key is encrypted before storage, never stored in plaintext
};

// Backend handles encryption automatically
// Keys displayed as: sk-••••••••••••••••••••1a2b (last 4 chars only)
```

### Stateless Summary Architecture
Summaries generated on-demand without database persistence:

```typescript
// Generate summary using user's API key
const generateSummary = async () => {
  const response = await fetch('/api/summaries/generate', {
    method: 'POST',
    body: JSON.stringify({
      transcript: transcriptionText
      // Backend automatically uses user's stored API key
    })
  });
};

// Export summary from current data
const exportSummary = async () => {
  const response = await fetch('/api/summaries/export', {
    method: 'POST',
    body: JSON.stringify({
      title: currentSummary.title,
      content: currentSummary.content,
      transcript: transcriptionText,
      format: 'markdown'
    })
  });
};
```

### Error Handling Patterns
Always use defensive programming for undefined data:

```typescript
// Good: Defensive checks
const hasTranscription = transcriptionText && transcriptionText.length > 0;
const summaryWords = (summaryContent || '').split(/\s+/).filter(word => word.length > 0).length;

// Bad: Direct access without checks
const hasTranscription = transcriptionText.length > 0; // Can crash
```

### Database Migration System
Automatic migration from previous version with student management:

```python
# Migration runs automatically on startup
# Manual execution if needed:
python migrations/clean_student_schema.py --dry-run  # Test migration
python migrations/clean_student_schema.py           # Execute migration
python migrations/verify_clean_schema.py            # Verify clean state
```

## Database Schema (Clean)
Minimal SQLite database for core functionality:
- **transcription_sessions**: Session tracking
- **app_settings**: Application configuration
- **api_usage**: Usage tracking (optional)

**Removed**: All student management tables (students, send_logs) have been completely removed.

## Testing Strategy
Comprehensive test suite with multiple categories:

```bash
# Backend testing (comprehensive suite available)
cd python_backend && python run_tests.py --suite all --coverage
cd python_backend && python run_tests.py --suite unit --verbose
cd python_backend && python run_tests.py --suite security
cd python_backend && python run_tests.py --suite integration

# Frontend testing (basic)
npm run test              # Run all tests
npm run test:watch        # Watch mode
npm run build             # TypeScript compilation check
```

**Test Categories**:
- **Unit Tests**: API key management, OpenAI integration, core functionality
- **Integration Tests**: End-to-end workflows, API key → transcription → summary
- **Security Tests**: Encryption/decryption, memory safety, validation
- **Migration Tests**: Database schema migration and cleanup verification

## Code Management Guidelines
- **Open Source Focus**: All proprietary features (student management) removed
- **Security-First**: Never store sensitive data in plaintext
- **Stateless Design**: No user data persistence beyond API key storage
- **Defensive Programming**: Always check for null/undefined values
- **Privacy-Focused**: No data collection or external reporting

## Audio Processing Details
Real-time audio pipeline with WebAudio API:
- **Audio Worklet**: `public/audio-worklet-processor.js` - Custom real-time processor
- **Chunked Upload**: Manageable HTTP chunks to `/api/transcription/chunk`
- **Session Management**: Python backend tracks sessions with unique IDs
- **SSE Streaming**: Real-time results via Server-Sent Events
- **Error Recovery**: Robust handling of network/device issues

## Development Workflow
- **Port Configuration**: Frontend (3131), backend (3939)
- **Environment Setup**: Copy `.env.example`, configure via Settings UI
- **API Key Management**: Use Settings page, never hardcode keys
- **State Management**: Zustand selectors, avoid direct mutation
- **Security**: All API keys encrypted, no browser storage of sensitive data

## Local Whisper Integration
NeuroBridge EDU features hybrid transcription with local Whisper models:

### Transcription Methods
- **`local_only`**: Use only local Whisper (fastest, most private)
- **`api_only`**: Use only OpenAI API (requires API key)
- **`local_first`**: Try local first, fallback to API (recommended)
- **`auto`**: Automatically choose optimal method

### Model Selection Guide
| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | 39MB | ~32x faster | Good | Testing, resource-constrained |
| `base` | 74MB | ~16x faster | Better | **Default choice** |
| `small` | 244MB | ~6x faster | Very good | Production quality |
| `medium` | 769MB | ~2x faster | Excellent | High accuracy needed |
| `large-v3` | 1.5GB | 1x | Best | Maximum quality |

### Performance Features
- **GPU Acceleration**: CUDA support with automatic CPU fallback
- **Model Caching**: Persistent model storage in `~/.cache/whisper/`
- **Real-time Processing**: Sub-second local processing with live updates
- **Cost Reduction**: 90% reduction in API usage compared to cloud-only

### Configuration Management
- **Runtime Configuration**: Use Settings UI to switch methods without restart
- **Environment Variables**: Default settings for deployment
- **Performance Monitoring**: Track success rates and processing times
- **Testing Endpoint**: `/api/transcription/test-local` for capability testing