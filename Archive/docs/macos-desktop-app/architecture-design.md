# NeuroBridge EDU - macOS Native App Architecture Specification

## Executive Summary

Based on comprehensive research using Context7 MCP and Perplexity MCP, this document outlines the complete architecture for packaging NeuroBridge EDU as a native macOS application. The recommended approach uses **Electron as the primary host framework** with an embedded Python FastAPI backend, providing optimal balance of development velocity, native integration, and user experience.

## 1. Complete Application Bundle Structure

### 1.1 macOS App Bundle Layout (.app Structure)

```
NeuroBridge EDU.app/
├── Contents/
│   ├── Info.plist                           # App metadata, permissions, URL schemes
│   ├── MacOS/
│   │   └── NeuroBridge EDU                  # Electron main executable
│   ├── Frameworks/                          # Electron framework and native deps
│   │   ├── Electron Framework.framework/
│   │   ├── Python.framework/                # Embedded Python 3.11+ runtime
│   │   └── NeuroBridge EDU Helper.app/      # Required Electron helper
│   └── Resources/
│       ├── app/                             # React frontend build
│       │   ├── index.html
│       │   ├── static/                      # JS, CSS, assets
│       │   └── public/                      # Icons, manifest
│       ├── python/                          # FastAPI backend
│       │   ├── main.py                      # FastAPI entry point
│       │   ├── api/                         # API routes
│       │   ├── services/                    # Business logic
│       │   ├── models/                      # Data models
│       │   └── requirements.txt             # Python dependencies
│       ├── models/                          # AI model files
│       │   ├── whisper-base.bin             # Whisper model weights
│       │   └── manifest.json               # Model metadata & checksums
│       ├── app.icns                         # Application icon
│       └── audio-worklet-processor.js       # Audio processing worker
```

### 1.2 Resource Organization Strategy

**Read-Only Bundle Resources:**
- React frontend assets in `Contents/Resources/app/`
- Python FastAPI application in `Contents/Resources/python/`
- Default AI models in `Contents/Resources/models/`
- Audio processing workers in `Contents/Resources/`

**Writable User Directories:**
- Application data: `~/Library/Application Support/NeuroBridge EDU/`
- User preferences: `~/Library/Preferences/com.neurobridge.edu.plist`
- Temporary files: `~/Library/Caches/NeuroBridge EDU/`
- Updated models: `~/Library/Application Support/NeuroBridge EDU/models/`

## 2. Process Management Architecture

### 2.1 Supervisor Process Pattern

**Electron Main Process (Host/Supervisor):**
```javascript
class BackendSupervisor {
  constructor() {
    this.pythonProcess = null;
    this.serverPort = null;
    this.authToken = null;
    this.healthCheckInterval = null;
    this.restartCount = 0;
    this.maxRestarts = 5;
  }

  async startBackend() {
    // Generate ephemeral port and auth token
    this.serverPort = await this.getFreePort();
    this.authToken = crypto.randomBytes(32).toString('hex');
    
    // Set up Python environment
    const pythonPath = path.join(__dirname, '../Resources/python');
    const env = {
      ...process.env,
      PYTHONPATH: pythonPath,
      SERVER_PORT: this.serverPort,
      AUTH_TOKEN: this.authToken,
      MODEL_PATH: path.join(app.getPath('userData'), 'models'),
      DATABASE_PATH: path.join(app.getPath('userData'), 'neurobridge.db')
    };

    // Spawn FastAPI server
    this.pythonProcess = spawn('python3', [
      path.join(pythonPath, 'main.py')
    ], { env, detached: false });

    // Monitor process health
    this.setupHealthMonitoring();
    this.setupProcessHandlers();
  }

  setupHealthMonitoring() {
    this.healthCheckInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:${this.serverPort}/health`, {
          headers: { 'Authorization': `Bearer ${this.authToken}` },
          timeout: 5000
        });
        if (!response.ok) throw new Error('Health check failed');
      } catch (error) {
        console.error('Backend health check failed:', error);
        this.handleUnhealthyBackend();
      }
    }, 10000);
  }

  async stopBackend() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    
    if (this.pythonProcess) {
      // Graceful shutdown
      this.pythonProcess.kill('SIGTERM');
      
      // Force kill after timeout
      setTimeout(() => {
        if (this.pythonProcess) {
          this.pythonProcess.kill('SIGKILL');
        }
      }, 5000);
    }
  }
}
```

### 2.2 FastAPI Backend Lifecycle

**Python FastAPI Startup:**
```python
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

# Environment configuration
SERVER_PORT = int(os.getenv('SERVER_PORT', 3939))
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
MODEL_PATH = os.getenv('MODEL_PATH')

app = FastAPI(title="NeuroBridge EDU Backend")

# Security middleware
security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    if token.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return token

# CORS configuration for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{SERVER_PORT}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=SERVER_PORT, log_level="info")
```

### 2.3 Process Health Monitoring

**Health Check States:**
- `STARTING`: Backend is initializing
- `HEALTHY`: Backend responding normally
- `DEGRADED`: Intermittent failures detected
- `FAILED`: Backend unresponsive, restart required
- `STOPPING`: Graceful shutdown in progress

**Restart Policy:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s intervals
- Maximum 5 restart attempts per session
- Circuit breaker pattern for repeated failures

## 3. Frontend-Backend Communication Architecture

### 3.1 Communication Layers

**Layer 1: Native IPC (Electron)**
- Window management, file dialogs, system preferences
- Microphone permissions and audio device access
- Native macOS integrations (menu bar, dock, notifications)

**Layer 2: HTTP/WebSocket (FastAPI)**
- Real-time transcription streaming
- AI model operations
- Student management and data export

**Layer 3: Security Token Authentication**
```javascript
// Frontend API client with token authentication
class BackendClient {
  constructor(port, authToken) {
    this.baseURL = `http://127.0.0.1:${port}`;
    this.authToken = authToken;
    this.ws = null;
  }

  async request(endpoint, options = {}) {
    return fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.authToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
  }

  connectWebSocket() {
    this.ws = new WebSocket(`ws://127.0.0.1:${this.port}/ws/transcription`);
    this.ws.onopen = () => {
      this.ws.send(JSON.stringify({
        type: 'auth',
        token: this.authToken
      }));
    };
  }
}
```

### 3.2 Real-Time Audio Streaming

**Audio Pipeline Architecture:**
1. **Capture**: Electron main process captures microphone via native APIs
2. **Chunking**: Audio data chunked into 1-2 second segments
3. **Streaming**: WebSocket connection streams audio chunks to Python backend
4. **Processing**: Whisper model processes chunks with partial results
5. **Response**: Streaming transcription results back to frontend via SSE

```javascript
// Audio capture in Electron main process
class AudioCapture {
  constructor(supervisor) {
    this.supervisor = supervisor;
    this.mediaRecorder = null;
    this.audioContext = null;
  }

  async startCapture() {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    });

    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(stream);
    
    await this.audioContext.audioWorklet.addModule('./audio-worklet-processor.js');
    const processor = new AudioWorkletNode(this.audioContext, 'audio-processor');
    
    processor.port.onmessage = (event) => {
      const audioData = event.data;
      this.sendToBackend(audioData);
    };

    source.connect(processor);
  }

  sendToBackend(audioData) {
    if (this.supervisor.isHealthy()) {
      this.supervisor.sendAudioChunk(audioData);
    }
  }
}
```

## 4. Native macOS Integration

### 4.1 Info.plist Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.neurobridge.edu</string>
    
    <key>CFBundleName</key>
    <string>NeuroBridge EDU</string>
    
    <key>CFBundleDisplayName</key>
    <string>NeuroBridge EDU</string>
    
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.education</string>
    
    <!-- Microphone permission -->
    <key>NSMicrophoneUsageDescription</key>
    <string>NeuroBridge EDU requires microphone access to provide real-time speech transcription for educational content.</string>
    
    <!-- File associations for audio files -->
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key>
            <string>Audio Files</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>mp3</string>
                <string>wav</string>
                <string>m4a</string>
                <string>aac</string>
            </array>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
        </dict>
    </array>
    
    <!-- URL scheme for deep linking -->
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>NeuroBridge EDU Protocol</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>neurobridge</string>
            </array>
        </dict>
    </array>
    
    <!-- App Transport Security -->
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <false/>
        <key>NSExceptionDomains</key>
        <dict>
            <key>api.openai.com</key>
            <dict>
                <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
                <false/>
                <key>NSTemporaryExceptionMinimumTLSVersion</key>
                <string>TLSv1.2</string>
            </dict>
        </dict>
    </dict>
    
    <!-- Graphics switching for Apple Silicon optimization -->
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    
    <!-- Dark mode support -->
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
```

### 4.2 Native Integration APIs

**Menu Bar Integration:**
```javascript
// Electron main process menu setup
const { Menu, app } = require('electron');

const menuTemplate = [
  {
    label: 'NeuroBridge EDU',
    submenu: [
      { role: 'about' },
      { type: 'separator' },
      {
        label: 'Preferences...',
        accelerator: 'CmdOrCtrl+,',
        click: () => showPreferencesWindow()
      },
      { type: 'separator' },
      { role: 'hide' },
      { role: 'hideothers' },
      { role: 'unhide' },
      { type: 'separator' },
      { role: 'quit' }
    ]
  },
  {
    label: 'File',
    submenu: [
      {
        label: 'Import Audio File...',
        accelerator: 'CmdOrCtrl+O',
        click: () => importAudioFile()
      },
      {
        label: 'Export Summary...',
        accelerator: 'CmdOrCtrl+E',
        click: () => exportSummary()
      }
    ]
  },
  {
    label: 'Record',
    submenu: [
      {
        label: 'Start Recording',
        accelerator: 'Space',
        click: () => toggleRecording()
      }
    ]
  }
];

Menu.setApplicationMenu(Menu.buildFromTemplate(menuTemplate));
```

**Dock and Notifications:**
```javascript
// Dock badge and notifications
const { app, Notification } = require('electron');

class NativeIntegration {
  updateTranscriptionStatus(isRecording, wordCount) {
    // Update dock badge with word count
    if (wordCount > 0) {
      app.dock.setBadge(wordCount.toString());
    } else {
      app.dock.setBadge('');
    }

    // Bounce dock when transcription completes
    if (!isRecording && wordCount > 0) {
      app.dock.bounce('informational');
    }
  }

  showNotification(title, body) {
    if (Notification.isSupported()) {
      new Notification({
        title,
        body,
        sound: 'Submarine'
      }).show();
    }
  }

  setProgressBar(progress) {
    // Show progress in dock tile (0.0 to 1.0)
    const windows = BrowserWindow.getAllWindows();
    windows.forEach(win => {
      win.setProgressBar(progress);
    });
  }
}
```

## 5. Resource Management and AI Model Optimization

### 5.1 Whisper Model Management

**Model Loading Strategy:**
```python
import asyncio
from pathlib import Path
import whisper
import torch
from typing import Optional

class ModelManager:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.current_model: Optional[whisper.Whisper] = None
        self.model_size = "base"  # Default model size
        self.device = self._detect_device()
        
    def _detect_device(self):
        if torch.backends.mps.is_available():
            return "mps"  # Apple Silicon Metal Performance Shaders
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    async def load_model(self, model_size: str = "base"):
        """Load Whisper model with Apple Silicon optimization"""
        if self.current_model and self.model_size == model_size:
            return self.current_model
            
        # Unload previous model to free memory
        if self.current_model:
            del self.current_model
            torch.mps.empty_cache() if self.device == "mps" else None
        
        # Load model with optimizations
        model_path = self.model_path / f"whisper-{model_size}.bin"
        
        if model_path.exists():
            # Load from local file
            self.current_model = whisper.load_model(str(model_path), device=self.device)
        else:
            # Download and cache
            self.current_model = whisper.load_model(model_size, device=self.device)
            # Save to local cache
            torch.save(self.current_model.state_dict(), model_path)
        
        self.model_size = model_size
        return self.current_model
    
    async def transcribe_chunk(self, audio_data: bytes) -> dict:
        """Transcribe audio chunk with streaming support"""
        if not self.current_model:
            await self.load_model()
        
        # Convert audio bytes to torch tensor
        audio_tensor = self._bytes_to_tensor(audio_data)
        
        # Transcribe with optimizations
        with torch.no_grad():
            result = self.current_model.transcribe(
                audio_tensor,
                language="en",  # Set default language
                fp16=self.device != "cpu",  # Use FP16 for GPU
                verbose=False
            )
        
        return result
    
    def get_memory_usage(self) -> dict:
        """Return current memory usage statistics"""
        if self.device == "mps":
            return {
                "device": "Apple Silicon (MPS)",
                "allocated": torch.mps.current_allocated_memory(),
                "cached": torch.mps.driver_allocated_memory()
            }
        return {"device": self.device, "allocated": 0, "cached": 0}
```

### 5.2 Memory Management Strategy

**Memory Optimization Patterns:**
1. **Lazy Loading**: Load models only when needed
2. **Memory Pooling**: Reuse audio buffers and tensors
3. **Garbage Collection**: Explicit cleanup after transcription
4. **Memory Monitoring**: Track usage and implement alerts
5. **Chunked Processing**: Stream large files in segments

**Resource Limits Configuration:**
```javascript
// Electron main process memory management
app.commandLine.appendSwitch('--max-old-space-size', '2048'); // 2GB for Node.js
app.commandLine.appendSwitch('--js-flags', '--max-old-space-size=2048');

// Memory monitoring
setInterval(() => {
  const memoryUsage = process.memoryUsage();
  console.log({
    rss: Math.round(memoryUsage.rss / 1024 / 1024),
    heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024),
    heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024)
  });
  
  // Alert if memory usage exceeds threshold
  if (memoryUsage.rss > 1024 * 1024 * 1024 * 3) { // 3GB
    console.warn('High memory usage detected');
    // Implement cleanup or model unloading
  }
}, 30000);
```

## 6. Security and Sandboxing Architecture

### 6.1 App Store Sandbox Configuration

**Entitlements File (entitlements.plist):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Enable App Sandbox -->
    <key>com.apple.security.app-sandbox</key>
    <true/>
    
    <!-- Allow microphone access -->
    <key>com.apple.security.device.microphone</key>
    <true/>
    
    <!-- Allow file access with user selection -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Allow downloads folder access -->
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    
    <!-- Allow network access -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Allow outgoing connections to OpenAI -->
    <key>com.apple.security.network.server</key>
    <false/>
    
    <!-- Application groups for shared data -->
    <key>com.apple.security.application-groups</key>
    <array>
        <string>group.com.neurobridge.edu</string>
    </array>
    
    <!-- Hardened runtime for notarization -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

### 6.2 Security Implementation

**Token-Based Authentication:**
```python
# FastAPI security middleware
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta

class SecurityManager:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.session_tokens = set()
        
    def generate_session_token(self) -> str:
        """Generate time-limited session token"""
        timestamp = int(datetime.utcnow().timestamp())
        nonce = secrets.token_hex(16)
        
        # HMAC-based token
        message = f"{timestamp}:{nonce}"
        signature = hmac.new(
            self.auth_token.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{message}:{signature}"
        self.session_tokens.add(token)
        return token
    
    def verify_token(self, token: str) -> bool:
        """Verify session token validity"""
        try:
            timestamp_str, nonce, signature = token.split(':')
            timestamp = int(timestamp_str)
            
            # Check token age (max 1 hour)
            current_time = int(datetime.utcnow().timestamp())
            if current_time - timestamp > 3600:
                return False
            
            # Verify HMAC signature
            message = f"{timestamp_str}:{nonce}"
            expected_signature = hmac.new(
                self.auth_token.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, AttributeError):
            return False
```

**Content Security Policy:**
```javascript
// Electron renderer security configuration
const { session } = require('electron');

// Set up Content Security Policy
session.defaultSession.webSecurity = true;

const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "media-src 'self' blob:",
  "connect-src 'self' ws://127.0.0.1:* http://127.0.0.1:* https://api.openai.com",
  "font-src 'self'",
  "object-src 'none'",
  "frame-src 'none'"
].join('; ');

session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
  callback({
    responseHeaders: {
      ...details.responseHeaders,
      'Content-Security-Policy': [csp]
    }
  });
});
```

## 7. Packaging and Distribution Strategy

### 7.1 Build Process Architecture

**Electron Builder Configuration:**
```json
{
  "build": {
    "appId": "com.neurobridge.edu",
    "productName": "NeuroBridge EDU",
    "directories": {
      "output": "dist"
    },
    "files": [
      "build/**/*",
      "node_modules/**/*",
      "python/**/*",
      "models/**/*",
      "package.json"
    ],
    "mac": {
      "category": "public.app-category.education",
      "icon": "assets/icon.icns",
      "entitlements": "build/entitlements.plist",
      "entitlementsInherit": "build/entitlements.plist",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "notarize": {
        "teamId": "YOUR_TEAM_ID"
      },
      "target": [
        {
          "target": "dmg",
          "arch": ["x64", "arm64"]
        },
        {
          "target": "mas",
          "arch": ["x64", "arm64"]
        }
      ]
    },
    "dmg": {
      "title": "Install NeuroBridge EDU",
      "icon": "assets/dmg-icon.icns",
      "background": "assets/dmg-background.png",
      "window": {
        "width": 540,
        "height": 380
      },
      "contents": [
        {
          "x": 140,
          "y": 200,
          "type": "file"
        },
        {
          "x": 400,
          "y": 200,
          "type": "link",
          "path": "/Applications"
        }
      ]
    },
    "afterSign": "scripts/notarize.js"
  }
}
```

### 7.2 Code Signing and Notarization

**Automated Signing Script:**
```javascript
// scripts/notarize.js
const { notarize } = require('electron-notarize');

exports.default = async function notarizeApp(context) {
  const { electronPlatformName, appOutDir } = context;
  
  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`Notarizing ${appPath}...`);

  try {
    await notarize({
      appBundleId: 'com.neurobridge.edu',
      appPath: appPath,
      appleId: process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_ID_PASSWORD,
      teamId: process.env.TEAM_ID,
    });
    
    console.log('Notarization completed successfully');
  } catch (error) {
    console.error('Notarization failed:', error);
    throw error;
  }
};
```

### 7.3 Auto-Update Implementation

**Update Architecture:**
```javascript
// Electron main process auto-updater
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');

class UpdateManager {
  constructor() {
    autoUpdater.logger = log;
    autoUpdater.checkForUpdatesAndNotify();
    
    // Check for updates every 30 minutes
    setInterval(() => {
      autoUpdater.checkForUpdatesAndNotify();
    }, 30 * 60 * 1000);
    
    this.setupUpdateHandlers();
  }
  
  setupUpdateHandlers() {
    autoUpdater.on('checking-for-update', () => {
      log.info('Checking for update...');
    });
    
    autoUpdater.on('update-available', (info) => {
      log.info('Update available.');
      this.notifyUserOfUpdate(info);
    });
    
    autoUpdater.on('update-not-available', (info) => {
      log.info('Update not available.');
    });
    
    autoUpdater.on('error', (err) => {
      log.error('Error in auto-updater:', err);
    });
    
    autoUpdater.on('download-progress', (progressObj) => {
      const logMessage = `Download speed: ${progressObj.bytesPerSecond} - Downloaded ${progressObj.percent}% (${progressObj.transferred}/${progressObj.total})`;
      log.info(logMessage);
      this.updateDownloadProgress(progressObj.percent);
    });
    
    autoUpdater.on('update-downloaded', (info) => {
      log.info('Update downloaded');
      this.promptUserToRestart();
    });
  }
  
  notifyUserOfUpdate(updateInfo) {
    const { dialog } = require('electron');
    dialog.showMessageBox({
      type: 'info',
      title: 'Update Available',
      message: `Version ${updateInfo.version} is available. It will be downloaded in the background.`,
      buttons: ['OK']
    });
  }
  
  promptUserToRestart() {
    const { dialog } = require('electron');
    const buttonIndex = dialog.showMessageBoxSync({
      type: 'info',
      title: 'Update Ready',
      message: 'Update downloaded. The application will restart to apply the update.',
      buttons: ['Restart Now', 'Later']
    });
    
    if (buttonIndex === 0) {
      autoUpdater.quitAndInstall();
    }
  }
}
```

## 8. Deployment and Operations

### 8.1 CI/CD Pipeline Architecture

**GitHub Actions Build Pipeline:**
```yaml
name: Build and Release macOS App

on:
  push:
    tags:
      - 'v*'

jobs:
  build-mac:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        npm install
        pip install -r python/requirements.txt
    
    - name: Build React frontend
      run: |
        npm run build
    
    - name: Package Python backend
      run: |
        pip install pyinstaller
        pyinstaller --onedir --hidden-import=uvicorn python/main.py
    
    - name: Prepare certificates
      env:
        CERTIFICATE_OSX_APPLICATION: ${{ secrets.CERTIFICATE_OSX_APPLICATION }}
        CERTIFICATE_PASSWORD: ${{ secrets.CERTIFICATE_PASSWORD }}
      run: |
        echo $CERTIFICATE_OSX_APPLICATION | base64 --decode > certificate.p12
        security create-keychain -p "$CERTIFICATE_PASSWORD" build.keychain
        security default-keychain -s build.keychain
        security unlock-keychain -p "$CERTIFICATE_PASSWORD" build.keychain
        security import certificate.p12 -k build.keychain -P "$CERTIFICATE_PASSWORD" -T /usr/bin/codesign
        security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$CERTIFICATE_PASSWORD" build.keychain
    
    - name: Build Electron app
      env:
        APPLE_ID: ${{ secrets.APPLE_ID }}
        APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
        TEAM_ID: ${{ secrets.TEAM_ID }}
      run: |
        npm run build:mac
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: mac-app
        path: dist/*.dmg
```

### 8.2 Error Handling and Diagnostics

**Comprehensive Logging System:**
```javascript
// Centralized logging system
const log = require('electron-log');
const path = require('path');
const { app } = require('electron');

class DiagnosticsManager {
  constructor() {
    this.setupLogging();
    this.setupCrashReporter();
    this.setupPerformanceMonitoring();
  }
  
  setupLogging() {
    // Configure log levels and transports
    log.transports.file.level = 'info';
    log.transports.file.maxSize = 10 * 1024 * 1024; // 10MB
    log.transports.file.file = path.join(app.getPath('userData'), 'app.log');
    
    // Console logging for development
    log.transports.console.level = 'debug';
    
    // Custom format
    log.transports.file.format = '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}';
  }
  
  setupCrashReporter() {
    const { crashReporter } = require('electron');
    
    crashReporter.start({
      productName: 'NeuroBridge EDU',
      companyName: 'NeuroBridge',
      submitURL: 'https://your-crash-server.com/submit',
      uploadToServer: false, // Set to true for production
      extra: {
        version: app.getVersion(),
        platform: process.platform,
        arch: process.arch
      }
    });
  }
  
  setupPerformanceMonitoring() {
    const { powerMonitor } = require('electron');
    
    powerMonitor.on('suspend', () => {
      log.info('System suspended - pausing background tasks');
      // Pause intensive operations
    });
    
    powerMonitor.on('resume', () => {
      log.info('System resumed - resuming background tasks');
      // Resume operations
    });
    
    // Memory monitoring
    setInterval(() => {
      const memoryUsage = process.memoryUsage();
      const cpuUsage = process.cpuUsage();
      
      log.debug('Performance metrics:', {
        memory: {
          rss: Math.round(memoryUsage.rss / 1024 / 1024) + 'MB',
          heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024) + 'MB'
        },
        cpu: {
          user: cpuUsage.user,
          system: cpuUsage.system
        }
      });
    }, 60000);
  }
  
  collectDiagnostics() {
    return {
      app: {
        version: app.getVersion(),
        name: app.getName(),
        locale: app.getLocale()
      },
      system: {
        platform: process.platform,
        arch: process.arch,
        version: process.getSystemVersion(),
        memory: process.memoryUsage(),
        uptime: process.uptime()
      },
      gpu: app.getGPUFeatureStatus(),
      displays: require('electron').screen.getAllDisplays()
    };
  }
}
```

## 9. Recommended Architecture Summary

Based on comprehensive research and analysis, **the recommended architecture for NeuroBridge EDU is Electron-based** with the following key components:

### 9.1 Technology Stack
- **Host Framework**: Electron 28+ for mature macOS integration
- **Frontend**: React 18+ with existing Vite build system
- **Backend**: FastAPI with embedded Python 3.11+ runtime
- **AI Models**: Whisper with Apple Silicon optimization (Metal Performance Shaders)
- **Communication**: HTTP/WebSocket with token authentication
- **Packaging**: electron-builder with code signing and notarization

### 9.2 Key Advantages
1. **Proven Integration**: Battle-tested patterns for hybrid web/native apps
2. **Development Velocity**: Reuses existing React frontend with minimal changes
3. **Native Experience**: Full access to macOS APIs, menus, notifications, file handling
4. **Security**: Comprehensive sandboxing and code signing support
5. **Distribution**: Supports both direct distribution (DMG) and Mac App Store
6. **Maintainability**: Clear separation of concerns with supervised backend processes

### 9.3 Performance Characteristics
- **Memory Usage**: ~150-200MB base Electron overhead + Python runtime + models
- **Startup Time**: <3 seconds for typical configurations
- **Bundle Size**: ~200-300MB depending on included models
- **Update Size**: Differential updates minimize download size

This architecture provides the optimal balance of development efficiency, user experience, and technical robustness for packaging NeuroBridge EDU as a professional macOS application.