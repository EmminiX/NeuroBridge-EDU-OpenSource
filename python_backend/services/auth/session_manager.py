"""
Session Management for Educational Platforms
Handles classroom sessions, individual sessions, and device tracking
"""

import json
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import redis.asyncio as redis
from utils.logger import get_logger

logger = get_logger(__name__)

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    user_id: str
    session_type: str  # "individual", "classroom", "admin"
    device_fingerprint: Optional[str] = None
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool = True
    
    # Educational platform specific
    classroom_id: Optional[str] = None
    instructor_id: Optional[str] = None
    course_id: Optional[str] = None
    
    # Security tracking
    login_method: str  # "password", "sso", "api_key"
    security_level: str = "standard"  # "standard", "elevated", "admin"
    force_logout_after: Optional[datetime] = None

class SessionManager:
    """
    Educational platform session manager
    
    Features:
    - Individual and classroom session management
    - Device fingerprinting and tracking
    - Session-based security controls
    - Educational context awareness
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/2",
        default_session_hours: int = 8,  # Educational day length
        classroom_session_hours: int = 4,  # Class period length
        admin_session_hours: int = 2,  # Admin sessions are shorter
    ):
        self.redis_url = redis_url
        self.redis_client = None
        
        # Session duration configurations
        self.session_durations = {
            "individual": timedelta(hours=default_session_hours),
            "classroom": timedelta(hours=classroom_session_hours),
            "admin": timedelta(hours=admin_session_hours),
            "api": timedelta(days=30)  # Long-lived for API access
        }
        
        # Memory fallback
        self.memory_sessions: Dict[str, SessionInfo] = {}
        self.last_cleanup = time.time()
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client with connection handling"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Connected to Redis for session management")
            except Exception as e:
                logger.warning(f"Redis connection failed for sessions: {e}")
                self.redis_client = None
        return self.redis_client
    
    async def create_session(
        self,
        user_id: str,
        session_type: str = "individual",
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        device_fingerprint: Optional[str] = None,
        classroom_id: Optional[str] = None,
        instructor_id: Optional[str] = None,
        course_id: Optional[str] = None,
        login_method: str = "password",
        security_level: str = "standard"
    ) -> SessionInfo:
        """Create a new session"""
        
        session_id = self._generate_session_id()
        now = datetime.now(timezone.utc)
        expires_at = now + self.session_durations.get(session_type, self.session_durations["individual"])
        
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            session_type=session_type,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            classroom_id=classroom_id,
            instructor_id=instructor_id,
            course_id=course_id,
            login_method=login_method,
            security_level=security_level
        )
        
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Store session in Redis
                session_key = f"session:{session_id}"
                user_sessions_key = f"user_sessions:{user_id}"
                
                # Store session data
                session_data = session_info.model_dump_json()
                ttl = int((expires_at - now).total_seconds())
                
                await redis_client.setex(session_key, ttl, session_data)
                
                # Add to user's session list
                await redis_client.sadd(user_sessions_key, session_id)
                await redis_client.expire(user_sessions_key, ttl)
                
                # Track by device if fingerprint provided
                if device_fingerprint:
                    device_key = f"device_sessions:{device_fingerprint}"
                    await redis_client.sadd(device_key, session_id)
                    await redis_client.expire(device_key, ttl)
                
                logger.info(f"Created {session_type} session {session_id} for user {user_id}")
            else:
                # Memory fallback
                self.memory_sessions[session_id] = session_info
                logger.info(f"Created session {session_id} in memory for user {user_id}")
            
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            # Return session info even if storage failed
            return session_info
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                session_data = await redis_client.get(f"session:{session_id}")
                if session_data:
                    session_dict = json.loads(session_data)
                    # Convert ISO strings back to datetime objects
                    for date_field in ["created_at", "last_activity", "expires_at", "force_logout_after"]:
                        if session_dict.get(date_field):
                            session_dict[date_field] = datetime.fromisoformat(session_dict[date_field])
                    return SessionInfo(**session_dict)
            else:
                # Memory fallback
                self._cleanup_memory_sessions()
                return self.memory_sessions.get(session_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            now = datetime.now(timezone.utc)
            
            # Check if session is expired
            if now >= session.expires_at:
                await self.invalidate_session(session_id, "expired")
                return False
            
            # Check for forced logout
            if session.force_logout_after and now >= session.force_logout_after:
                await self.invalidate_session(session_id, "forced_logout")
                return False
            
            session.last_activity = now
            
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Update in Redis
                session_data = session.model_dump_json()
                ttl = int((session.expires_at - now).total_seconds())
                await redis_client.setex(f"session:{session_id}", ttl, session_data)
            else:
                # Update in memory
                self.memory_sessions[session_id] = session
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            return False
    
    async def invalidate_session(self, session_id: str, reason: str = "logout") -> bool:
        """Invalidate a session"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return True  # Already gone
            
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Remove from Redis
                await redis_client.delete(f"session:{session_id}")
                
                # Remove from user session list
                await redis_client.srem(f"user_sessions:{session.user_id}", session_id)
                
                # Remove from device session list
                if session.device_fingerprint:
                    await redis_client.srem(f"device_sessions:{session.device_fingerprint}", session_id)
            else:
                # Remove from memory
                self.memory_sessions.pop(session_id, None)
            
            logger.info(
                f"Invalidated session {session_id} for user {session.user_id}",
                extra={
                    "event": "session_invalidated",
                    "session_id": session_id,
                    "user_id": session.user_id,
                    "reason": reason,
                    "session_type": session.session_type
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all active sessions for a user"""
        try:
            redis_client = await self._get_redis_client()
            sessions = []
            
            if redis_client:
                session_ids = await redis_client.smembers(f"user_sessions:{user_id}")
                
                for session_id in session_ids:
                    session = await self.get_session(session_id.decode())
                    if session and session.is_active:
                        sessions.append(session)
            else:
                # Memory fallback
                self._cleanup_memory_sessions()
                sessions = [
                    session for session in self.memory_sessions.values()
                    if session.user_id == user_id and session.is_active
                ]
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    async def invalidate_user_sessions(
        self, 
        user_id: str, 
        exclude_session_id: Optional[str] = None,
        reason: str = "security_event"
    ) -> int:
        """Invalidate all sessions for a user except optionally one"""
        try:
            sessions = await self.get_user_sessions(user_id)
            invalidated_count = 0
            
            for session in sessions:
                if exclude_session_id and session.session_id == exclude_session_id:
                    continue
                
                if await self.invalidate_session(session.session_id, reason):
                    invalidated_count += 1
            
            logger.info(
                f"Invalidated {invalidated_count} sessions for user {user_id}",
                extra={
                    "event": "bulk_session_invalidation",
                    "user_id": user_id,
                    "count": invalidated_count,
                    "reason": reason
                }
            )
            
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate user sessions: {e}")
            return 0
    
    async def get_device_sessions(self, device_fingerprint: str) -> List[SessionInfo]:
        """Get all sessions for a device"""
        try:
            redis_client = await self._get_redis_client()
            sessions = []
            
            if redis_client:
                session_ids = await redis_client.smembers(f"device_sessions:{device_fingerprint}")
                
                for session_id in session_ids:
                    session = await self.get_session(session_id.decode())
                    if session and session.is_active:
                        sessions.append(session)
            else:
                # Memory fallback
                sessions = [
                    session for session in self.memory_sessions.values()
                    if session.device_fingerprint == device_fingerprint and session.is_active
                ]
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get device sessions: {e}")
            return []
    
    async def force_logout_after(self, session_id: str, minutes: int) -> bool:
        """Set forced logout time for a session"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            session.force_logout_after = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            
            redis_client = await self._get_redis_client()
            
            if redis_client:
                session_data = session.model_dump_json()
                ttl = int((session.expires_at - datetime.now(timezone.utc)).total_seconds())
                await redis_client.setex(f"session:{session_id}", ttl, session_data)
            else:
                self.memory_sessions[session_id] = session
            
            logger.info(f"Set forced logout for session {session_id} in {minutes} minutes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set forced logout: {e}")
            return False
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)
    
    def _cleanup_memory_sessions(self):
        """Clean up expired sessions from memory"""
        current_time = time.time()
        
        # Run cleanup every 5 minutes
        if current_time - self.last_cleanup < 300:
            return
        
        now = datetime.now(timezone.utc)
        expired_sessions = [
            session_id for session_id, session in self.memory_sessions.items()
            if session.expires_at <= now or (session.force_logout_after and session.force_logout_after <= now)
        ]
        
        for session_id in expired_sessions:
            del self.memory_sessions[session_id]
        
        self.last_cleanup = current_time
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions from memory")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics for monitoring"""
        try:
            redis_client = await self._get_redis_client()
            
            if redis_client:
                # Count sessions by type
                session_keys = await redis_client.keys("session:*")
                sessions_by_type = {}
                total_sessions = 0
                
                for key in session_keys:
                    session_data = await redis_client.get(key)
                    if session_data:
                        session_dict = json.loads(session_data)
                        session_type = session_dict.get("session_type", "unknown")
                        sessions_by_type[session_type] = sessions_by_type.get(session_type, 0) + 1
                        total_sessions += 1
                
                return {
                    "total_active_sessions": total_sessions,
                    "sessions_by_type": sessions_by_type,
                    "storage": "redis"
                }
            else:
                # Memory stats
                self._cleanup_memory_sessions()
                sessions_by_type = {}
                
                for session in self.memory_sessions.values():
                    session_type = session.session_type
                    sessions_by_type[session_type] = sessions_by_type.get(session_type, 0) + 1
                
                return {
                    "total_active_sessions": len(self.memory_sessions),
                    "sessions_by_type": sessions_by_type,
                    "storage": "memory"
                }
        
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}


# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager