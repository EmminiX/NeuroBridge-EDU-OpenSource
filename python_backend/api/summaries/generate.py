"""
Summary Generation Endpoint
Generates AI summaries without database storage
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.openai.summarize import summarization_service
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("summaries.generate")


class GenerateSummaryRequest(BaseModel):
    """Request schema for summary generation"""
    transcript: str
    title: Optional[str] = None
    subject: Optional[str] = None
    saveToDatabase: bool = False  # Keep for compatibility but ignore
    options: Optional[Dict[str, Any]] = None


@router.post("/generate")
async def generate_summary(request: GenerateSummaryRequest):
    """
    Generate AI summary from transcript without database storage
    
    Args:
        request: GenerateSummaryRequest with transcript and optional parameters
        
    Returns:
        Generated summary with metadata
    """
    try:
        # Validate transcript
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript is required")
        
        # Generate summary using AI service
        result = await summarization_service.summarize_transcript(
            transcript=request.transcript,
            title=request.title,
            context=request.subject,
            custom_instructions=request.options.get("instructions") if request.options else None
        )
        
        # Generate title if not provided
        title = request.title
        if not title:
            title = await summarization_service.generate_title(result["summary"])
        
        # Return summary without database ID
        return {
            "success": True,
            "data": {
                "content": result["summary"],
                "title": title,
                "created_at": None,  # No database timestamp
                "metadata": result.get("metadata", {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")