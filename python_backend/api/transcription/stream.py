"""
Server-Sent Events Stream Endpoint  
GET /api/transcribe/stream/{session_id} - Real-time transcription results
"""

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from services.whisper.session import session_manager
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("transcription.stream")


class SSEClient:
    """SSE client wrapper for managing connections"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue = asyncio.Queue()
        self.connected = True
    
    async def send_json(self, data: dict):
        """Send JSON data to client via queue"""
        if self.connected:
            await self.queue.put(data)
    
    async def disconnect(self):
        """Mark client as disconnected"""
        self.connected = False
        await self.queue.put(None)  # Signal to close connection


@router.get("/stream/{session_id}")
async def stream_transcription_results(session_id: str, request: Request):
    """
    Server-Sent Events stream for real-time transcription results
    Client connects to receive live transcription updates as audio chunks are processed
    """
    try:
        # Create SSE client for this connection
        sse_client = SSEClient(session_id)
        
        # Register client with session manager
        success = await session_manager.add_sse_client(session_id, sse_client)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or inactive"
            )
        
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for transcription results"""
            try:
                # Send initial connection confirmation
                yield {
                    "event": "connected",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "status": "connected",
                        "message": "SSE stream established",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                }
                
                # Keep connection alive and process messages
                while sse_client.connected:
                    try:
                        # Wait for transcription results with timeout
                        data = await asyncio.wait_for(
                            sse_client.queue.get(),
                            timeout=30.0  # 30-second keepalive
                        )
                        
                        # Check for disconnect signal
                        if data is None:
                            logger.debug(f"SSE client disconnected for session {session_id}")
                            break
                        
                        # Send transcription result
                        yield {
                            "event": "transcription",
                            "data": json.dumps({
                                **data,
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        }
                        
                    except asyncio.TimeoutError:
                        # Send keepalive ping
                        yield {
                            "event": "keepalive",
                            "data": json.dumps({
                                "sessionId": session_id,
                                "status": "alive",
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        }
                        
                    except Exception as e:
                        logger.error(f"Error in SSE event generator for session {session_id}: {e}")
                        yield {
                            "event": "error",
                            "data": json.dumps({
                                "sessionId": session_id,
                                "error": str(e),
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        }
                        break
                
                # Send final disconnection message
                yield {
                    "event": "disconnected",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "status": "disconnected",
                        "message": "SSE stream closed",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                }
                
            except Exception as e:
                logger.error(f"SSE generator error for session {session_id}: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "sessionId": session_id,
                        "error": "Stream generator error",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                }
            
            finally:
                # Ensure client is marked as disconnected
                await sse_client.disconnect()
        
        logger.info(f"SSE stream established for session: {session_id}")
        
        # Return EventSourceResponse with proper headers
        return EventSourceResponse(
            event_generator(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to establish SSE stream for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to establish transcription stream: {str(e)}"
        )