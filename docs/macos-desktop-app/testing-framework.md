# macOS App Testing & Quality Assurance Strategy for NeuroBridge EDU

Based on my research into macOS app testing frameworks, Apple's requirements, and the specific challenges of hybrid desktop apps with embedded Python environments, I'll create a comprehensive testing strategy for NeuroBridge EDU.

## Executive Summary

This comprehensive testing strategy ensures the NeuroBridge EDU macOS app meets professional quality standards across all supported configurations. The strategy addresses the unique challenges of a hybrid desktop app that embeds a Python/FastAPI backend, React frontend, real-time audio processing, and local database functionality within a native macOS app bundle.

## 1. macOS App Bundle Testing Framework

### 1.1 App Bundle Structure Validation

**Automated Bundle Validation Suite:**

```python
# test_bundle_structure.py
import pytest
import os
import plistlib
from pathlib import Path

class TestAppBundleStructure:
    @pytest.fixture(scope="class")
    def app_bundle_path(self):
        """Locate the NeuroBridge.app bundle"""
        return Path("./dist/NeuroBridge.app")
    
    def test_bundle_structure_exists(self, app_bundle_path):
        """Verify complete app bundle structure"""
        required_paths = [
            "Contents/Info.plist",
            "Contents/MacOS/NeuroBridge", 
            "Contents/Resources/",
            "Contents/Frameworks/Python.framework",
            "Contents/Resources/python_backend/",
            "Contents/Resources/frontend/build/"
        ]
        
        for path in required_paths:
            full_path = app_bundle_path / path
            assert full_path.exists(), f"Missing required path: {path}"
    
    def test_info_plist_validation(self, app_bundle_path):
        """Validate Info.plist contains required keys and permissions"""
        plist_path = app_bundle_path / "Contents/Info.plist"
        
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        required_keys = [
            "CFBundleIdentifier",
            "CFBundleVersion", 
            "CFBundleShortVersionString",
            "NSMicrophoneUsageDescription",
            "NSLocalNetworkUsageDescription"
        ]
        
        for key in required_keys:
            assert key in plist_data, f"Missing required Info.plist key: {key}"
        
        # Verify microphone permission description
        assert len(plist_data["NSMicrophoneUsageDescription"]) > 10
```

### 1.2 Code Signing and Notarization Testing

**Security Validation Framework:**

```python
# test_security_validation.py
import subprocess
import pytest

class TestSecurityValidation:
    @pytest.fixture(scope="class") 
    def app_bundle_path(self):
        return Path("./dist/NeuroBridge.app")
    
    def test_code_signature_valid(self, app_bundle_path):
        """Verify app bundle is properly code signed"""
        result = subprocess.run([
            "codesign", "--verify", "--verbose", 
            str(app_bundle_path)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Code signing verification failed: {result.stderr}"
    
    def test_gatekeeper_compatibility(self, app_bundle_path):
        """Test Gatekeeper approval"""
        result = subprocess.run([
            "spctl", "--assess", "--verbose", 
            str(app_bundle_path)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Gatekeeper assessment failed: {result.stderr}"
    
    def test_hardened_runtime_entitlements(self, app_bundle_path):
        """Verify hardened runtime entitlements"""
        result = subprocess.run([
            "codesign", "--display", "--entitlements", "-", 
            str(app_bundle_path)
        ], capture_output=True, text=True)
        
        required_entitlements = [
            "com.apple.security.device.microphone",
            "com.apple.security.network.server",
            "com.apple.security.network.client"
        ]
        
        for entitlement in required_entitlements:
            assert entitlement in result.stdout, f"Missing entitlement: {entitlement}"
```

### 1.3 Universal Binary Testing

**Cross-Architecture Validation:**

```bash
#!/bin/bash
# test_universal_binary.sh

# Test script for Universal Binary validation
APP_PATH="./dist/NeuroBridge.app/Contents/MacOS/NeuroBridge"

echo "Testing Universal Binary Support..."

# Check if binary supports both architectures
file "$APP_PATH"

# Test x86_64 architecture
arch -x86_64 "$APP_PATH" --test-mode --validate-arch &
x86_64_pid=$!

# Test arm64 architecture  
arch -arm64 "$APP_PATH" --test-mode --validate-arch &
arm64_pid=$!

# Wait for both tests and check exit codes
wait $x86_64_pid
x86_64_result=$?

wait $arm64_pid
arm64_result=$?

if [ $x86_64_result -eq 0 ] && [ $arm64_result -eq 0 ]; then
    echo "✅ Universal binary validation passed"
    exit 0
else
    echo "❌ Universal binary validation failed"
    exit 1
fi
```

## 2. Cross-Platform macOS Testing Matrix

### 2.1 Hardware and OS Compatibility Matrix

**Automated Test Matrix Configuration:**

```python
# test_matrix_config.py
import pytest

# Test matrix for different macOS configurations
TEST_MATRIX = [
    # (macOS Version, Architecture, Hardware Class)
    ("13.0", "arm64", "MacBook Air M1"),
    ("13.0", "arm64", "MacBook Pro M2"), 
    ("14.0", "arm64", "Mac Studio M2"),
    ("12.0", "x86_64", "MacBook Pro Intel"),
    ("13.0", "x86_64", "iMac Intel"),
    ("14.0", "arm64", "Mac Mini M2")
]

@pytest.mark.parametrize("macos_version,arch,hardware", TEST_MATRIX)
class TestCrossCompatibility:
    def test_app_startup_time(self, macos_version, arch, hardware):
        """Test cold startup performance across configurations"""
        import time
        start_time = time.time()
        
        # Launch app and wait for ready signal
        result = self.launch_app_and_wait_ready(timeout=30)
        
        startup_time = time.time() - start_time
        
        # Performance targets vary by hardware class
        max_startup_time = {
            "M1": 8.0,
            "M2": 6.0, 
            "Intel": 12.0
        }
        
        hardware_class = "M2" if "M2" in hardware else ("M1" if "M1" in hardware else "Intel")
        
        assert startup_time < max_startup_time[hardware_class], \
            f"Startup too slow on {hardware}: {startup_time:.2f}s"
```

### 2.2 Performance Benchmarking Framework

**Comprehensive Performance Testing:**

```python
# test_performance_benchmarks.py
import pytest
import psutil
import time
from pathlib import Path

class TestPerformanceBenchmarks:
    @pytest.fixture(scope="class")
    def app_process(self):
        """Launch app and return process handle"""
        # Implementation to launch and return process
        pass
    
    def test_memory_usage_limits(self, app_process):
        """Verify memory usage stays within acceptable limits"""
        # Warm up the application
        time.sleep(10)
        
        memory_info = psutil.Process(app_process.pid).memory_info()
        
        # Memory limits (in MB)
        MAX_RSS = 500  # Resident Set Size
        MAX_VMS = 1000  # Virtual Memory Size
        
        assert memory_info.rss / 1024 / 1024 < MAX_RSS, \
            f"RSS memory usage too high: {memory_info.rss / 1024 / 1024:.1f}MB"
        
        assert memory_info.vms / 1024 / 1024 < MAX_VMS, \
            f"Virtual memory usage too high: {memory_info.vms / 1024 / 1024:.1f}MB"
    
    def test_cpu_usage_under_load(self, app_process):
        """Test CPU usage during intensive transcription"""
        # Start CPU monitoring
        process = psutil.Process(app_process.pid)
        cpu_samples = []
        
        # Simulate heavy audio processing load
        for i in range(30):  # 30 seconds of monitoring
            cpu_percent = process.cpu_percent(interval=1)
            cpu_samples.append(cpu_percent)
        
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # CPU usage limits
        assert avg_cpu < 60.0, f"Average CPU usage too high: {avg_cpu:.1f}%"
        assert max_cpu < 85.0, f"Peak CPU usage too high: {max_cpu:.1f}%"
```

## 3. Embedded Python Environment Testing

### 3.1 Python Runtime Validation

**Embedded Python Environment Tests:**

```python
# test_embedded_python.py
import pytest
import subprocess
import sys
from pathlib import Path

class TestEmbeddedPython:
    @pytest.fixture(scope="class")
    def python_path(self):
        """Get path to embedded Python interpreter"""
        return Path("./dist/NeuroBridge.app/Contents/Frameworks/Python.framework/Versions/3.11/bin/python3")
    
    def test_python_runtime_initialization(self, python_path):
        """Test embedded Python starts correctly"""
        result = subprocess.run([
            str(python_path), "-c", "import sys; print(sys.version)"
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, f"Python initialization failed: {result.stderr}"
        assert "3.11" in result.stdout, "Wrong Python version"
    
    def test_required_packages_available(self, python_path):
        """Verify all required Python packages are bundled"""
        required_packages = [
            "fastapi", "uvicorn", "sqlalchemy", "openai", 
            "whisper", "numpy", "scipy", "librosa"
        ]
        
        for package in required_packages:
            result = subprocess.run([
                str(python_path), "-c", f"import {package}; print('{package} OK')"
            ], capture_output=True, text=True, timeout=5)
            
            assert result.returncode == 0, f"Package {package} not available: {result.stderr}"
    
    def test_whisper_model_loading(self, python_path):
        """Test Whisper model loads correctly from bundle"""
        test_script = """
import whisper
import os
import sys

# Set model path to bundled location
model_path = os.path.join(os.path.dirname(sys.executable), 
                         '..', 'Resources', 'whisper_models')
                         
try:
    model = whisper.load_model('base', download_root=model_path)
    print('Whisper model loaded successfully')
    print(f'Model device: {model.device}')
    sys.exit(0)
except Exception as e:
    print(f'Whisper model loading failed: {e}')
    sys.exit(1)
"""
        
        result = subprocess.run([
            str(python_path), "-c", test_script
        ], capture_output=True, text=True, timeout=30)
        
        assert result.returncode == 0, f"Whisper model loading failed: {result.stderr}"
        assert "loaded successfully" in result.stdout
```

### 3.2 FastAPI Backend Testing

**Backend Integration Tests:**

```python
# test_fastapi_backend.py
import pytest
import requests
import time
import subprocess
from pathlib import Path

class TestFastAPIBackend:
    @pytest.fixture(scope="class")
    def backend_server(self):
        """Start the embedded FastAPI server"""
        app_bundle = Path("./dist/NeuroBridge.app")
        python_path = app_bundle / "Contents/Frameworks/Python.framework/Versions/3.11/bin/python3"
        backend_script = app_bundle / "Contents/Resources/python_backend/main.py"
        
        # Start backend server
        process = subprocess.Popen([
            str(python_path), str(backend_script), 
            "--host", "127.0.0.1", "--port", "3939"
        ], env={"PYTHONPATH": str(backend_script.parent)})
        
        # Wait for server to start
        for _ in range(30):  # 30 second timeout
            try:
                response = requests.get("http://127.0.0.1:3939/health", timeout=2)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)
        else:
            process.terminate()
            pytest.fail("Backend server failed to start")
        
        yield process
        
        process.terminate()
        process.wait()
    
    def test_health_endpoint(self, backend_server):
        """Test backend health endpoint responds correctly"""
        response = requests.get("http://127.0.0.1:3939/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "whisper_ready" in data
        assert "database_ready" in data
    
    def test_transcription_endpoint(self, backend_server):
        """Test transcription endpoint with sample audio"""
        # Create a small test audio file (silence)
        import wave
        import struct
        
        sample_rate = 16000
        duration = 1  # 1 second
        
        with wave.open("/tmp/test_audio.wav", "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            
            for _ in range(sample_rate * duration):
                wav_file.writeframes(struct.pack('<h', 0))
        
        # Test transcription
        with open("/tmp/test_audio.wav", "rb") as audio_file:
            response = requests.post(
                "http://127.0.0.1:3939/api/transcribe/chunk",
                files={"audio": audio_file},
                timeout=30
            )
        
        assert response.status_code == 200
        # Should handle silence gracefully
        assert response.json()["success"] in [True, False]  # May be empty for silence
```

## 4. Frontend-Backend Integration Testing

### 4.1 React Frontend Testing

**Frontend Integration Test Suite:**

```python
# test_frontend_integration.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class TestFrontendIntegration:
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--use-fake-ui-for-media-stream")  # Allow mic access
        options.add_argument("--use-fake-device-for-media-stream")
        
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1200, 800)
        
        yield driver
        driver.quit()
    
    @pytest.fixture(scope="class")
    def app_url(self, backend_server):
        """URL to the React frontend served by the app"""
        return "http://127.0.0.1:3939"  # Assuming backend serves frontend
    
    def test_app_loads_successfully(self, driver, app_url):
        """Test React app loads without errors"""
        driver.get(app_url)
        
        # Wait for app to load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.id, "root")))
        
        # Check for React error boundary
        error_elements = driver.find_elements(By.class_name, "error-boundary")
        assert len(error_elements) == 0, "React error boundary triggered"
        
        # Verify main components loaded
        wait.until(EC.presence_of_element_located((By.class_name, "transcription-display")))
        wait.until(EC.presence_of_element_located((By.class_name, "audio-recorder")))
    
    def test_microphone_permission_flow(self, driver, app_url):
        """Test microphone permission handling"""
        driver.get(app_url)
        
        # Click record button
        wait = WebDriverWait(driver, 10)
        record_button = wait.until(EC.element_to_be_clickable((By.id, "record-button")))
        record_button.click()
        
        # Should show connection status
        wait.until(EC.presence_of_element_located((By.class_name, "connection-status")))
        
        # In test environment, should show "Connected" or permission request
        time.sleep(2)  # Allow status to update
        status = driver.find_element(By.class_name, "connection-status").text
        assert status in ["Connected", "Requesting permissions..."]
    
    def test_summary_generation_flow(self, driver, app_url):
        """Test AI summary generation workflow"""
        driver.get(app_url)
        
        wait = WebDriverWait(driver, 10)
        
        # Simulate having transcription text (would normally come from recording)
        driver.execute_script("""
            window.testMode = true;
            window.setTranscriptionText('This is a test transcript for summary generation.');
        """)
        
        # Click generate summary button
        summary_button = wait.until(EC.element_to_be_clickable((By.id, "generate-summary")))
        summary_button.click()
        
        # Should show loading state
        wait.until(EC.presence_of_element_located((By.class_name, "loading-spinner")))
        
        # Wait for summary to generate (with extended timeout)
        wait = WebDriverWait(driver, 60)
        summary_content = wait.until(EC.presence_of_element_located((By.class_name, "summary-content")))
        
        assert len(summary_content.text) > 0, "Summary was not generated"
```

### 4.2 Real-time Communication Testing

**WebSocket/SSE Testing Framework:**

```python
# test_realtime_communication.py
import pytest
import asyncio
import websockets
import json
from urllib.parse import urljoin

class TestRealtimeCommunication:
    @pytest.fixture(scope="class")
    def event_loop(self):
        """Create event loop for async tests"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    def test_sse_transcription_stream(self, backend_server):
        """Test Server-Sent Events for real-time transcription"""
        import sseclient
        import requests
        
        # Start a transcription session
        response = requests.post("http://127.0.0.1:3939/api/transcribe/start")
        assert response.status_code == 200
        session_data = response.json()
        session_id = session_data["session_id"]
        
        # Connect to SSE stream
        sse_url = f"http://127.0.0.1:3939/api/transcribe/stream/{session_id}"
        
        messages_received = []
        with requests.get(sse_url, stream=True) as response:
            client = sseclient.SSEClient(response)
            
            # Collect messages for 5 seconds
            start_time = time.time()
            for event in client.events():
                if time.time() - start_time > 5:
                    break
                    
                if event.data:
                    messages_received.append(json.loads(event.data))
        
        # Should receive at least heartbeat messages
        assert len(messages_received) > 0, "No SSE messages received"
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, backend_server, event_loop):
        """Test WebSocket connection stability"""
        ws_url = "ws://127.0.0.1:3939/ws/transcription"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send test message
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(), timeout=5.0
                )
                
                data = json.loads(response)
                assert data["type"] == "pong", "WebSocket ping/pong failed"
                
        except asyncio.TimeoutError:
            pytest.fail("WebSocket connection timed out")
        except websockets.exceptions.ConnectionClosed:
            pytest.fail("WebSocket connection closed unexpectedly")
```

## 5. Audio Processing Pipeline Testing

### 5.1 Audio Capture and Processing Tests

**Comprehensive Audio Testing Framework:**

```python
# test_audio_processing.py
import pytest
import numpy as np
import wave
import struct
import tempfile
import requests
from pathlib import Path

class TestAudioProcessing:
    @pytest.fixture(scope="class")
    def test_audio_samples(self):
        """Generate test audio samples for various scenarios"""
        sample_rate = 16000
        samples = {}
        
        # Silence
        silence = np.zeros(sample_rate)  # 1 second of silence
        samples["silence"] = silence
        
        # Sine wave (for basic processing test)
        t = np.linspace(0, 1, sample_rate)
        sine_wave = np.sin(2 * np.pi * 440 * t)  # 440Hz tone
        samples["tone"] = sine_wave
        
        # White noise (for robustness testing)
        white_noise = np.random.normal(0, 0.1, sample_rate)
        samples["noise"] = white_noise
        
        # Speech-like signal (formants)
        speech_like = (np.sin(2 * np.pi * 150 * t) +  # Fundamental
                      0.5 * np.sin(2 * np.pi * 900 * t) +  # First formant
                      0.3 * np.sin(2 * np.pi * 2100 * t))  # Second formant
        samples["speech_like"] = speech_like
        
        return samples
    
    def create_wav_file(self, audio_data, filename, sample_rate=16000):
        """Helper to create WAV file from numpy array"""
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            
            # Convert to 16-bit PCM
            pcm_data = (audio_data * 32767).astype(np.int16)
            wav_file.writeframes(pcm_data.tobytes())
    
    def test_audio_format_validation(self, backend_server, test_audio_samples):
        """Test various audio formats are handled correctly"""
        formats_to_test = [
            ("wav", 16000, 1),  # Standard format
            ("wav", 44100, 1),  # High sample rate
            ("wav", 8000, 1),   # Low sample rate
        ]
        
        for fmt, sample_rate, channels in formats_to_test:
            with tempfile.NamedTemporaryFile(suffix=f".{fmt}") as temp_file:
                # Resample audio to target sample rate
                audio_data = test_audio_samples["tone"]
                if sample_rate != 16000:
                    # Simple resampling (for test purposes)
                    audio_data = np.interp(
                        np.linspace(0, len(audio_data), sample_rate),
                        np.arange(len(audio_data)),
                        audio_data
                    )
                
                self.create_wav_file(audio_data, temp_file.name, sample_rate)
                
                # Test transcription with this format
                with open(temp_file.name, "rb") as audio_file:
                    response = requests.post(
                        "http://127.0.0.1:3939/api/transcribe/chunk",
                        files={"audio": audio_file},
                        timeout=30
                    )
                
                assert response.status_code == 200, \
                    f"Failed to process {fmt} at {sample_rate}Hz"
    
    def test_audio_quality_thresholds(self, backend_server, test_audio_samples):
        """Test audio processing maintains quality thresholds"""
        test_cases = [
            ("silence", False),      # Should detect silence
            ("noise", False),        # Should reject pure noise
            ("speech_like", True),   # Should accept speech-like signal
            ("tone", False),         # Should reject pure tone
        ]
        
        for audio_type, should_transcribe in test_cases:
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
                self.create_wav_file(test_audio_samples[audio_type], temp_file.name)
                
                with open(temp_file.name, "rb") as audio_file:
                    response = requests.post(
                        "http://127.0.0.1:3939/api/transcribe/chunk",
                        files={"audio": audio_file},
                        timeout=30
                    )
                
                assert response.status_code == 200
                result = response.json()
                
                if should_transcribe:
                    # Should attempt transcription (may be empty but shouldn't error)
                    assert result["success"] is True
                else:
                    # Should handle gracefully (empty result is OK)
                    assert result["success"] in [True, False]
    
    def test_concurrent_audio_processing(self, backend_server, test_audio_samples):
        """Test system handles multiple simultaneous audio requests"""
        import concurrent.futures
        import threading
        
        def process_audio_chunk(chunk_id):
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
                self.create_wav_file(
                    test_audio_samples["speech_like"], 
                    temp_file.name
                )
                
                with open(temp_file.name, "rb") as audio_file:
                    response = requests.post(
                        "http://127.0.0.1:3939/api/transcribe/chunk",
                        files={"audio": audio_file},
                        timeout=60
                    )
                
                return response.status_code, response.json()
        
        # Test with 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_audio_chunk, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        for status_code, result in results:
            assert status_code == 200, "Concurrent audio processing failed"
            assert result["success"] in [True, False]  # Processing may succeed or fail gracefully
```

### 5.2 Whisper Model Performance Testing

**AI Model Performance Validation:**

```python
# test_whisper_performance.py
import pytest
import time
import statistics
from pathlib import Path

class TestWhisperPerformance:
    @pytest.fixture(scope="class")
    def whisper_benchmarks(self):
        """Load or create benchmark audio files with known transcripts"""
        # In real implementation, load from test assets
        return [
            ("test_audio_1.wav", "Hello, this is a test transcript."),
            ("test_audio_2.wav", "NeuroBridge is an educational transcription tool."),
            ("test_audio_3.wav", "The quick brown fox jumps over the lazy dog."),
        ]
    
    def test_transcription_latency_targets(self, backend_server, whisper_benchmarks):
        """Test Whisper transcription meets latency targets"""
        latencies = []
        
        for audio_file, expected_transcript in whisper_benchmarks:
            # Skip if test file doesn't exist (would be provided in real tests)
            if not Path(audio_file).exists():
                continue
                
            start_time = time.time()
            
            with open(audio_file, "rb") as audio:
                response = requests.post(
                    "http://127.0.0.1:3939/api/transcribe/chunk",
                    files={"audio": audio},
                    timeout=60
                )
            
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)
            
            assert response.status_code == 200
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            
            # Performance targets
            assert avg_latency < 5.0, f"Average latency too high: {avg_latency:.2f}s"
            assert p95_latency < 8.0, f"P95 latency too high: {p95_latency:.2f}s"
    
    def test_transcription_accuracy(self, backend_server, whisper_benchmarks):
        """Test Whisper transcription accuracy against known examples"""
        from difflib import SequenceMatcher
        
        accuracies = []
        
        for audio_file, expected_transcript in whisper_benchmarks:
            if not Path(audio_file).exists():
                continue
            
            with open(audio_file, "rb") as audio:
                response = requests.post(
                    "http://127.0.0.1:3939/api/transcribe/chunk",
                    files={"audio": audio},
                    timeout=60
                )
            
            assert response.status_code == 200
            result = response.json()
            
            if result["success"] and result.get("transcript"):
                actual_transcript = result["transcript"].strip().lower()
                expected_clean = expected_transcript.strip().lower()
                
                # Calculate similarity ratio
                similarity = SequenceMatcher(
                    None, actual_transcript, expected_clean
                ).ratio()
                accuracies.append(similarity)
        
        if accuracies:
            avg_accuracy = statistics.mean(accuracies)
            
            # Accuracy target (70% for basic test audio)
            assert avg_accuracy > 0.7, \
                f"Transcription accuracy too low: {avg_accuracy:.1%}"
```

## 6. User Experience Testing Framework

### 6.1 Installation and First-Run Testing

**Complete User Journey Tests:**

```python
# test_user_experience.py
import pytest
import subprocess
import time
from pathlib import Path

class TestUserExperience:
    def test_first_launch_experience(self):
        """Test complete first-launch user experience"""
        app_path = Path("./dist/NeuroBridge.app/Contents/MacOS/NeuroBridge")
        
        # Launch app for first time
        process = subprocess.Popen([str(app_path)], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
        
        try:
            # Wait for app to initialize
            time.sleep(10)
            
            # Check if process is still running (hasn't crashed)
            return_code = process.poll()
            assert return_code is None, "App crashed on first launch"
            
            # App should create necessary directories
            data_dir = Path.home() / "Library/Application Support/NeuroBridge"
            assert data_dir.exists(), "App data directory not created"
            
            # Database should be initialized
            db_file = data_dir / "neurobridge.db"
            assert db_file.exists(), "Database not initialized"
            
        finally:
            process.terminate()
            process.wait()
    
    def test_app_lifecycle_management(self):
        """Test complete app lifecycle (launch, background, quit)"""
        app_path = Path("./dist/NeuroBridge.app/Contents/MacOS/NeuroBridge")
        
        # Launch app
        process = subprocess.Popen([str(app_path)])
        
        try:
            # Normal operation
            time.sleep(5)
            assert process.poll() is None, "App crashed during normal operation"
            
            # Simulate backgrounding (send SIGSTOP)
            process.send_signal(signal.SIGSTOP)
            time.sleep(2)
            
            # Resume (send SIGCONT)
            process.send_signal(signal.SIGCONT) 
            time.sleep(2)
            assert process.poll() is None, "App failed to resume from background"
            
            # Graceful shutdown (send SIGTERM)
            process.terminate()
            
            # Wait for clean shutdown
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pytest.fail("App didn't shut down gracefully")
                
        except Exception:
            process.kill()  # Force kill if something goes wrong
            raise
    
    def test_resource_cleanup_on_quit(self):
        """Test app properly cleans up resources on quit"""
        import psutil
        
        app_path = Path("./dist/NeuroBridge.app/Contents/MacOS/NeuroBridge")
        
        # Get initial resource baseline
        initial_processes = {p.pid for p in psutil.process_iter()}
        initial_temp_files = set(Path("/tmp").glob("neurobridge*"))
        
        # Launch and quit app
        process = subprocess.Popen([str(app_path)])
        time.sleep(5)
        
        # Get app's child processes
        app_process = psutil.Process(process.pid)
        child_pids = {child.pid for child in app_process.children(recursive=True)}
        
        # Quit app
        process.terminate()
        process.wait(timeout=10)
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # Check for zombie processes
        current_processes = {p.pid for p in psutil.process_iter()}
        zombie_processes = child_pids & current_processes
        
        assert len(zombie_processes) == 0, f"Zombie processes found: {zombie_processes}"
        
        # Check temp file cleanup
        current_temp_files = set(Path("/tmp").glob("neurobridge*"))
        leaked_files = current_temp_files - initial_temp_files
        
        assert len(leaked_files) == 0, f"Temp files not cleaned up: {leaked_files}"
```

### 6.2 Accessibility and Usability Testing

**Accessibility Compliance Framework:**

```python
# test_accessibility.py
import pytest
from selenium import webdriver
from axe_selenium_python import Axe

class TestAccessibility:
    @pytest.fixture(scope="class")
    def driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-web-security")
        driver = webdriver.Chrome(options=options)
        yield driver
        driver.quit()
    
    def test_wcag_compliance(self, driver, app_url):
        """Test Web Content Accessibility Guidelines compliance"""
        driver.get(app_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Run accessibility audit
        axe = Axe(driver)
        results = axe.run()
        
        # Check for violations
        violations = results["violations"]
        
        # Filter out minor violations if needed
        serious_violations = [v for v in violations if v["impact"] in ["serious", "critical"]]
        
        assert len(serious_violations) == 0, \
            f"Serious accessibility violations found: {[v['help'] for v in serious_violations]}"
    
    def test_keyboard_navigation(self, driver, app_url):
        """Test complete keyboard navigation"""
        from selenium.webdriver.common.keys import Keys
        
        driver.get(app_url)
        time.sleep(3)
        
        # Start with body focused
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
        
        # Tab through all interactive elements
        interactive_elements = []
        current_element = driver.switch_to.active_element
        
        for i in range(20):  # Limit to prevent infinite loops
            interactive_elements.append(current_element.tag_name)
            current_element.send_keys(Keys.TAB)
            
            new_element = driver.switch_to.active_element
            if new_element == current_element:
                break  # Reached end of tab order
            current_element = new_element
        
        # Should have tabbed through key interactive elements
        expected_elements = ["button", "input", "select", "textarea"]
        found_elements = set(interactive_elements)
        
        assert len(found_elements & set(expected_elements)) > 0, \
            "No interactive elements found in tab order"
    
    def test_screen_reader_compatibility(self, driver, app_url):
        """Test screen reader accessibility features"""
        driver.get(app_url)
        time.sleep(3)
        
        # Check for proper ARIA labels
        record_button = driver.find_element(By.ID, "record-button")
        assert record_button.get_attribute("aria-label") is not None, \
            "Record button missing aria-label"
        
        # Check for live regions (for transcription updates)
        live_regions = driver.find_elements(By.CSS_SELECTOR, "[aria-live]")
        assert len(live_regions) > 0, "No live regions found for dynamic content"
        
        # Check heading structure
        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
        assert len(headings) > 0, "No headings found for screen reader navigation"
```

## 7. Performance and Stress Testing

### 7.1 Load Testing Framework

**Comprehensive Performance Testing:**

```python
# test_load_performance.py
import pytest
import concurrent.futures
import time
import psutil
import requests
from threading import Event

class TestLoadPerformance:
    def test_concurrent_transcription_sessions(self, backend_server):
        """Test multiple simultaneous transcription sessions"""
        session_count = 10
        duration = 60  # Test for 1 minute
        
        session_results = []
        stop_event = Event()
        
        def transcription_session(session_id):
            """Single transcription session worker"""
            start_time = time.time()
            request_count = 0
            errors = 0
            
            while not stop_event.is_set() and (time.time() - start_time) < duration:
                try:
                    # Simulate regular audio chunk upload
                    with open("test_audio_chunk.wav", "rb") as audio:
                        response = requests.post(
                            "http://127.0.0.1:3939/api/transcribe/chunk",
                            files={"audio": audio},
                            timeout=30
                        )
                    
                    request_count += 1
                    if response.status_code != 200:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                
                time.sleep(2)  # 2 second chunks
            
            return {
                "session_id": session_id,
                "requests": request_count,
                "errors": errors,
                "duration": time.time() - start_time
            }
        
        # Start concurrent sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=session_count) as executor:
            futures = [executor.submit(transcription_session, i) for i in range(session_count)]
            
            # Let it run for the duration
            time.sleep(duration)
            stop_event.set()
            
            # Collect results
            session_results = [future.result() for future in futures]
        
        # Analyze results
        total_requests = sum(result["requests"] for result in session_results)
        total_errors = sum(result["errors"] for result in session_results)
        
        error_rate = total_errors / total_requests if total_requests > 0 else 1
        
        assert error_rate < 0.05, f"Error rate too high during load test: {error_rate:.1%}"
        assert total_requests > session_count * 20, "Too few requests processed during load test"
    
    def test_memory_stability_under_load(self, backend_server):
        """Test memory usage remains stable during extended operation"""
        # Get baseline memory usage
        backend_process = psutil.Process()  # Assumes we can get the backend process
        initial_memory = backend_process.memory_info().rss
        
        memory_samples = []
        test_duration = 300  # 5 minutes
        start_time = time.time()
        
        # Generate continuous load while monitoring memory
        def continuous_load():
            while time.time() - start_time < test_duration:
                try:
                    requests.post(
                        "http://127.0.0.1:3939/api/summaries/generate",
                        json={"transcript": "Test transcript " * 100},
                        timeout=30
                    )
                except:
                    pass  # Continue on errors
                time.sleep(1)
        
        import threading
        load_thread = threading.Thread(target=continuous_load)
        load_thread.daemon = True
        load_thread.start()
        
        # Monitor memory every 10 seconds
        while time.time() - start_time < test_duration:
            current_memory = backend_process.memory_info().rss
            memory_samples.append(current_memory)
            time.sleep(10)
        
        # Analyze memory stability
        memory_growth = max(memory_samples) - min(memory_samples)
        memory_growth_mb = memory_growth / 1024 / 1024
        
        # Memory should not grow more than 100MB during test
        assert memory_growth_mb < 100, f"Memory grew by {memory_growth_mb:.1f}MB during load test"
    
    def test_database_performance_under_load(self, backend_server):
        """Test database performance with concurrent operations"""
        concurrent_operations = 50
        
        def database_operation(op_id):
            try:
                # Test student creation/retrieval operations
                response = requests.post(
                    "http://127.0.0.1:3939/api/students/",
                    json={
                        "name": f"Test Student {op_id}",
                        "email": f"test{op_id}@example.com"
                    },
                    timeout=10
                )
                return response.status_code == 200
            except:
                return False
        
        # Execute concurrent database operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(database_operation, i) 
                      for i in range(concurrent_operations)]
            
            results = [future.result() for future in futures]
        
        success_rate = sum(results) / len(results)
        assert success_rate > 0.95, f"Database operation success rate too low: {success_rate:.1%}"
```

## 8. Regression Testing and CI Integration

### 8.1 Automated Regression Test Suite

**CI/CD Integration Framework:**

```yaml
# .github/workflows/macos-testing.yml
name: macOS App Testing

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-macos:
    runs-on: macos-latest
    strategy:
      matrix:
        architecture: [arm64, x86_64]
        
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install testing dependencies
      run: |
        pip install pytest pytest-xvfb selenium axe-selenium-python
        pip install -r python_backend/requirements.txt
    
    - name: Build macOS App Bundle
      run: |
        ./scripts/build_macos_app.sh --arch ${{ matrix.architecture }}
    
    - name: Run Bundle Structure Tests
      run: |
        pytest test_bundle_structure.py -v
    
    - name: Run Security Validation Tests
      run: |
        pytest test_security_validation.py -v
    
    - name: Run Performance Benchmarks
      run: |
        pytest test_performance_benchmarks.py -v --benchmark-only
    
    - name: Run Integration Tests
      run: |
        pytest test_frontend_integration.py -v --maxfail=5
    
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results-${{ matrix.architecture }}
        path: |
          test-results/
          logs/
          screenshots/
```

### 8.2 Performance Regression Detection

**Automated Performance Monitoring:**

```python
# test_performance_regression.py
import pytest
import json
import statistics
from pathlib import Path

class TestPerformanceRegression:
    @pytest.fixture(scope="class")
    def baseline_metrics(self):
        """Load baseline performance metrics"""
        baseline_file = Path("test_data/performance_baseline.json")
        
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        else:
            # Return default baseline if file doesn't exist
            return {
                "app_startup_time": 8.0,
                "transcription_latency_p95": 5.0,
                "memory_usage_max": 400,
                "cpu_usage_avg": 45.0
            }
    
    def test_startup_time_regression(self, baseline_metrics):
        """Test app startup time hasn't regressed"""
        # Measure current startup time (implementation would go here)
        current_startup_time = self.measure_app_startup_time()
        
        baseline = baseline_metrics["app_startup_time"]
        regression_threshold = 1.2  # 20% regression threshold
        
        assert current_startup_time < baseline * regression_threshold, \
            f"Startup time regressed: {current_startup_time:.2f}s vs baseline {baseline:.2f}s"
    
    def test_transcription_latency_regression(self, baseline_metrics):
        """Test transcription latency hasn't regressed"""
        # Run transcription benchmark
        latencies = self.run_transcription_benchmark()
        
        if latencies:
            current_p95 = statistics.quantiles(latencies, n=20)[18]
            baseline_p95 = baseline_metrics["transcription_latency_p95"]
            
            regression_threshold = 1.3  # 30% regression threshold
            
            assert current_p95 < baseline_p95 * regression_threshold, \
                f"Transcription latency regressed: P95 {current_p95:.2f}s vs baseline {baseline_p95:.2f}s"
    
    def test_memory_usage_regression(self, baseline_metrics):
        """Test memory usage hasn't regressed"""
        max_memory_mb = self.measure_peak_memory_usage()
        
        baseline_memory = baseline_metrics["memory_usage_max"]
        regression_threshold = 1.25  # 25% regression threshold
        
        assert max_memory_mb < baseline_memory * regression_threshold, \
            f"Memory usage regressed: {max_memory_mb}MB vs baseline {baseline_memory}MB"
    
    def update_baseline_metrics(self):
        """Update baseline metrics file with current measurements"""
        new_metrics = {
            "app_startup_time": self.measure_app_startup_time(),
            "transcription_latency_p95": statistics.quantiles(
                self.run_transcription_benchmark(), n=20
            )[18],
            "memory_usage_max": self.measure_peak_memory_usage(),
            "cpu_usage_avg": self.measure_average_cpu_usage()
        }
        
        baseline_file = Path("test_data/performance_baseline.json")
        baseline_file.parent.mkdir(exist_ok=True)
        
        with open(baseline_file, 'w') as f:
            json.dump(new_metrics, f, indent=2)
```

## 9. Release Validation Procedures

### 9.1 Pre-Release Validation Checklist

**Complete Release Validation Framework:**

```python
# test_release_validation.py
import pytest
import subprocess
import plistlib
from pathlib import Path

class TestReleaseValidation:
    """Comprehensive pre-release validation suite"""
    
    def test_version_consistency(self):
        """Verify version numbers are consistent across all files"""
        app_bundle = Path("./dist/NeuroBridge.app")
        
        # Get version from Info.plist
        plist_path = app_bundle / "Contents/Info.plist"
        with open(plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        bundle_version = plist_data["CFBundleShortVersionString"]
        
        # Check version in package.json
        import json
        with open("package.json") as f:
            package_data = json.load(f)
        
        package_version = package_data["version"]
        
        assert bundle_version == package_version, \
            f"Version mismatch: bundle={bundle_version}, package={package_version}"
    
    def test_code_signing_complete(self):
        """Verify all binaries and frameworks are properly signed"""
        app_bundle = Path("./dist/NeuroBridge.app")
        
        # Find all executable files
        executables = []
        for path in app_bundle.rglob("*"):
            if path.is_file() and (path.suffix in ['.dylib', '.so', ''] or 
                                  'MacOS' in str(path) or 
                                  'Frameworks' in str(path)):
                result = subprocess.run(['file', str(path)], 
                                       capture_output=True, text=True)
                if 'Mach-O' in result.stdout:
                    executables.append(path)
        
        # Check each executable is signed
        unsigned_files = []
        for executable in executables:
            result = subprocess.run(['codesign', '-v', str(executable)], 
                                   capture_output=True)
            if result.returncode != 0:
                unsigned_files.append(executable)
        
        assert len(unsigned_files) == 0, \
            f"Unsigned executables found: {unsigned_files}"
    
    def test_notarization_status(self):
        """Verify app is properly notarized"""
        app_bundle = Path("./dist/NeuroBridge.app")
        
        result = subprocess.run([
            'spctl', '--assess', '--verbose', str(app_bundle)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Notarization check failed: {result.stderr}"
        assert "accepted" in result.stderr, "App not accepted by Gatekeeper"
    
    def test_required_entitlements_present(self):
        """Verify all required entitlements are present"""
        app_bundle = Path("./dist/NeuroBridge.app")
        
        result = subprocess.run([
            'codesign', '--display', '--entitlements', '-', str(app_bundle)
        ], capture_output=True, text=True)
        
        required_entitlements = [
            "com.apple.security.device.microphone",
            "com.apple.security.network.server", 
            "com.apple.security.network.client",
            "com.apple.security.files.user-selected.read-write"
        ]
        
        missing_entitlements = []
        for entitlement in required_entitlements:
            if entitlement not in result.stdout:
                missing_entitlements.append(entitlement)
        
        assert len(missing_entitlements) == 0, \
            f"Missing required entitlements: {missing_entitlements}"
    
    def test_installer_package_creation(self):
        """Test creation of installer package"""
        app_bundle = Path("./dist/NeuroBridge.app")
        
        # Create installer package
        result = subprocess.run([
            'pkgbuild',
            '--root', str(app_bundle.parent),
            '--identifier', 'com.neurobridge.app',
            '--version', '1.0.0',
            '--install-location', '/Applications',
            './dist/NeuroBridge.pkg'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Package creation failed: {result.stderr}"
        
        pkg_path = Path("./dist/NeuroBridge.pkg")
        assert pkg_path.exists(), "Package file not created"
        assert pkg_path.stat().st_size > 100000, "Package file too small"
```

### 9.2 Final Integration Test Suite

**End-to-End Release Validation:**

```python
# test_e2e_release.py
import pytest
import subprocess
import time
import requests
from pathlib import Path

class TestEndToEndRelease:
    """Complete end-to-end testing of the released app"""
    
    @pytest.fixture(scope="class")
    def installed_app(self):
        """Install app from package and return installation info"""
        pkg_path = Path("./dist/NeuroBridge.pkg")
        
        # Install package
        result = subprocess.run([
            'sudo', 'installer', '-pkg', str(pkg_path), '-target', '/'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Installation failed: {result.stderr}"
        
        app_path = Path("/Applications/NeuroBridge.app")
        assert app_path.exists(), "App not installed to /Applications"
        
        yield app_path
        
        # Cleanup: remove installed app
        subprocess.run(['sudo', 'rm', '-rf', str(app_path)])
    
    def test_fresh_install_first_launch(self, installed_app):
        """Test first launch of freshly installed app"""
        # Launch app
        process = subprocess.Popen([
            str(installed_app / "Contents/MacOS/NeuroBridge")
        ])
        
        try:
            # Wait for app to initialize
            time.sleep(15)
            
            # Check app is running
            assert process.poll() is None, "App crashed on first launch"
            
            # Check backend is responding
            for attempt in range(30):
                try:
                    response = requests.get("http://localhost:3939/health", timeout=2)
                    if response.status_code == 200:
                        break
                except:
                    pass
                time.sleep(1)
            else:
                pytest.fail("Backend not responding after first launch")
            
            # Check frontend is accessible
            response = requests.get("http://localhost:3939", timeout=5)
            assert response.status_code == 200, "Frontend not accessible"
            
        finally:
            process.terminate()
            process.wait(timeout=10)
    
    def test_complete_user_workflow(self, installed_app):
        """Test complete user workflow from installation to summary export"""
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Launch app
        process = subprocess.Popen([
            str(installed_app / "Contents/MacOS/NeuroBridge")
        ])
        
        try:
            time.sleep(10)
            
            # Setup Chrome driver with mic permissions
            options = webdriver.ChromeOptions()
            options.add_argument("--use-fake-ui-for-media-stream")
            options.add_argument("--use-fake-device-for-media-stream")
            
            driver = webdriver.Chrome(options=options)
            
            try:
                # Navigate to app
                driver.get("http://localhost:3939")
                
                wait = WebDriverWait(driver, 15)
                
                # Test recording workflow
                record_button = wait.until(
                    EC.element_to_be_clickable((By.id, "record-button"))
                )
                record_button.click()
                
                # Simulate recording for a few seconds
                time.sleep(5)
                
                # Stop recording
                stop_button = wait.until(
                    EC.element_to_be_clickable((By.id, "stop-button"))
                )
                stop_button.click()
                
                # Generate summary
                summary_button = wait.until(
                    EC.element_to_be_clickable((By.id, "generate-summary"))
                )
                summary_button.click()
                
                # Wait for summary generation
                summary_content = wait.until(
                    EC.presence_of_element_located((By.class_name, "summary-content"))
                )
                
                assert len(summary_content.text) > 0, "Summary not generated"
                
                # Test export functionality
                export_button = wait.until(
                    EC.element_to_be_clickable((By.id, "export-summary"))
                )
                export_button.click()
                
                # Should trigger download
                time.sleep(2)
                
            finally:
                driver.quit()
                
        finally:
            process.terminate()
            process.wait()
    
    def test_uninstall_cleanup(self, installed_app):
        """Test app uninstall leaves no residual files"""
        # Note where app data might be stored
        data_locations = [
            Path.home() / "Library/Application Support/NeuroBridge",
            Path.home() / "Library/Preferences/com.neurobridge.app.plist",
            Path.home() / "Library/Logs/NeuroBridge",
        ]
        
        # Launch app briefly to create data files
        process = subprocess.Popen([
            str(installed_app / "Contents/MacOS/NeuroBridge")
        ])
        time.sleep(5)
        process.terminate()
        process.wait()
        
        # Remove app
        subprocess.run(['sudo', 'rm', '-rf', str(installed_app)])
        
        # Check for leftover files (this is informational)
        leftover_files = []
        for location in data_locations:
            if location.exists():
                leftover_files.append(location)
        
        if leftover_files:
            print(f"Note: Leftover files found (expected): {leftover_files}")
```

## 10. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Set up testing infrastructure and CI/CD pipeline
- Implement app bundle structure validation
- Create security validation framework
- Establish performance baseline metrics

### Phase 2: Core Testing (Weeks 3-4) 
- Implement embedded Python environment tests
- Create FastAPI backend integration tests
- Develop audio processing pipeline tests
- Set up real-time communication testing

### Phase 3: User Experience (Weeks 5-6)
- Build frontend integration test suite
- Implement accessibility testing framework
- Create user experience and lifecycle tests
- Develop cross-platform compatibility tests

### Phase 4: Performance & Scale (Weeks 7-8)
- Implement load testing framework
- Create memory and performance monitoring
- Set up regression detection system
- Build comprehensive benchmarking suite

### Phase 5: Release Validation (Weeks 9-10)
- Create pre-release validation procedures
- Implement end-to-end release testing
- Set up automated quality gates
- Document release validation process

## Conclusion

This comprehensive testing strategy ensures NeuroBridge EDU meets the highest quality standards for macOS desktop applications. By addressing the unique challenges of hybrid apps with embedded Python environments and following Apple's best practices, this framework provides confidence in the app's reliability, performance, and user experience across all supported macOS configurations.

The strategy emphasizes automation where possible while recognizing the need for manual testing in areas like accessibility and user experience. Regular execution of these tests, combined with continuous integration practices, will maintain consistent quality throughout the development lifecycle.