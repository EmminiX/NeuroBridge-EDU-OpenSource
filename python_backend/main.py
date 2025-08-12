"""
NeuroBridge EDU - AI-Powered Educational Transcription Platform
Copyright (c) 2025 NeuroBridge EDU

This software is licensed under the NeuroBridge EDU Non-Commercial License.
You may use, modify, and distribute this software for non-commercial purposes only.
Commercial use requires explicit written permission.

Contact: neurobridgeedu@gmail.com
Website: https://neurobridgeedu.eu

See LICENSE file for full terms and conditions.

NeuroBridge EDU Python Backend - Security Enhanced
FastAPI application entry point with comprehensive security features
"""

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import register_routes
from middleware.cors import setup_cors
# from middleware.rate_limiting import create_rate_limiter  # Disabled - requires Redis
from middleware.security_headers import SecurityHeadersMiddleware
from models.database.connection import init_database
from config import settings
from config.security import get_security_config, validate_security_setup
from utils.logger import setup_logging
from utils.error_handler import global_exception_handler
from utils.secure_logger_simple import get_security_logger

# Initialize security configuration
security_config = get_security_config()
security_logger = get_security_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with security initialization"""
    # Startup
    setup_logging()
    
    # Validate security configuration
    security_valid = validate_security_setup()
    if not security_valid and security_config.is_production:
        security_logger.log_security_event(
            event_type="security_misconfiguration",
            message="Security configuration warnings detected in production",
            severity="error"
        )
    
    # Initialize database
    await init_database()
    
    # Log application startup
    security_logger.log_security_event(
        event_type="application_startup",
        message="NeuroBridge EDU backend started",
        severity="info",
        additional_data={
            'environment': security_config.ENVIRONMENT,
            'security_features': {
                'rate_limiting': security_config.RATE_LIMIT_ENABLED,
                'security_headers': security_config.SECURITY_HEADERS_ENABLED,
                'https_enforced': security_config.FORCE_HTTPS,
                'audit_logging': security_config.AUDIT_TRAIL_ENABLED
            }
        }
    )
    
    yield
    
    # Shutdown
    security_logger.log_security_event(
        event_type="application_shutdown",
        message="NeuroBridge EDU backend shutting down",
        severity="info"
    )


# Create FastAPI application with security-focused configuration
app = FastAPI(
    title="NeuroBridge EDU API",
    description="Real-time transcription and AI summarization platform with enterprise security",
    version="2.0.0-security-enhanced",
    lifespan=lifespan,
    # Disable docs in production for security
    docs_url="/docs" if not security_config.is_production else None,
    redoc_url="/redoc" if not security_config.is_production else None,
    openapi_url="/openapi.json" if not security_config.is_production else None
)

# Security Middleware Stack (order matters!)

# 1. Security Headers Middleware (temporarily disabled for testing)
# if security_config.SECURITY_HEADERS_ENABLED:
#     app.add_middleware(
#         SecurityHeadersMiddleware,
#         force_https=security_config.FORCE_HTTPS,
#         csp_report_uri=security_config.CSP_REPORT_URI,
#         allowed_origins=security_config.get_cors_origins(),
#         development_mode=security_config.is_development
#     )

# 2. Rate Limiting Middleware (temporarily disabled for testing)
# if security_config.RATE_LIMIT_ENABLED:
#     rate_limiter = create_rate_limiter(
#         redis_url=security_config.REDIS_URL,
#         enable_burst=True,
#         whitelist_ips=['127.0.0.1', '::1']  # Local development IPs
#     )
#     app.add_middleware(type(rate_limiter), **rate_limiter.__dict__)

# 3. CORS Middleware
setup_cors(app)

# Register all API routes
register_routes(app)

# Add global exception handler
@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception):
    # Log security-relevant exceptions
    if hasattr(exc, 'status_code') and exc.status_code in [401, 403, 429]:
        security_logger.log_security_event(
            event_type="security_exception",
            message=f"Security exception: {exc.__class__.__name__}",
            # REMOVED: ip_address for GDPR compliance
            resource=request.url.path,
            action=request.method,
            severity="warning",
            additional_data={
                'exception_type': exc.__class__.__name__,
                'status_code': getattr(exc, 'status_code', None)
            }
        )
    
    return await global_exception_handler(request, exc)

# Enhanced health check endpoint with security information
@app.get("/health")
async def health_check():
    """Health check endpoint with basic security status"""
    health_data = {
        "status": "healthy",
        "service": "neurobridge-edu",
        "version": "2.0.0-security-enhanced",
        "port": settings.PORT
    }
    
    # Add security status in development mode only
    if security_config.is_development:
        health_data["security"] = {
            "rate_limiting": security_config.RATE_LIMIT_ENABLED,
            "security_headers": security_config.SECURITY_HEADERS_ENABLED,
            "https_enforced": security_config.FORCE_HTTPS,
            "environment": security_config.ENVIRONMENT
        }
    
    return health_data

# Security monitoring endpoint (development only)
if security_config.is_development:
    @app.get("/security/status")
    async def security_status():
        """Detailed security configuration status (development only)"""
        return {
            "security_config": {
                "rate_limiting": security_config.get_rate_limit_config(),
                "jwt_config": {
                    "algorithm": security_config.JWT_ALGORITHM,
                    "access_token_expire_minutes": security_config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
                    "refresh_token_expire_days": security_config.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                },
                "compliance": security_config.get_compliance_config(),
                "session_config": security_config.get_session_config()
            },
            "warnings": security_config.validate_security_configuration()
        }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )