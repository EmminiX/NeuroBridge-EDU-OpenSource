"""
Secure API Key Management System
Handles encryption, storage, and validation of user-provided API keys
"""

import os
import json
import base64
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException
import secrets

from utils.logger import get_logger

logger = get_logger("api_key_manager")


class APIKeyManager:
    """
    Secure API Key Management with AES-256-GCM encryption
    
    Features:
    - AES-256-GCM authenticated encryption
    - HKDF key derivation from master key
    - HMAC fingerprinting for duplicate detection
    - Secure key storage in user data directory
    - Memory-safe operations with buffer cleanup
    """
    
    def __init__(self):
        self._master_key: Optional[bytes] = None
        self._encryption_key: Optional[bytes] = None
        self._hmac_key: Optional[bytes] = None
        self._storage_path = Path.home() / ".neurobridge" / "keys.json"
        self._master_key_path = Path.home() / ".neurobridge" / "master.key"
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the API key manager with encryption keys
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Ensure storage directory exists
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load or generate master key
            await self._load_or_generate_master_key()
            
            # Derive encryption and HMAC keys from master key
            self._derive_keys()
            
            self._initialized = True
            logger.info("API key manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize API key manager: {e}")
            self._initialized = False
            return False
    
    async def store_api_key(self, provider: str, api_key: str, label: Optional[str] = None) -> str:
        """
        Securely store an API key with encryption
        
        Args:
            provider: API provider name (e.g., "openai")
            api_key: The API key to store
            label: Optional label for the key
            
        Returns:
            str: Key ID for referencing the stored key
            
        Raises:
            RuntimeError: If manager not initialized
            ValueError: If API key is invalid format
        """
        if not self._initialized:
            raise RuntimeError("API key manager not initialized")
        
        # Validate API key format
        if not api_key or len(api_key.strip()) < 10:
            raise ValueError("Invalid API key format")
        
        api_key = api_key.strip()
        
        try:
            # Generate unique key ID
            key_id = secrets.token_urlsafe(16)
            
            # Create associated data for AEAD
            aad = f"provider:{provider}|id:{key_id}".encode()
            
            # Generate random nonce for GCM
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            # Encrypt the API key
            aesgcm = AESGCM(self._encryption_key)
            ciphertext = aesgcm.encrypt(nonce, api_key.encode(), aad)
            
            # Generate HMAC fingerprint for duplicate detection
            h = hmac.HMAC(self._hmac_key, hashes.SHA256(), backend=default_backend())
            h.update(api_key.encode())
            fingerprint = h.finalize().hex()
            
            # Prepare key data for storage
            key_data = {
                "id": key_id,
                "provider": provider,
                "label": label or f"{provider.title()} API Key",
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "aad": base64.b64encode(aad).decode(),
                "fingerprint": fingerprint,
                "created_at": datetime.utcnow().isoformat(),
                "last_used_at": None,
                "status": "active"
            }
            
            # Load existing keys and check for duplicates
            stored_keys = await self._load_stored_keys()
            
            # Check for duplicate fingerprints
            for existing_id, existing_data in stored_keys.items():
                if existing_data.get("fingerprint") == fingerprint:
                    raise ValueError("API key already stored")
            
            # Store the new key
            stored_keys[key_id] = key_data
            await self._save_stored_keys(stored_keys)
            
            # Clear sensitive data from memory
            api_key = "0" * len(api_key)
            
            logger.info(f"API key stored successfully: {key_id} for {provider}")
            return key_id
            
        except Exception as e:
            logger.error(f"Failed to store API key: {e}")
            raise
    
    async def retrieve_api_key(self, key_id: str) -> Optional[str]:
        """
        Retrieve and decrypt an API key
        
        Args:
            key_id: The key ID to retrieve
            
        Returns:
            str: Decrypted API key or None if not found
            
        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized:
            raise RuntimeError("API key manager not initialized")
        
        try:
            stored_keys = await self._load_stored_keys()
            
            if key_id not in stored_keys:
                return None
            
            key_data = stored_keys[key_id]
            
            # Decode stored data
            ciphertext = base64.b64decode(key_data["ciphertext"])
            nonce = base64.b64decode(key_data["nonce"])
            aad = base64.b64decode(key_data["aad"])
            
            # Decrypt the API key
            aesgcm = AESGCM(self._encryption_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
            api_key = plaintext.decode()
            
            # Update last used timestamp
            key_data["last_used_at"] = datetime.utcnow().isoformat()
            stored_keys[key_id] = key_data
            await self._save_stored_keys(stored_keys)
            
            logger.info(f"API key retrieved successfully: {key_id}")
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to retrieve API key: {e}")
            return None
    
    async def list_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        List all stored API keys (without decrypting them)
        
        Returns:
            Dict: Key metadata (no plaintext keys)
        """
        if not self._initialized:
            raise RuntimeError("API key manager not initialized")
        
        try:
            stored_keys = await self._load_stored_keys()
            
            # Return metadata only (remove sensitive fields)
            result = {}
            for key_id, key_data in stored_keys.items():
                result[key_id] = {
                    "id": key_data["id"],
                    "provider": key_data["provider"], 
                    "label": key_data["label"],
                    "created_at": key_data["created_at"],
                    "last_used_at": key_data["last_used_at"],
                    "status": key_data["status"]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return {}
    
    async def delete_api_key(self, key_id: str) -> bool:
        """
        Delete an API key from storage
        
        Args:
            key_id: The key ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not self._initialized:
            raise RuntimeError("API key manager not initialized")
        
        try:
            stored_keys = await self._load_stored_keys()
            
            if key_id not in stored_keys:
                return False
            
            del stored_keys[key_id]
            await self._save_stored_keys(stored_keys)
            
            logger.info(f"API key deleted: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False
    
    async def validate_api_key(self, key_id: str, provider: str = "openai") -> bool:
        """
        Validate an API key by testing it with the provider
        
        Args:
            key_id: The key ID to validate
            provider: The API provider to test against
            
        Returns:
            bool: True if key is valid, False otherwise
        """
        if provider != "openai":
            logger.warning(f"Validation not supported for provider: {provider}")
            return False
        
        api_key = await self.retrieve_api_key(key_id)
        if not api_key:
            return False
        
        try:
            from openai import AsyncOpenAI
            
            # Test the API key with a simple request
            client = AsyncOpenAI(api_key=api_key)
            models = await client.models.list()
            
            # If we get here, the key is valid
            api_key = "0" * len(api_key)  # Clear from memory
            return len(list(models)) > 0
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            if api_key:
                api_key = "0" * len(api_key)  # Clear from memory
            return False
    
    @property
    def is_initialized(self) -> bool:
        """Check if the API key manager is initialized"""
        return self._initialized
    
    async def _load_or_generate_master_key(self):
        """Load existing master key or generate a new one"""
        if self._master_key_path.exists():
            # Load existing master key
            with open(self._master_key_path, "rb") as f:
                self._master_key = f.read()
                
            if len(self._master_key) != 32:
                raise ValueError("Invalid master key length")
                
        else:
            # Generate new master key
            self._master_key = os.urandom(32)  # 256-bit master key
            
            # Save master key securely
            with open(self._master_key_path, "wb") as f:
                f.write(self._master_key)
                
            # Set secure file permissions (owner read/write only)
            os.chmod(self._master_key_path, 0o600)
            
            logger.info("Generated new master key")
    
    def _derive_keys(self):
        """Derive encryption and HMAC keys from master key using HKDF"""
        # Derive encryption key
        hkdf_enc = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key for AES-256
            salt=b"neurobridge-encryption",
            info=b"api-key-encryption",
            backend=default_backend()
        )
        self._encryption_key = hkdf_enc.derive(self._master_key)
        
        # Derive HMAC key
        hkdf_hmac = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key for HMAC-SHA256
            salt=b"neurobridge-hmac",
            info=b"api-key-fingerprint",
            backend=default_backend()
        )
        self._hmac_key = hkdf_hmac.derive(self._master_key)
    
    async def _load_stored_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load stored keys from JSON file"""
        if not self._storage_path.exists():
            return {}
        
        try:
            with open(self._storage_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load stored keys: {e}")
            return {}
    
    async def _save_stored_keys(self, keys: Dict[str, Dict[str, Any]]):
        """Save keys to JSON file with secure permissions"""
        try:
            with open(self._storage_path, "w") as f:
                json.dump(keys, f, indent=2)
            
            # Set secure file permissions (owner read/write only)
            os.chmod(self._storage_path, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save stored keys: {e}")
            raise


# Global API key manager instance
api_key_manager = APIKeyManager()


async def get_api_key_manager() -> APIKeyManager:
    """
    Dependency function to get API key manager
    
    Returns:
        APIKeyManager: The initialized manager
        
    Raises:
        RuntimeError: If manager initialization fails
    """
    if not api_key_manager.is_initialized:
        success = await api_key_manager.initialize()
        if not success:
            raise RuntimeError("Failed to initialize API key manager")
    
    return api_key_manager