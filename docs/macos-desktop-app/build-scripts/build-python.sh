#!/bin/bash
# Build Python backend for macOS app packaging
# This script packages the FastAPI backend into a standalone executable

set -e  # Exit on any error

# Configuration
BUILD_TYPE=${1:-production}
ARCH=${2:-universal}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
PYTHON_BACKEND_DIR="$PROJECT_ROOT/python_backend"
OUTPUT_DIR="$PROJECT_ROOT/python-dist"

echo "🐍 Building Python backend for macOS ($BUILD_TYPE, $ARCH)"
echo "Project root: $PROJECT_ROOT"
echo "Python backend: $PYTHON_BACKEND_DIR"
echo "Output directory: $OUTPUT_DIR"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Check if python backend exists
if [ ! -d "$PYTHON_BACKEND_DIR" ]; then
    echo "❌ Error: Python backend directory not found at $PYTHON_BACKEND_DIR"
    exit 1
fi

# Navigate to Python backend directory
cd "$PYTHON_BACKEND_DIR"

# Check for requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found in $PYTHON_BACKEND_DIR"
    exit 1
fi

# Install build dependencies
echo "📦 Installing build dependencies..."
pip install --upgrade pip
pip install pyinstaller pyoxidizer briefcase

# Install project dependencies
echo "📦 Installing project dependencies..."
pip install -r requirements.txt

if [ "$BUILD_TYPE" = "production" ]; then
    echo "🏭 Building for production with PyOxidizer..."
    
    # Create PyOxidizer configuration if it doesn't exist
    if [ ! -f "pyoxidizer.bzl" ]; then
        echo "📝 Creating PyOxidizer configuration..."
        cat > pyoxidizer.bzl << 'EOF'
def make_exe():
    dist = default_python_distribution()
    
    python_config = dist.make_python_interpreter_config()
    python_config.run_command = "from main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=3939)"
    
    exe = dist.to_python_executable(
        name = "neurobridge-backend",
        config = python_config,
        extension_module_filter = "minimal",
        include_sources = True,
        include_resources = False,
    )
    
    # Bundle FastAPI backend
    exe.add_python_resources([
        dist.read_package_root(
            path = ".",
            packages = ["api", "services", "models", "utils"]
        )
    ])
    
    return exe

def make_embedded_resources():
    return {}

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

register_target("exe", make_exe)
register_target("resources", make_embedded_resources) 
register_target("install", make_install, depends=["exe"])
EOF
    fi
    
    # Build with PyOxidizer
    if [ "$ARCH" = "universal" ]; then
        pyoxidizer build --target-triple universal2-apple-darwin
        cp -R target/universal2-apple-darwin/debug/install/* "$OUTPUT_DIR/"
    elif [ "$ARCH" = "arm64" ]; then
        pyoxidizer build --target-triple aarch64-apple-darwin
        cp -R target/aarch64-apple-darwin/debug/install/* "$OUTPUT_DIR/"
    else
        pyoxidizer build --target-triple x86_64-apple-darwin
        cp -R target/x86_64-apple-darwin/debug/install/* "$OUTPUT_DIR/"
    fi
    
else
    echo "🔧 Building for development with PyInstaller..."
    
    # Create PyInstaller spec file
    cat > neurobridge-backend.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Collect all Python backend files
datas = [
    ('api', 'api'),
    ('services', 'services'),
    ('models', 'models'),
    ('utils', 'utils'),
    ('requirements.txt', '.'),
]

# Add any additional data files
if os.path.exists('data'):
    datas.append(('data', 'data'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'sqlalchemy',
        'openai',
        'whisper',
        'numpy',
        'scipy',
        'librosa',
        'soundfile',
        'aiosqlite',
        'sse_starlette',
        'python_multipart',
        'reportlab'
    ],
    hookspath=[],
    hooksconfig={
        "matplotlib": {"backends": []},  # Exclude if not needed
    },
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL.ImageTk',  # Reduce size
        'test',
        'unittest',
        'pdb',
        'doctest'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='neurobridge-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='neurobridge-backend'
)
EOF

    # Build with PyInstaller
    pyinstaller neurobridge-backend.spec --clean --noconfirm
    
    # Copy output
    cp -R dist/neurobridge-backend/* "$OUTPUT_DIR/"
    
    # Clean up spec file
    rm -f neurobridge-backend.spec
fi

# Verify output
if [ ! -d "$OUTPUT_DIR" ] || [ -z "$(ls -A "$OUTPUT_DIR")" ]; then
    echo "❌ Error: Build failed - output directory is empty"
    exit 1
fi

echo "✅ Python backend built successfully!"
echo "📁 Output location: $OUTPUT_DIR"
echo "📊 Bundle size: $(du -sh "$OUTPUT_DIR" | cut -f1)"

# List contents for verification
echo "📋 Bundle contents:"
ls -la "$OUTPUT_DIR"

echo "🎉 Python backend build complete!"