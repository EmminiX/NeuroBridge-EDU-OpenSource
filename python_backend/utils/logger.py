"""
Logging Configuration
Centralized logging setup for the application
"""

import logging
import sys
import os

# Simple fallback settings - will be overridden by setup_logging if needed
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


def setup_logging() -> None:
    """Configure application logging"""
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
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