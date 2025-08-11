"""
Logging Configuration
Centralized logging setup for the application
"""

import logging
import sys
from config import settings


def setup_logging() -> None:
    """Configure application logging"""
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Get application logger
    logger = logging.getLogger("neurobridge")
    logger.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(f"neurobridge.{name}")