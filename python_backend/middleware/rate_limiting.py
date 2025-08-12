"""
Advanced Rate Limiting Middleware for NeuroBridge EDU
Educational platform optimized rate limiting with granular per-endpoint controls
"""

import time
import json
import hashlib
from typing import Dict, Optional, Tuple, Callable
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from utils.logger import get_logger

logger = get_logger(__name__)

class AdvancedRateLimiter(BaseHTTPMiddleware):
    """
    Educational platform optimized rate limiter with:
    - Per-endpoint granular limits
    - Educational usage patterns
    - IP and user-based limiting
    - Burst handling for legitimate traffic spikes
    - Security event logging
    """
    
    def __init__(
        self,
        app,
        redis_url: str = "redis://localhost:6379/0",
        default_limit: int = 60,  # requests per window
        default_window: int = 60,  # seconds
        enable_burst: bool = True,
        burst_multiplier: float = 1.5,
        whitelist_ips: Optional[list] = None
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.redis_client = None
        self.default_limit = default_limit
        self.default_window = default_window
        self.enable_burst = enable_burst
        self.burst_multiplier = burst_multiplier
        self.whitelist_ips = set(whitelist_ips or [])
        
        # Educational platform specific rate limits
        self.endpoint_limits = {
            # Transcription endpoints - higher limits for educational use
            "/api/transcription/start": {"limit": 100, "window": 3600, "description": "Transcription sessions per hour"},
            "/api/transcription/chunk": {"limit": 1000, "window": 3600, "description": "Audio chunks per hour"},
            "/api/transcription/stream": {"limit": 200, "window": 3600, "description": "Stream connections per hour"},
            
            # API key operations - strict limits for security
            "/api/api-keys/store": {"limit": 10, "window": 3600, "description": "API key creation per hour"},
            "/api/api-keys/validate": {"limit": 30, "window": 3600, "description": "API key validation per hour"},
            "/api/api-keys/delete": {"limit": 20, "window": 3600, "description": "API key deletion per hour"},
            
            # Summary generation - moderate limits
            "/api/summaries/generate": {"limit": 50, "window": 3600, "description": "Summary generation per hour"},
            "/api/summaries/export": {"limit": 100, "window": 3600, "description": "Summary export per hour"},
            
            # Authentication endpoints - strict security
            "/token": {"limit": 5, "window": 300, "description": "Login attempts per 5 minutes"},
            "/auth/refresh": {"limit": 20, "window": 3600, "description": "Token refresh per hour"},
            
            # Health and general endpoints
            "/health": {"limit": 1000, "window": 3600, "description": "Health checks per hour"},
        }
        
        # In-memory fallback for when Redis is unavailable
        self.fallback_cache: Dict[str, Dict] = {}
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable):
        """Main middleware dispatch method"""
        # Initialize Redis connection if not available
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
                self.redis_client = None

        # Skip rate limiting for whitelisted IPs
        client_ip = self._get_client_ip(request)
        if client_ip in self.whitelist_ips:
            return await call_next(request)

        # Check rate limits
        try:
            is_allowed, retry_after, limit_info = await self._check_rate_limit(request)
            
            if not is_allowed:
                # Log security event
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "event": "rate_limit_exceeded",
                        "ip": client_ip,
                        "path": request.url.path,
                        "method": request.method,
                        "user_agent": request.headers.get("user-agent", "unknown"),
                        "limit_type": limit_info["type"],
                        "retry_after": retry_after
                    }
                )
                
                # Return 429 Too Many Requests with proper headers
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests for {limit_info['description']}",
                        "retry_after": retry_after,
                        "limit": limit_info["limit"],
                        "window": limit_info["window"]
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit_info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                        "X-RateLimit-Window": str(limit_info["window"])
                    }
                )
            
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
            response.headers["X-RateLimit-Window"] = str(limit_info["window"])
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # In case of rate limiting failure, allow the request but log the error
            return await call_next(request)

    async def _check_rate_limit(self, request: Request) -> Tuple[bool, int, Dict]:
        """Check if request should be rate limited"""
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        
        # Determine rate limit configuration for this endpoint
        limit_config = self._get_limit_config(path)
        
        # Create cache keys for different scopes
        ip_key = f"rl:ip:{client_ip}:{path}:{int(time.time() / limit_config['window'])}"
        user_key = f"rl:user:{user_id}:{path}:{int(time.time() / limit_config['window'])}" if user_id else None
        
        # Check limits
        if self.redis_client:
            is_allowed, retry_after = await self._check_redis_limit(ip_key, user_key, limit_config)
        else:
            is_allowed, retry_after = await self._check_memory_limit(ip_key, user_key, limit_config)
        
        return is_allowed, retry_after, limit_config

    async def _check_redis_limit(self, ip_key: str, user_key: Optional[str], config: Dict) -> Tuple[bool, int]:
        """Check rate limits using Redis"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Check IP-based limit
            current_ip = await self.redis_client.get(ip_key)
            current_ip_count = int(current_ip) if current_ip else 0
            
            # Check user-based limit if user is authenticated
            current_user_count = 0
            if user_key:
                current_user = await self.redis_client.get(user_key)
                current_user_count = int(current_user) if current_user else 0
            
            # Apply limits (more restrictive wins)
            limit = config["limit"]
            if self.enable_burst:
                limit = int(limit * self.burst_multiplier)
            
            # Check if limits exceeded
            ip_exceeded = current_ip_count >= limit
            user_exceeded = user_key and current_user_count >= limit
            
            if ip_exceeded or user_exceeded:
                return False, config["window"]
            
            # Increment counters
            pipe.incr(ip_key)
            pipe.expire(ip_key, config["window"])
            
            if user_key:
                pipe.incr(user_key)
                pipe.expire(user_key, config["window"])
            
            await pipe.execute()
            return True, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True, 0  # Fail open

    async def _check_memory_limit(self, ip_key: str, user_key: Optional[str], config: Dict) -> Tuple[bool, int]:
        """Fallback in-memory rate limiting"""
        current_time = time.time()
        
        # Clean up old entries every 5 minutes
        if current_time - self.last_cleanup > 300:
            self._cleanup_memory_cache(current_time)
            self.last_cleanup = current_time
        
        # Check IP limit
        if ip_key not in self.fallback_cache:
            self.fallback_cache[ip_key] = {"count": 0, "reset_time": current_time + config["window"]}
        
        ip_entry = self.fallback_cache[ip_key]
        if current_time > ip_entry["reset_time"]:
            ip_entry["count"] = 0
            ip_entry["reset_time"] = current_time + config["window"]
        
        # Check user limit if applicable
        user_exceeded = False
        if user_key:
            if user_key not in self.fallback_cache:
                self.fallback_cache[user_key] = {"count": 0, "reset_time": current_time + config["window"]}
            
            user_entry = self.fallback_cache[user_key]
            if current_time > user_entry["reset_time"]:
                user_entry["count"] = 0
                user_entry["reset_time"] = current_time + config["window"]
            
            user_exceeded = user_entry["count"] >= config["limit"]
        
        # Apply limits
        limit = config["limit"]
        if self.enable_burst:
            limit = int(limit * self.burst_multiplier)
        
        ip_exceeded = ip_entry["count"] >= limit
        
        if ip_exceeded or user_exceeded:
            return False, int(max(ip_entry["reset_time"] - current_time, 0))
        
        # Increment counters
        ip_entry["count"] += 1
        if user_key and user_key in self.fallback_cache:
            self.fallback_cache[user_key]["count"] += 1
        
        return True, 0

    def _cleanup_memory_cache(self, current_time: float):
        """Remove expired entries from memory cache"""
        expired_keys = [
            key for key, entry in self.fallback_cache.items()
            if current_time > entry["reset_time"] + 300  # Keep for 5 minutes after expiry
        ]
        for key in expired_keys:
            del self.fallback_cache[key]

    def _get_limit_config(self, path: str) -> Dict:
        """Get rate limit configuration for endpoint"""
        # Exact match first
        if path in self.endpoint_limits:
            config = self.endpoint_limits[path].copy()
            config["type"] = "endpoint_specific"
            return config
        
        # Pattern matching for parameterized endpoints
        for endpoint_pattern, limits in self.endpoint_limits.items():
            if self._path_matches_pattern(path, endpoint_pattern):
                config = limits.copy()
                config["type"] = "pattern_matched"
                return config
        
        # Default limits
        return {
            "limit": self.default_limit,
            "window": self.default_window,
            "description": "default rate limit",
            "type": "default"
        }

    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for API endpoints"""
        # Handle common patterns like /api/transcription/{sessionId}
        if "{" in pattern:
            pattern_parts = pattern.split("/")
            path_parts = path.split("/")
            
            if len(pattern_parts) != len(path_parts):
                return False
            
            for pattern_part, path_part in zip(pattern_parts, path_parts):
                if pattern_part.startswith("{") and pattern_part.endswith("}"):
                    continue  # Skip parameter parts
                if pattern_part != path_part:
                    return False
            
            return True
        
        return path.startswith(pattern)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address with proxy support"""
        # Check for forwarded IP headers (common in educational environments behind proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request (for authenticated users)"""
        # This will be enhanced when JWT authentication is implemented
        # For now, we can extract from Authorization header or session
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            # Create a hash of the token as user identifier
            return hashlib.sha256(token.encode()).hexdigest()[:16]
        
        return None

    async def limit_transcription(self, request: Request) -> bool:
        """Specific method for transcription endpoint limiting"""
        is_allowed, _, _ = await self._check_rate_limit(request)
        return is_allowed

    async def limit_api_keys(self, request: Request) -> bool:
        """Specific method for API key operation limiting"""
        is_allowed, _, _ = await self._check_rate_limit(request)
        return is_allowed

    async def limit_summaries(self, request: Request) -> bool:
        """Specific method for summary generation limiting"""
        is_allowed, _, _ = await self._check_rate_limit(request)
        return is_allowed


# Utility function to create and configure the rate limiter
def create_rate_limiter(
    redis_url: str = "redis://localhost:6379/0",
    enable_burst: bool = True,
    whitelist_ips: Optional[list] = None
) -> AdvancedRateLimiter:
    """Factory function to create properly configured rate limiter"""
    
    # Default whitelist for development and educational environments
    default_whitelist = [
        "127.0.0.1", 
        "::1", 
        "localhost",
        # Add institutional IP ranges as needed
    ]
    
    if whitelist_ips:
        default_whitelist.extend(whitelist_ips)
    
    return AdvancedRateLimiter(
        app=None,  # Will be set by middleware registration
        redis_url=redis_url,
        enable_burst=enable_burst,
        whitelist_ips=default_whitelist
    )


# Educational platform specific rate limiting decorators
def require_rate_limit(limit_type: str = "default"):
    """Decorator for applying specific rate limits to endpoints"""
    def decorator(func):
        func._rate_limit_type = limit_type
        return func
    return decorator