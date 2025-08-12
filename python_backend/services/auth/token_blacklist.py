"""
JWT Token Blacklist Management
Redis-based token revocation system for logout and security events
"""

import json
import time
from typing import Optional, Set, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from utils.logger import get_logger

logger = get_logger(__name__)

class TokenBlacklist:
    """
    Token blacklisting system for secure logout and security events
    
    Features:
    - Redis-based storage with automatic expiration
    - Memory fallback for high availability
    - Bulk blacklisting for security incidents
    - Educational session tracking
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_url = redis_url
        self.redis_client = None
        
        # In-memory fallback for when Redis is unavailable
        self.memory_blacklist: Set[str] = set()
        self.memory_expiry: Dict[str, float] = {}
        self.last_cleanup = time.time()
        
        # Blacklist reasons for auditing
        self.LOGOUT = "logout"
        self.SECURITY_INCIDENT = "security_incident"
        self.PASSWORD_RESET = "password_reset"
        self.ACCOUNT_DISABLED = "account_disabled"
        self.SESSION_EXPIRED = "session_expired"
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection handling"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Connected to Redis for token blacklist")
            except Exception as e:
                logger.warning(f"Redis connection failed for blacklist: {e}")
                self.redis_client = None
        return self.redis_client
    
    async def blacklist_token(
        self, 
        jti: str, 
        exp_timestamp: int, 
        reason: str = None,
        user_id: str = None,
        session_id: str = None
    ) -> bool:
        """
        Add token to blacklist
        
        Args:
            jti: JWT ID to blacklist
            exp_timestamp: Token expiration timestamp
            reason: Reason for blacklisting (for audit)
            user_id: User identifier
            session_id: Session identifier
        """
        try:
            redis_client = await self._get_redis_client()
            
            # Calculate TTL (time until token would naturally expire)
            current_time = int(time.time())
            ttl = max(exp_timestamp - current_time, 0)
            
            if ttl == 0:
                # Token already expired, no need to blacklist
                return True
            
            blacklist_data = {
                "jti": jti,
                "blacklisted_at": current_time,
                "expires_at": exp_timestamp,
                "reason": reason or self.LOGOUT,
                "user_id": user_id,
                "session_id": session_id
            }
            
            if redis_client:
                # Store in Redis with automatic expiration
                await redis_client.setex(
                    f"bl:{jti}", 
                    ttl, 
                    json.dumps(blacklist_data)
                )
                logger.info(f"Token {jti[:8]}... blacklisted in Redis: {reason}")
            else:
                # Fallback to memory storage
                self.memory_blacklist.add(jti)
                self.memory_expiry[jti] = exp_timestamp
                logger.info(f"Token {jti[:8]}... blacklisted in memory: {reason}")
            
            # Log security event
            logger.info(
                "Token blacklisted",
                extra={
                    "event": "token_blacklisted",
                    "jti": jti[:8] + "...",  # Truncated for security
                    "reason": reason,
                    "user_id": user_id,
                    "session_id": session_id,
                    "ttl": ttl
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti[:8]}...: {e}")
            return False
    
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Check Redis
                result = await redis_client.get(f"bl:{jti}")
                return result is not None
            else:
                # Check memory fallback
                self._cleanup_memory_blacklist()
                return jti in self.memory_blacklist
                
        except Exception as e:
            logger.error(f"Failed to check blacklist for {jti[:8]}...: {e}")
            # Fail secure - assume blacklisted if we can't check
            return True
    
    async def blacklist_user_tokens(
        self, 
        user_id: str, 
        reason: str = None,
        exclude_jti: str = None
    ) -> int:
        """
        Blacklist all tokens for a user (useful for security incidents)
        Returns number of tokens blacklisted
        """
        try:
            redis_client = await self._get_redis_client()
            reason = reason or self.SECURITY_INCIDENT
            
            if not redis_client:
                logger.warning("Cannot blacklist user tokens without Redis")
                return 0
            
            # Find all active tokens for user
            # This requires storing user->token mapping (implemented separately)
            pattern = f"user_token:{user_id}:*"
            keys = await redis_client.keys(pattern)
            
            blacklisted_count = 0
            current_time = int(time.time())
            
            for key in keys:
                try:
                    token_data = await redis_client.get(key)
                    if token_data:
                        token_info = json.loads(token_data)
                        jti = token_info.get("jti")
                        exp = token_info.get("exp")
                        
                        # Skip the token we want to keep (e.g., the one used for this request)
                        if exclude_jti and jti == exclude_jti:
                            continue
                        
                        if jti and exp and exp > current_time:
                            await self.blacklist_token(
                                jti=jti,
                                exp_timestamp=exp,
                                reason=reason,
                                user_id=user_id
                            )
                            blacklisted_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing token key {key}: {e}")
                    continue
            
            logger.info(
                f"Blacklisted {blacklisted_count} tokens for user {user_id}",
                extra={
                    "event": "bulk_token_blacklist",
                    "user_id": user_id,
                    "reason": reason,
                    "count": blacklisted_count
                }
            )
            
            return blacklisted_count
            
        except Exception as e:
            logger.error(f"Failed to blacklist user tokens: {e}")
            return 0
    
    async def blacklist_session_tokens(
        self, 
        session_id: str, 
        reason: str = None
    ) -> int:
        """
        Blacklist all tokens for a session
        Returns number of tokens blacklisted
        """
        try:
            redis_client = await self._get_redis_client()
            reason = reason or self.SESSION_EXPIRED
            
            if not redis_client:
                logger.warning("Cannot blacklist session tokens without Redis")
                return 0
            
            # Find all tokens for session
            pattern = f"session_token:{session_id}:*"
            keys = await redis_client.keys(pattern)
            
            blacklisted_count = 0
            current_time = int(time.time())
            
            for key in keys:
                try:
                    token_data = await redis_client.get(key)
                    if token_data:
                        token_info = json.loads(token_data)
                        jti = token_info.get("jti")
                        exp = token_info.get("exp")
                        
                        if jti and exp and exp > current_time:
                            await self.blacklist_token(
                                jti=jti,
                                exp_timestamp=exp,
                                reason=reason,
                                session_id=session_id
                            )
                            blacklisted_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing session token key {key}: {e}")
                    continue
            
            logger.info(f"Blacklisted {blacklisted_count} tokens for session {session_id}")
            return blacklisted_count
            
        except Exception as e:
            logger.error(f"Failed to blacklist session tokens: {e}")
            return 0
    
    async def get_blacklist_info(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about blacklisted token"""
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                result = await redis_client.get(f"bl:{jti}")
                if result:
                    return json.loads(result)
            
            # Check memory fallback
            if jti in self.memory_blacklist:
                return {
                    "jti": jti,
                    "blacklisted_at": None,
                    "expires_at": self.memory_expiry.get(jti),
                    "reason": "unknown",
                    "storage": "memory"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get blacklist info for {jti[:8]}...: {e}")
            return None
    
    def _cleanup_memory_blacklist(self):
        """Clean up expired tokens from memory"""
        current_time = time.time()
        
        # Run cleanup every 5 minutes
        if current_time - self.last_cleanup < 300:
            return
        
        expired_tokens = [
            jti for jti, exp_time in self.memory_expiry.items()
            if exp_time <= current_time
        ]
        
        for jti in expired_tokens:
            self.memory_blacklist.discard(jti)
            del self.memory_expiry[jti]
        
        self.last_cleanup = current_time
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens from memory")
    
    async def cleanup_expired_tokens(self) -> int:
        """Manual cleanup of expired tokens (for maintenance)"""
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Redis automatically expires keys, but we can clean up any orphaned data
                pattern = "bl:*"
                keys = await redis_client.keys(pattern)
                
                expired_count = 0
                current_time = int(time.time())
                
                for key in keys:
                    try:
                        data = await redis_client.get(key)
                        if data:
                            token_info = json.loads(data)
                            if token_info.get("expires_at", 0) <= current_time:
                                await redis_client.delete(key)
                                expired_count += 1
                    except Exception:
                        # Delete malformed entries
                        await redis_client.delete(key)
                        expired_count += 1
                
                logger.info(f"Cleaned up {expired_count} expired blacklist entries")
                return expired_count
            
            # Memory cleanup
            self._cleanup_memory_blacklist()
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0


# Global blacklist instance
_token_blacklist = None

def get_token_blacklist() -> TokenBlacklist:
    """Get global token blacklist instance"""
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist()
    return _token_blacklist