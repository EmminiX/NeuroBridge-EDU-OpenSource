"""
Configuration package for NeuroBridge EDU backend
"""

from .security import get_security_config, validate_security_setup

# Import the settings instance from the parent config module
import sys
import os

# Add the parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the settings from config.py
try:
    from config import settings
except ImportError:
    # Create a minimal fallback settings object
    from pydantic_settings import BaseSettings
    
    from typing import Optional
    
    from typing import List
    
    class FallbackSettings(BaseSettings):
        LOG_LEVEL: str = "INFO"
        HOST: str = "0.0.0.0"
        PORT: int = 3939
        DATABASE_PATH: str = "../data/neurobridge.db"
        LOCAL_WHISPER_ENABLED: bool = True
        LOCAL_WHISPER_MODEL_SIZE: str = "base"
        LOCAL_WHISPER_DEVICE: Optional[str] = None
        TRANSCRIPTION_METHOD: str = "local_first"
        OPENAI_API_KEY: Optional[str] = None
        WHISPER_CACHE: Optional[str] = None
        CORS_ORIGINS: str = "http://localhost:3131,http://localhost:3939"
        
        @property
        def cors_origins_list(self) -> List[str]:
            """Convert CORS_ORIGINS string to list"""
            if isinstance(self.CORS_ORIGINS, str):
                return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
            return self.CORS_ORIGINS if self.CORS_ORIGINS else ["http://localhost:3131", "http://localhost:3939"]
        
    settings = FallbackSettings()

__all__ = [
    'get_security_config',
    'validate_security_setup',
    'settings'
]