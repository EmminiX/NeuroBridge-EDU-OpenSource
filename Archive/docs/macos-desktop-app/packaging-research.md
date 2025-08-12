# macOS Desktop App Packaging Research Report

## Executive Summary

Based on comprehensive research using Context7 MCP and Perplexity MCP, the optimal strategy for packaging NeuroBridge EDU as a native macOS desktop app involves:

1. **PyInstaller** for Python packaging (preferred over py2app for heavy ML dependencies)
2. **WKWebView with PyObjC** for frontend integration (preferred over embedded HTTP server)
3. **whisper.cpp with quantized models** for AI inference (preferred over Python Whisper)
4. **On-demand model downloads** with local caching (not bundled in app)
5. **Hardened Runtime + Developer ID** signing and notarization

## 1. macOS App Bundling Strategy Analysis

### PyInstaller vs py2app vs Alternatives

**PyInstaller (RECOMMENDED)**
- ✅ **Superior for Heavy Dependencies**: Excellent support for PyTorch, NumPy, and other ML libraries
- ✅ **Mature Hook System**: Comprehensive dependency analysis and collection
- ✅ **Active Maintenance**: Regular updates and community support
- ✅ **macOS Code Signing**: Better integration with modern signing/notarization workflows
- ✅ **Architecture Support**: Robust universal2 and Apple Silicon support
- ⚠️ **Bundle Size**: Larger than py2app but manageable with proper exclusions

**py2app (NOT RECOMMENDED for this use case)**
- ❌ **ML Stack Issues**: Frequent problems with PyTorch and heavy native dependencies
- ❌ **Maintenance Lag**: Slower adoption of new macOS features
- ❌ **Code Signing Problems**: Common issues with hardened runtime and notarization
- ❌ **Community Reports**: Consistent feedback about difficulties with modern ML stacks

**BeeWare Briefcase (ALTERNATIVE)**
- ✅ **Native App Experience**: Better macOS integration and installer support
- ⚠️ **Heavy Dependencies**: Requires manual recipes for PyTorch/ML stacks
- ⚠️ **Learning Curve**: More setup work compared to PyInstaller

## 2. Python Environment Packaging

### Recommended Approach: One-Folder Distribution

```python
# PyInstaller spec file structure
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend/dist', 'frontend')],  # React build
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'whisper',  # If using Python Whisper
    ],
    hookspath=[],
    hooksconfig={
        "matplotlib": {"backends": []},  # Exclude if not needed
    },
    runtime_hooks=[],
    excludes=[
        'torch.distributions',  # Exclude unused PyTorch modules
        'torchvision',
        'test',
        'unittest',
    ],
    noarchive=False,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NeuroBridge EDU',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app
    disable_windowed_traceback=False,
    target_arch='arm64',  # Or 'universal2' for universal binary
    codesign_identity='Developer ID Application: Your Name',
    entitlements_file='entitlements.plist',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NeuroBridge EDU'
)

app = BUNDLE(
    coll,
    name='NeuroBridge EDU.app',
    icon='icon.icns',
    bundle_identifier='com.yourcompany.neurobridge-edu',
    info_plist={
        'NSMicrophoneUsageDescription': 'This app needs microphone access for real-time transcription.',
        'LSMinimumSystemVersion': '10.15',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
```

### File Size Optimization

1. **Exclude Unused PyTorch Components**:
   ```python
   excludes=[
       'torch.distributions',
       'torch.nn.modules.loss',
       'torchvision',
       'torchaudio',  # If not using audio features
   ]
   ```

2. **Remove Test and Debug Files**:
   ```python
   # Custom hook to remove test directories
   from PyInstaller.utils.hooks import collect_all
   
   def hook(hook_api):
       # Remove test directories from collections
       pass
   ```

## 3. Whisper Integration Strategy

### Recommended: whisper.cpp over Python Whisper

**Model Sizes and Performance (2025 data)**:
- **Tiny**: ~78MB quantized (INT8), real-time on Apple Silicon
- **Base**: ~141MB standard, ~78MB quantized (INT8), near real-time
- **Small**: ~244MB standard, ~138MB quantized, good for accuracy/speed balance
- **Medium**: ~769MB standard, ~413MB quantized, offline processing
- **Large-v3**: ~1.5GB+ standard, ~800MB+ quantized, highest accuracy

**Deployment Strategy**:
```python
# Model management system
class WhisperModelManager:
    def __init__(self):
        self.models_dir = Path.home() / "Library/Application Support/NeuroBridge EDU/Models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def download_model(self, model_name: str, quantization: str = "int8"):
        """Download model on first use with progress tracking"""
        model_file = self.models_dir / f"{model_name}-{quantization}.bin"
        if not model_file.exists():
            # Download with resume support and checksum verification
            self._download_with_progress(model_name, quantization, model_file)
        return model_file
    
    def list_available_models(self):
        """Return models available for download with sizes"""
        return {
            "tiny": {"size": "78MB", "description": "Fastest, good for real-time"},
            "base": {"size": "78MB", "description": "Balanced speed/accuracy"},
            "small": {"size": "138MB", "description": "Better accuracy"},
            "medium": {"size": "413MB", "description": "High accuracy, slower"},
        }
```

### Model Loading Optimization
```python
# Use memory mapping for efficient model loading
import mmap

class WhisperEngine:
    def __init__(self, model_path):
        self.model_path = model_path
        self._model_handle = None
        
    def load_model(self):
        """Memory-map model for efficient loading"""
        if self._model_handle is None:
            # Use whisper.cpp Python bindings with mmap
            self._model_handle = whisper_cpp.Whisper.from_file(
                str(self.model_path),
                use_mmap=True  # Enable memory mapping
            )
        return self._model_handle
```

## 4. Frontend Integration Architecture

### Recommended: WKWebView + PyObjC Approach

```python
# PyObjC-based WebView integration
import objc
from Foundation import *
from WebKit import *
from Cocoa import *

class NeuroBridgeWebView(NSObject):
    def init(self):
        self = objc.super(NeuroBridgeWebView, self).init()
        if self is None:
            return None
            
        # Configure WKWebView
        config = WKWebViewConfiguration.alloc().init()
        
        # Add message handler for React -> Python communication
        content_controller = config.userContentController()
        content_controller.addScriptMessageHandler_name_(self, "pythonBridge")
        
        # Create WebView
        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, 1200, 800),
            config
        )
        
        # Load React app from bundle
        bundle_path = NSBundle.mainBundle().resourcePath()
        html_path = os.path.join(bundle_path, "frontend", "index.html")
        html_url = NSURL.fileURLWithPath_(html_path)
        self.webview.loadFileURL_allowingReadAccessToURL_(html_url, html_url)
        
        return self
    
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        """Handle messages from React frontend"""
        body = message.body()
        if body.get("action") == "startTranscription":
            self.start_transcription()
        elif body.get("action") == "stopTranscription":
            self.stop_transcription()
```

### Security Configuration
```python
# Secure communication setup
def setup_secure_bridge():
    # Generate per-session token
    session_token = secrets.token_urlsafe(32)
    
    # Inject token into WebView
    js_injection = f"""
    window.NEUROBRIDGE_TOKEN = '{session_token}';
    window.NEUROBRIDGE_API_BASE = 'bridge://api';
    """
    
    # Add to WKUserScript for document start
    user_script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
        js_injection,
        WKUserScriptInjectionTime.WKUserScriptInjectionTimeAtDocumentStart,
        True
    )
    
    return user_script, session_token
```

### App Bundle Structure
```
NeuroBridge EDU.app/
├── Contents/
│   ├── Info.plist                 # App metadata and permissions
│   ├── MacOS/
│   │   └── NeuroBridge EDU        # Main executable (PyInstaller bundle)
│   ├── Resources/
│   │   ├── frontend/              # React production build
│   │   │   ├── index.html
│   │   │   ├── static/
│   │   │   └── assets/
│   │   ├── icon.icns             # App icon
│   │   └── models/               # Optional: single tiny model for offline
│   └── Frameworks/               # Python runtime and dependencies
│       ├── Python.framework
│       └── lib/
```

## 5. Code Signing and Distribution

### Required Entitlements (entitlements.plist)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Audio recording permission -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    
    <!-- Network access for model downloads -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Dynamic library loading (for ML libraries) -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    
    <!-- Disable library validation for Python extensions -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

### Complete Signing Script
```bash
#!/bin/bash

APP_NAME="NeuroBridge EDU"
IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"
ENTITLEMENTS="entitlements.plist"

# Find and sign all binaries recursively
find "$APP_NAME.app" -type f \( -name "*.dylib" -o -name "*.so" -o -perm +111 \) -exec \
    codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" {} \;

# Sign the main app bundle
codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" "$APP_NAME.app"

# Verify signing
codesign --verify --verbose=4 --strict "$APP_NAME.app"

# Submit for notarization
xcrun notarytool submit "$APP_NAME.dmg" --keychain-profile "notarytool-profile" --wait

# Staple the notarization ticket
xcrun stapler staple "$APP_NAME.app"
xcrun stapler staple "$APP_NAME.dmg"

# Final verification
spctl --assess --type execute --verbose=4 "$APP_NAME.app"
```

## 6. Performance and File Size Estimates

### Bundle Size Breakdown (Estimated)
- **Base PyInstaller Bundle**: ~150MB
- **Python Runtime + Dependencies**: ~200MB
- **PyTorch (CPU-optimized)**: ~150MB
- **React Frontend**: ~5MB
- **Optional Tiny Model**: ~78MB (quantized)
- **Total Estimated Size**: ~580MB (without large models)

### Runtime Performance (Apple Silicon)
- **App Startup**: 2-3 seconds (one-folder mode)
- **Model Loading**: 1-2 seconds (memory-mapped)
- **Real-time Transcription**: Tiny/Base models achieve real-time performance
- **Memory Usage**: ~500MB-1GB depending on model size

## 7. Implementation Roadmap

### Phase 1: Core Packaging (Week 1-2)
1. Set up PyInstaller configuration
2. Create basic PyObjC WebView wrapper
3. Implement React build integration
4. Test basic app bundle creation

### Phase 2: AI Integration (Week 3-4)
1. Integrate whisper.cpp bindings
2. Implement model download manager
3. Add real-time audio processing pipeline
4. Test transcription performance

### Phase 3: Polish & Distribution (Week 5-6)
1. Implement code signing automation
2. Create DMG with installer UI
3. Set up notarization workflow
4. Add automatic update mechanism

### Phase 4: Testing & Deployment (Week 7-8)
1. Test on various macOS versions (10.15+)
2. Validate on different Mac hardware (Intel/Apple Silicon)
3. Performance optimization and debugging
4. Prepare distribution infrastructure

## 8. Alternative Approaches Considered

### Why Not Electron?
- **Size Overhead**: Electron apps are typically 200-300MB larger
- **Python Integration**: Complex to integrate FastAPI backend
- **Performance**: V8 engine overhead vs native WKWebView

### Why Not Tauri?
- **Learning Curve**: Requires Rust development
- **Python Backend**: Still need separate Python process management
- **Ecosystem**: Less mature for Python ML applications

### Why Not Pure Native (Swift/Objective-C)?
- **Development Time**: Requires rewriting entire Python backend
- **ML Ecosystem**: Python has superior AI/ML library support
- **Maintenance**: Two codebases to maintain

## Conclusion

The recommended architecture provides the best balance of:
- **Native Performance**: WKWebView + PyObjC for UI responsiveness
- **Development Efficiency**: Reuse existing React + FastAPI code
- **Distribution Simplicity**: Single app bundle with proper signing
- **User Experience**: Professional macOS app with proper system integration
- **Maintainability**: Minimal platform-specific code required

This approach leverages the strengths of each technology while minimizing the complexity and size overhead compared to alternatives like Electron or complete rewrites.