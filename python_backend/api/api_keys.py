"""
API Key Management Endpoints
Secure storage and management of user-provided API keys
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.api_key_manager import get_api_key_manager, APIKeyManager
from utils.logger import get_logger

router = APIRouter()
logger = get_logger("api_keys")


class APIKeyCreateRequest(BaseModel):
    """Request schema for storing an API key"""
    provider: str = Field(..., description="API provider name (e.g., 'openai')")
    api_key: str = Field(..., min_length=10, description="The API key to store")
    label: Optional[str] = Field(None, description="Optional label for the key")


class APIKeyResponse(BaseModel):
    """Response schema for API key operations"""
    id: str
    provider: str
    label: str
    created_at: str
    last_used_at: Optional[str]
    status: str


class APIKeyValidationResponse(BaseModel):
    """Response schema for API key validation"""
    valid: bool
    message: str
    tested_at: str


@router.post("/store", response_model=Dict[str, Any])
async def store_api_key(
    request: APIKeyCreateRequest,
    manager: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Store an encrypted API key
    
    Args:
        request: API key storage request
        manager: API key manager dependency
        
    Returns:
        Dict with success status and key ID
        
    Raises:
        HTTPException: 400 if validation fails, 500 if storage fails
    """
    try:
        # Validate provider
        if request.provider.lower() not in ["openai"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {request.provider}"
            )
        
        # Store the API key
        key_id = await manager.store_api_key(
            provider=request.provider.lower(),
            api_key=request.api_key,
            label=request.label
        )
        
        logger.info(f"API key stored successfully: {key_id}")
        
        return {
            "success": True,
            "data": {
                "key_id": key_id,
                "provider": request.provider.lower(),
                "label": request.label or f"{request.provider.title()} API Key",
                "message": "API key stored successfully"
            }
        }
        
    except ValueError as e:
        logger.warning(f"API key validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to store API key")


@router.get("/list", response_model=Dict[str, Any])
async def list_api_keys(
    manager: APIKeyManager = Depends(get_api_key_manager)
):
    """
    List all stored API keys (metadata only, no plaintext keys)
    
    Args:
        manager: API key manager dependency
        
    Returns:
        Dict with list of key metadata
    """
    try:
        keys = await manager.list_api_keys()
        
        return {
            "success": True,
            "data": {
                "keys": list(keys.values()),
                "count": len(keys)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.post("/validate/{key_id}", response_model=Dict[str, Any])
async def validate_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Validate an API key by testing it with the provider
    
    Args:
        key_id: The key ID to validate
        manager: API key manager dependency
        
    Returns:
        Dict with validation result
        
    Raises:
        HTTPException: 404 if key not found, 500 if validation fails
    """
    try:
        from datetime import datetime
        
        # Check if key exists first
        keys = await manager.list_api_keys()
        if key_id not in keys:
            raise HTTPException(status_code=404, detail="API key not found")
        
        key_info = keys[key_id]
        
        # Validate the key
        is_valid = await manager.validate_api_key(key_id, key_info["provider"])
        
        result = {
            "valid": is_valid,
            "message": "API key is valid" if is_valid else "API key is invalid or expired",
            "tested_at": datetime.utcnow().isoformat(),
            "provider": key_info["provider"]
        }
        
        logger.info(f"API key validation result for {key_id}: {is_valid}")
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate API key {key_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate API key")


@router.delete("/delete/{key_id}", response_model=Dict[str, Any])
async def delete_api_key(
    key_id: str,
    manager: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Delete an API key from storage
    
    Args:
        key_id: The key ID to delete
        manager: API key manager dependency
        
    Returns:
        Dict with deletion result
        
    Raises:
        HTTPException: 404 if key not found, 500 if deletion fails
    """
    try:
        deleted = await manager.delete_api_key(key_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="API key not found")
        
        logger.info(f"API key deleted successfully: {key_id}")
        
        return {
            "success": True,
            "data": {
                "key_id": key_id,
                "message": "API key deleted successfully"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key {key_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.get("/health", response_model=Dict[str, Any])
async def api_key_system_health(
    manager: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Check the health of the API key management system
    
    Args:
        manager: API key manager dependency
        
    Returns:
        Dict with system health status
    """
    try:
        keys = await manager.list_api_keys()
        
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "initialized": manager.is_initialized,
                "stored_keys_count": len(keys),
                "message": "API key management system is operational"
            }
        }
        
    except Exception as e:
        logger.error(f"API key system health check failed: {e}")
        raise HTTPException(status_code=500, detail="API key system unhealthy")


@router.get("/providers", response_model=Dict[str, Any])
async def list_supported_providers():
    """
    List supported API providers
    
    Returns:
        Dict with list of supported providers
    """
    providers = {
        "openai": {
            "name": "OpenAI",
            "description": "OpenAI GPT and Whisper APIs",
            "key_format": "sk-...",
            "validation_supported": True
        }
    }
    
    return {
        "success": True,
        "data": {
            "providers": providers,
            "count": len(providers)
        }
    }