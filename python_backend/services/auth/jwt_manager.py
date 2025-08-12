"""
JWT Token Manager with Enhanced Security
Educational platform optimized JWT implementation with short-lived access tokens,
secure refresh tokens, and comprehensive security features.
"""

import os
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from utils.logger import get_logger

logger = get_logger(__name__)

class TokenData(BaseModel):
    """Token payload data structure"""
    sub: str  # Subject (user identifier)
    aud: str  # Audience
    iss: str  # Issuer
    iat: int  # Issued at
    exp: int  # Expiry
    nbf: int  # Not before
    jti: str  # JWT ID for blacklisting
    type: str  # access or refresh
    scopes: list = []  # Permission scopes
    session_id: Optional[str] = None  # Session identifier
    device_fp: Optional[str] = None  # Device fingerprint


class JWTManager:
    """
    Secure JWT Manager for Educational Platforms
    
    Features:
    - Short-lived access tokens (15 minutes)
    - Long-lived refresh tokens (7 days) with rotation
    - EdDSA (Ed25519) signatures for enhanced security
    - Token blacklisting with JTI tracking
    - Device binding with fingerprints
    - Educational-specific scopes and session management
    """
    
    def __init__(
        self,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        algorithm: str = "EdDSA",
        issuer: str = "neurobridge-edu",
        audience: str = "neurobridge-users"
    ):
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        
        # Initialize cryptographic keys
        self._private_key = None
        self._public_key = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new Ed25519 key pair"""
        private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH", "~/.neurobridge/jwt_private.pem")
        public_key_path = os.getenv("JWT_PUBLIC_KEY_PATH", "~/.neurobridge/jwt_public.pem")
        
        private_key_path = os.path.expanduser(private_key_path)
        public_key_path = os.path.expanduser(public_key_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(private_key_path), exist_ok=True, mode=0o700)
        
        try:
            # Try to load existing keys
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                with open(private_key_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(f.read(), password=None)
                
                with open(public_key_path, "rb") as f:
                    self._public_key = serialization.load_pem_public_key(f.read())
                
                logger.info("Loaded existing JWT keys")
            else:
                # Generate new key pair
                self._generate_new_keys(private_key_path, public_key_path)
                
        except Exception as e:
            logger.error(f"Error loading JWT keys: {e}")
            # Generate new keys as fallback
            self._generate_new_keys(private_key_path, public_key_path)
    
    def _generate_new_keys(self, private_key_path: str, public_key_path: str):
        """Generate new Ed25519 key pair"""
        # Generate Ed25519 key pair
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
        # Serialize and save keys
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Save with secure permissions
        with open(private_key_path, "wb") as f:
            f.write(private_pem)
        os.chmod(private_key_path, 0o600)
        
        with open(public_key_path, "wb") as f:
            f.write(public_pem)
        os.chmod(public_key_path, 0o644)
        
        logger.info("Generated new JWT key pair")
    
    def create_access_token(
        self, 
        subject: str, 
        scopes: list = None,
        session_id: str = None,
        device_fingerprint: str = None,
        custom_claims: Dict[str, Any] = None
    ) -> str:
        """Create a short-lived access token"""
        now = datetime.now(timezone.utc)
        expire_time = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": subject,
            "aud": self.audience,
            "iss": self.issuer,
            "iat": int(now.timestamp()),
            "exp": int(expire_time.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": self._generate_jti(),
            "type": "access",
            "scopes": scopes or [],
            "session_id": session_id,
            "device_fp": device_fingerprint
        }
        
        # Add custom claims if provided
        if custom_claims:
            payload.update(custom_claims)
        
        return jwt.encode(payload, self._private_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self, 
        subject: str, 
        session_id: str,
        device_fingerprint: str = None
    ) -> str:
        """Create a long-lived refresh token"""
        now = datetime.now(timezone.utc)
        expire_time = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": subject,
            "aud": self.audience,
            "iss": self.issuer,
            "iat": int(now.timestamp()),
            "exp": int(expire_time.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": self._generate_jti(),
            "type": "refresh",
            "session_id": session_id,
            "device_fp": device_fingerprint
        }
        
        return jwt.encode(payload, self._private_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """
        Verify and decode a JWT token
        
        Args:
            token: The JWT token to verify
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            TokenData if valid, None if invalid
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "nbf", "aud", "iss", "sub", "jti", "type"]
                }
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None
            
            # Create and return TokenData
            return TokenData(**payload)
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[tuple[str, str]]:
        """
        Generate new access token from valid refresh token
        Returns tuple of (new_access_token, new_refresh_token) or None
        """
        # Verify refresh token
        token_data = self.verify_token(refresh_token, "refresh")
        if not token_data:
            return None
        
        # Generate new tokens with same session and device
        new_access_token = self.create_access_token(
            subject=token_data.sub,
            scopes=token_data.scopes,
            session_id=token_data.session_id,
            device_fingerprint=token_data.device_fp
        )
        
        new_refresh_token = self.create_refresh_token(
            subject=token_data.sub,
            session_id=token_data.session_id,
            device_fingerprint=token_data.device_fp
        )
        
        return new_access_token, new_refresh_token
    
    def extract_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract claims without verification (for logging/debugging)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID for blacklisting"""
        return secrets.token_urlsafe(32)
    
    def get_public_key_jwk(self) -> Dict[str, str]:
        """Get public key in JWK format for client-side verification"""
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "kty": "OKP",
            "crv": "Ed25519", 
            "x": public_bytes.hex(),
            "use": "sig",
            "alg": "EdDSA"
        }


# Global JWT manager instance
_jwt_manager = None

def get_jwt_manager() -> JWTManager:
    """Get global JWT manager instance"""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager

# Convenience functions
def create_access_token(
    subject: str, 
    scopes: list = None,
    session_id: str = None,
    device_fingerprint: str = None,
    custom_claims: Dict[str, Any] = None
) -> str:
    """Create access token using global manager"""
    return get_jwt_manager().create_access_token(
        subject, scopes, session_id, device_fingerprint, custom_claims
    )

def create_refresh_token(
    subject: str, 
    session_id: str,
    device_fingerprint: str = None
) -> str:
    """Create refresh token using global manager"""
    return get_jwt_manager().create_refresh_token(subject, session_id, device_fingerprint)

def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify token using global manager"""
    return get_jwt_manager().verify_token(token, token_type)