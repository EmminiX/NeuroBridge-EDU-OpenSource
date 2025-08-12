"""
Configuration management using Pydantic BaseSettings
Environment variable driven configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional, List, Union
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 3939
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_PATH: str = "../data/neurobridge.db"
    
    # AI Services (Optional - users can store keys via API key management)
    OPENAI_API_KEY: Optional[str] = None
    
    # Local Whisper configuration
    LOCAL_WHISPER_ENABLED: bool = True
    LOCAL_WHISPER_MODEL_SIZE: str = "base"  # tiny, base, small, medium, large-v2, large-v3
    LOCAL_WHISPER_DEVICE: Optional[str] = None  # auto-detect if None, or "cpu", "cuda", "mps"
    TRANSCRIPTION_METHOD: str = "local_first"  # local_only, api_only, local_first, auto
    WHISPER_CACHE: Optional[str] = None  # Custom cache directory for models
    
    # CORS - accepts both list and comma-separated string
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3131", "http://localhost:3939", "http://localhost:8000"]
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    model_config = {
        "env_file": "../.env",  # Look for .env in project root
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra env vars
    }


settings = Settings()