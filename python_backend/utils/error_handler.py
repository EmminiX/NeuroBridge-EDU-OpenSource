"""
Enhanced error handling and logging system
Provides comprehensive error tracking and debugging
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
import json

# Configure detailed error logger
error_logger = logging.getLogger("error_handler")
error_logger.setLevel(logging.DEBUG)

# File handler for error logs
file_handler = logging.FileHandler("./logs/errors.log", mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
    'File: %(pathname)s:%(lineno)d\n'
    'Function: %(funcName)s\n'
    '---'
)
file_handler.setFormatter(file_formatter)
error_logger.addHandler(file_handler)

# Console handler for immediate visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter(
    '❌ %(levelname)s: %(message)s'
)
console_handler.setFormatter(console_formatter)
error_logger.addHandler(console_handler)


class ErrorHandler:
    """Comprehensive error handling for the application"""
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Log error with full context and stack trace
        
        Args:
            error: The exception that occurred
            context: Additional context information
            request: FastAPI request object if available
            
        Returns:
            Error details dictionary
        """
        error_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        
        error_details = {
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }
        
        # Add request details if available
        if request:
            error_details["request"] = {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None
            }
        
        # Log to file with full details
        error_logger.error(
            f"Error {error_id}: {error}",
            extra={"error_details": json.dumps(error_details, indent=2)}
        )
        
        return error_details
    
    @staticmethod
    def create_error_response(
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Create standardized error response
        
        Args:
            status_code: HTTP status code
            message: User-friendly error message
            details: Additional error details
            error_id: Unique error identifier
            
        Returns:
            JSONResponse with error information
        """
        response_data = {
            "success": False,
            "error": {
                "message": message,
                "code": status_code,
                "error_id": error_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if details:
            response_data["error"]["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors
    
    Args:
        request: FastAPI request object
        exc: The exception that occurred
        
    Returns:
        JSONResponse with error details
    """
    error_details = ErrorHandler.log_error(
        error=exc,
        context={"endpoint": str(request.url.path)},
        request=request
    )
    
    # Don't expose internal details in production
    message = "An internal server error occurred"
    if hasattr(exc, 'detail'):
        message = exc.detail
    
    return ErrorHandler.create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_id=error_details["error_id"]
    )


def log_api_error(
    endpoint: str,
    error: Exception,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Convenience function for logging API errors
    
    Args:
        endpoint: API endpoint where error occurred
        error: The exception
        additional_context: Extra context information
    """
    context = {"endpoint": endpoint}
    if additional_context:
        context.update(additional_context)
    
    ErrorHandler.log_error(error=error, context=context)