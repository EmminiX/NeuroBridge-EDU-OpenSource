"""
Authentication Dependencies for FastAPI
JWT-based authentication with educational platform features
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth import verify_token, TokenData
from services.auth.token_blacklist import get_token_blacklist
from services.auth.session_manager import get_session_manager
from utils.secure_logger_simple import get_security_logger

# Security scheme
security = HTTPBearer(auto_error=False)
security_logger = get_security_logger()

class AuthenticationError(HTTPException):
    """Custom authentication error with security logging"""
    
    def __init__(self, detail: str, request: Request = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        # Log authentication failure
        if request:
            security_logger.log_authentication_event(
                success=False,
                user_id=None,
                # REMOVED: ip_address, user_agent for GDPR compliance
                failure_reason=detail
            )

class AuthorizationError(HTTPException):
    """Custom authorization error"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Get current authenticated user from JWT token
    """
    if not credentials:
        raise AuthenticationError("No authentication token provided", request)
    
    token = credentials.credentials
    
    # Verify token is not blacklisted
    token_blacklist = get_token_blacklist()
    
    # First decode to get JTI without verification
    try:
        from services.auth.jwt_manager import get_jwt_manager
        jwt_manager = get_jwt_manager()
        unverified_claims = jwt_manager.extract_token_claims(token)
        
        if unverified_claims and unverified_claims.get('jti'):
            is_blacklisted = await token_blacklist.is_blacklisted(unverified_claims['jti'])
            if is_blacklisted:
                raise AuthenticationError("Token has been revoked", request)
    except Exception:
        pass  # Continue with full verification
    
    # Verify and decode token
    token_data = verify_token(token, "access")
    if not token_data:
        raise AuthenticationError("Invalid or expired token", request)
    
    # Update session activity if session tracking is enabled
    if token_data.session_id:
        session_manager = get_session_manager()
        session_active = await session_manager.update_session_activity(token_data.session_id)
        if not session_active:
            raise AuthenticationError("Session expired or invalid", request)
    
    # Log successful authentication
    security_logger.log_authentication_event(
        success=True,
        user_id=token_data.sub,
        # REMOVED: ip_address, user_agent for GDPR compliance
        method="jwt"
    )
    
    return token_data

async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Get current active user (placeholder for user status checking)
    In a full system, this would check if user account is active/enabled
    """
    # For now, all authenticated users are considered active
    # In a complete system, you would check user status in database
    return current_user

def require_scopes(required_scopes: List[str]):
    """
    Dependency factory for scope-based authorization
    """
    async def check_scopes(
        request: Request,
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user has required scopes"""
        user_scopes = set(current_user.scopes or [])
        required_scopes_set = set(required_scopes)
        
        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            
            # Log authorization failure
            security_logger.log_security_event(
                event_type="permission_denied",
                message=f"Insufficient scopes for endpoint",
                user_id=current_user.sub,
                # REMOVED: ip_address for GDPR compliance
                resource=request.url.path,
                action=request.method,
                outcome="denied",
                severity="warning",
                additional_data={
                    'required_scopes': list(required_scopes),
                    'user_scopes': list(user_scopes),
                    'missing_scopes': list(missing_scopes)
                }
            )
            
            raise AuthorizationError(
                f"Missing required scopes: {', '.join(missing_scopes)}"
            )
        
        return current_user
    
    return check_scopes

def require_session_type(allowed_session_types: List[str]):
    """
    Dependency factory for session type-based authorization
    """
    async def check_session_type(
        request: Request,
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user's session type is allowed"""
        
        if not current_user.session_id:
            raise AuthorizationError("Session-based access required")
        
        # Get session information
        session_manager = get_session_manager()
        session = await session_manager.get_session(current_user.session_id)
        
        if not session:
            raise AuthenticationError("Session not found or expired")
        
        if session.session_type not in allowed_session_types:
            security_logger.log_security_event(
                event_type="permission_denied",
                message=f"Session type not allowed for endpoint",
                user_id=current_user.sub,
                # REMOVED: ip_address for GDPR compliance
                resource=request.url.path,
                action=request.method,
                outcome="denied",
                severity="warning",
                additional_data={
                    'session_type': session.session_type,
                    'allowed_session_types': allowed_session_types
                }
            )
            
            raise AuthorizationError(
                f"Session type '{session.session_type}' not allowed. Required: {', '.join(allowed_session_types)}"
            )
        
        return current_user
    
    return check_session_type

# Common permission dependencies
require_transcription_access = require_scopes(["transcription:read"])
require_transcription_write = require_scopes(["transcription:write"])
require_summary_access = require_scopes(["summary:read"])
require_summary_write = require_scopes(["summary:write"])
require_admin_access = require_scopes(["admin:read", "admin:write"])
require_api_key_access = require_scopes(["api_keys:manage"])

# Session type dependencies
require_individual_session = require_session_type(["individual"])
require_classroom_session = require_session_type(["classroom", "individual"])
require_admin_session = require_session_type(["admin"])

# Optional authentication (for public endpoints that can benefit from user context)
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[TokenData]:
    """
    Optional authentication - returns None if no valid token
    Useful for endpoints that can work with or without authentication
    """
    if not credentials:
        return None
    
    try:
        token_data = verify_token(credentials.credentials, "access")
        
        # Check if token is blacklisted
        if token_data and token_data.jti:
            token_blacklist = get_token_blacklist()
            is_blacklisted = await token_blacklist.is_blacklisted(token_data.jti)
            if is_blacklisted:
                return None
        
        return token_data
    except Exception:
        return None

# Educational platform specific dependencies
async def require_educational_context(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Ensure user is in an educational context (classroom or individual learning)
    """
    if not current_user.session_id:
        raise AuthorizationError("Educational session required")
    
    session_manager = get_session_manager()
    session = await session_manager.get_session(current_user.session_id)
    
    if not session or session.session_type not in ["individual", "classroom"]:
        raise AuthorizationError("Educational session context required")
    
    return current_user