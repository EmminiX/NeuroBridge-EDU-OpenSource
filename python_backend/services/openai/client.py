"""
OpenAI client initialization and configuration
Provides async OpenAI client with user-provided API keys via encrypted storage
"""

import os
from typing import Optional
from openai import AsyncOpenAI
from config import settings
import logging

from services.api_key_manager import get_api_key_manager, APIKeyManager

logger = logging.getLogger(__name__)


class OpenAIClientManager:
    """
    Manages OpenAI client instance with user-provided API keys
    
    Features:
    - Dynamic client initialization with user API keys
    - API key validation via encrypted storage
    - Connection health checking
    - Proper client lifecycle management
    """
    
    def __init__(self):
        self._clients: dict[str, AsyncOpenAI] = {}
        self._api_key_manager: Optional[APIKeyManager] = None
    
    async def initialize_key_manager(self):
        """Initialize the API key manager if not already done"""
        if not self._api_key_manager:
            self._api_key_manager = await get_api_key_manager()
    
    async def get_client_for_key(self, key_id: str) -> Optional[AsyncOpenAI]:
        """
        Get OpenAI client for a specific API key
        
        Args:
            key_id: The stored key ID to use
            
        Returns:
            AsyncOpenAI: The initialized client or None if key not found
        """
        try:
            await self.initialize_key_manager()
            
            # Check if we already have a client for this key
            if key_id in self._clients:
                return self._clients[key_id]
            
            # Retrieve the API key
            api_key = await self._api_key_manager.retrieve_api_key(key_id)
            if not api_key:
                logger.error(f"API key not found: {key_id}")
                return None
            
            # Create new client
            client = AsyncOpenAI(api_key=api_key)
            
            # Test the client with a simple call
            await client.models.list()
            
            # Cache the client
            self._clients[key_id] = client
            
            # Clear API key from memory
            api_key = "0" * len(api_key)
            
            logger.info(f"OpenAI client initialized for key: {key_id}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for key {key_id}: {e}")
            return None
    
    async def get_default_client(self) -> Optional[AsyncOpenAI]:
        """
        Get the default OpenAI client (first available OpenAI key)
        
        Returns:
            AsyncOpenAI: The initialized client or None if no keys available
        """
        try:
            await self.initialize_key_manager()
            
            # Get list of stored keys
            keys = await self._api_key_manager.list_api_keys()
            
            # Find first OpenAI key
            openai_keys = [k for k, v in keys.items() if v.get("provider") == "openai" and v.get("status") == "active"]
            
            if not openai_keys:
                # Fall back to environment/config if no stored keys
                return await self._try_fallback_initialization()
            
            # Use first available key
            default_key_id = openai_keys[0]
            return await self.get_client_for_key(default_key_id)
            
        except Exception as e:
            logger.error(f"Failed to get default OpenAI client: {e}")
            return await self._try_fallback_initialization()
    
    async def _try_fallback_initialization(self) -> Optional[AsyncOpenAI]:
        """Try to initialize with environment/config API key as fallback"""
        try:
            api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("No OpenAI API key found in stored keys or environment")
                return None
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Test connection
            await client.models.list()
            
            logger.info("OpenAI client initialized with environment/config key")
            return client
            
        except Exception as e:
            logger.error(f"Fallback initialization failed: {e}")
            return None
    
    async def health_check(self, key_id: Optional[str] = None) -> bool:
        """
        Perform health check on OpenAI client connection
        
        Args:
            key_id: Optional specific key to test, otherwise uses default
            
        Returns:
            bool: True if client is healthy, False otherwise
        """
        try:
            client = await self.get_client_for_key(key_id) if key_id else await self.get_default_client()
            
            if not client:
                return False
            
            # Simple API call to verify connection
            models = await client.models.list()
            return len(list(models)) > 0
            
        except Exception as e:
            logger.error(f"OpenAI client health check failed: {e}")
            return False
    
    async def list_available_keys(self) -> list[dict]:
        """
        List available OpenAI keys
        
        Returns:
            List of available key metadata
        """
        try:
            await self.initialize_key_manager()
            keys = await self._api_key_manager.list_api_keys()
            
            return [
                {
                    "key_id": k,
                    "label": v.get("label"),
                    "created_at": v.get("created_at"),
                    "last_used_at": v.get("last_used_at")
                }
                for k, v in keys.items()
                if v.get("provider") == "openai" and v.get("status") == "active"
            ]
            
        except Exception as e:
            logger.error(f"Failed to list available keys: {e}")
            return []
    
    async def close_all(self):
        """Close all OpenAI client connections"""
        for key_id, client in self._clients.items():
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client for key {key_id}: {e}")
        
        self._clients.clear()


# Global client manager instance
openai_manager = OpenAIClientManager()


async def get_openai_client(key_id: Optional[str] = None) -> AsyncOpenAI:
    """
    Dependency function to get OpenAI client
    
    Args:
        key_id: Optional specific key ID to use, otherwise uses default
    
    Returns:
        AsyncOpenAI: The initialized client
        
    Raises:
        RuntimeError: If no client can be initialized
    """
    client = await openai_manager.get_client_for_key(key_id) if key_id else await openai_manager.get_default_client()
    
    if not client:
        raise RuntimeError("No OpenAI API key available. Please store an API key first.")
    
    return client


async def get_default_openai_client() -> AsyncOpenAI:
    """
    Dependency function to get the default OpenAI client
    
    Returns:
        AsyncOpenAI: The initialized client with default key
        
    Raises:
        RuntimeError: If no client can be initialized
    """
    return await get_openai_client()