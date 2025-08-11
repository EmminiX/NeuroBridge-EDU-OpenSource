"""
Error logging endpoint for frontend error reporting
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("api.errors")
router = APIRouter()


class ErrorReport(BaseModel):
    """Frontend error report schema"""
    message: str
    stack: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/")
async def log_frontend_error(error: ErrorReport):
    """
    Log errors from frontend application
    
    Args:
        error: Error details from frontend
        
    Returns:
        Success confirmation
    """
    try:
        # Log the error with appropriate level
        if error.type == "critical":
            logger.error(f"Frontend critical error: {error.message}", extra={
                "stack": error.stack,
                "url": error.url,
                "userAgent": error.userAgent,
                "metadata": error.metadata
            })
        else:
            logger.warning(f"Frontend error: {error.message}", extra={
                "stack": error.stack,
                "url": error.url,
                "userAgent": error.userAgent,
                "metadata": error.metadata
            })
        
        return {
            "success": True,
            "message": "Error logged successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to log frontend error: {e}")
        raise HTTPException(status_code=500, detail="Failed to log error")