"""
Security Headers Middleware for Educational Platforms
Comprehensive security headers implementation with educational-specific CSP policies
"""

import os
from typing import Dict, List, Optional, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from utils.logger import get_logger

logger = get_logger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware for educational platforms
    
    Implements:
    - Content Security Policy (CSP) with educational-specific rules
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options protection
    - X-Content-Type-Options
    - Referrer Policy
    - Permissions Policy
    - Cross-Origin policies
    """
    
    def __init__(
        self,
        app: ASGIApp,
        force_https: bool = None,
        csp_report_uri: str = None,
        allowed_origins: List[str] = None,
        development_mode: bool = False
    ):
        super().__init__(app)
        
        # Environment detection
        self.development_mode = development_mode or os.getenv('ENVIRONMENT', 'production').lower() != 'production'
        self.force_https = force_https if force_https is not None else not self.development_mode
        
        # CSP configuration
        self.csp_report_uri = csp_report_uri or os.getenv('CSP_REPORT_URI')
        self.allowed_origins = allowed_origins or self._get_allowed_origins()
        
        # Build security headers
        self.security_headers = self._build_security_headers()
    
    def _get_allowed_origins(self) -> List[str]:
        """Get allowed origins from environment"""
        origins_env = os.getenv('CORS_ORIGINS', 'http://localhost:3131,http://localhost:3939')
        return [origin.strip() for origin in origins_env.split(',') if origin.strip()]
    
    def _build_security_headers(self) -> Dict[str, str]:
        """Build comprehensive security headers"""
        headers = {}
        
        # Content Security Policy - Educational Platform Optimized
        csp_policy = self._build_csp_policy()
        if csp_policy:
            headers['Content-Security-Policy'] = csp_policy
        
        # HTTP Strict Transport Security (HSTS)
        if self.force_https:
            headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # X-Frame-Options - Prevent clickjacking
        headers['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options - Prevent MIME type sniffing
        headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-XSS-Protection - Legacy XSS protection
        headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy - Control referrer information
        headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy - Control browser features
        permissions_policy = self._build_permissions_policy()
        if permissions_policy:
            headers['Permissions-Policy'] = permissions_policy
        
        # Cross-Origin Embedder Policy
        headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # Cross-Origin Opener Policy
        headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cross-Origin Resource Policy
        headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        
        # Server identification removal
        headers['Server'] = 'NeuroBridge-EDU'
        
        return headers
    
    def _build_csp_policy(self) -> str:
        """Build Content Security Policy for educational platform"""
        
        # Base origins
        self_origin = "'self'"
        
        # Extract domains from allowed origins for CSP
        allowed_domains = []
        for origin in self.allowed_origins:
            try:
                # Extract domain from origin
                if origin.startswith('http://') or origin.startswith('https://'):
                    domain = origin.split('//')[1].split('/')[0]
                    allowed_domains.append(domain)
            except Exception:
                continue
        
        # Development vs Production CSP
        if self.development_mode:
            csp_directives = {
                'default-src': [self_origin],
                'script-src': [self_origin, "'unsafe-inline'", "'unsafe-eval'", "blob:"] + allowed_domains,
                'style-src': [self_origin, "'unsafe-inline'"] + allowed_domains,
                'img-src': [self_origin, "data:", "blob:"] + allowed_domains,
                'font-src': [self_origin, "data:"] + allowed_domains,
                'connect-src': [self_origin, "ws:", "wss:"] + allowed_domains,
                'media-src': [self_origin, "blob:"] + allowed_domains,
                'worker-src': [self_origin, "blob:"],
                'child-src': [self_origin, "blob:"],
                'frame-ancestors': ["'none'"],
                'base-uri': [self_origin],
                'form-action': [self_origin]
            }
        else:
            # Production CSP - More restrictive
            csp_directives = {
                'default-src': [self_origin],
                'script-src': [self_origin, "'strict-dynamic'"] + allowed_domains,
                'style-src': [self_origin, "'unsafe-inline'"] + allowed_domains,  # Needed for Tailwind CSS
                'img-src': [self_origin, "data:"] + allowed_domains,
                'font-src': [self_origin, "data:"] + allowed_domains,
                'connect-src': [self_origin, "wss:", "https:"] + allowed_domains,
                'media-src': [self_origin, "blob:"] + allowed_domains,
                'worker-src': [self_origin, "blob:"],
                'child-src': [self_origin],
                'frame-ancestors': ["'none'"],
                'base-uri': [self_origin],
                'form-action': [self_origin],
                'upgrade-insecure-requests': []  # Force HTTPS
            }
        
        # Add report URI if configured
        if self.csp_report_uri:
            csp_directives['report-uri'] = [self.csp_report_uri]
        
        # Build CSP string
        csp_parts = []
        for directive, sources in csp_directives.items():
            if sources:
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(directive)
        
        return '; '.join(csp_parts)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy for educational platform"""
        
        # Educational platform appropriate permissions
        permissions = {
            # Allow microphone for audio recording
            'microphone': self._format_origins_for_permissions(self.allowed_origins),
            
            # Disable camera by default (can be enabled per feature)
            'camera': '()',
            
            # Allow clipboard for copy/paste functionality
            'clipboard-read': self._format_origins_for_permissions(self.allowed_origins),
            'clipboard-write': self._format_origins_for_permissions(self.allowed_origins),
            
            # Disable geolocation (not needed for educational platform)
            'geolocation': '()',
            
            # Disable notifications (avoid distractions)
            'notifications': '()',
            
            # Disable payment APIs
            'payment': '()',
            
            # Allow fullscreen for presentation mode
            'fullscreen': self._format_origins_for_permissions(self.allowed_origins),
            
            # Disable USB access
            'usb': '()',
            
            # Disable MIDI access
            'midi': '()',
            
            # Allow autoplay for educational content
            'autoplay': self._format_origins_for_permissions(self.allowed_origins),
            
            # Disable accelerometer/gyroscope (mobile distractions)
            'accelerometer': '()',
            'gyroscope': '()',
            
            # Allow display capture for screen sharing (instructor feature)
            'display-capture': self._format_origins_for_permissions(self.allowed_origins),
        }
        
        # Format permissions policy
        policy_parts = []
        for feature, origins in permissions.items():
            policy_parts.append(f"{feature}={origins}")
        
        return ', '.join(policy_parts)
    
    def _format_origins_for_permissions(self, origins: List[str]) -> str:
        """Format origins for Permissions Policy syntax"""
        if not origins:
            return '()'
        
        # Convert to permissions policy format
        formatted_origins = []
        for origin in origins:
            if origin == 'self':
                formatted_origins.append('self')
            else:
                # Extract domain for permissions policy
                try:
                    if origin.startswith('http://') or origin.startswith('https://'):
                        domain = origin.split('//')[1].split('/')[0]
                        formatted_origins.append(f'"{domain}"')
                    else:
                        formatted_origins.append(f'"{origin}"')
                except Exception:
                    continue
        
        if formatted_origins:
            return f"({' '.join(formatted_origins)})"
        else:
            return "(self)"
    
    async def dispatch(self, request: Request, call_next):
        """Apply security headers to all responses"""
        
        # HTTPS enforcement
        if self.force_https and request.url.scheme == 'http':
            # Redirect to HTTPS
            https_url = request.url.replace(scheme='https')
            return JSONResponse(
                status_code=301,
                content={'detail': 'HTTPS required'},
                headers={'Location': str(https_url)}
            )
        
        # Process the request
        response = await call_next(request)
        
        # Apply security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Additional security headers based on response type
        self._apply_conditional_headers(request, response)
        
        return response
    
    def _apply_conditional_headers(self, request: Request, response: Response):
        """Apply conditional security headers based on request/response"""
        
        # For API responses, add additional headers
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # For static assets, allow caching with security
        elif any(request.url.path.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.svg', '.woff', '.woff2']):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        # For sensitive endpoints, add extra protection
        sensitive_paths = ['/api/api-keys/', '/api/auth/', '/token']
        if any(request.url.path.startswith(path) for path in sensitive_paths):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive, nosnippet'

class CSPReportHandler:
    """Handle Content Security Policy violation reports"""
    
    def __init__(self, log_violations: bool = True):
        self.log_violations = log_violations
    
    async def handle_csp_report(self, request: Request):
        """Handle CSP violation reports"""
        try:
            report_data = await request.json()
            
            if self.log_violations:
                violation = report_data.get('csp-report', {})
                logger.warning(
                    "CSP Violation",
                    extra={
                        'event': 'csp_violation',
                        'blocked_uri': violation.get('blocked-uri', 'unknown'),
                        'violated_directive': violation.get('violated-directive', 'unknown'),
                        'document_uri': violation.get('document-uri', 'unknown'),
                        'source_file': violation.get('source-file', 'unknown'),
                        'line_number': violation.get('line-number', 'unknown'),
                        'user_agent': request.headers.get('user-agent', 'unknown')
                    }
                )
            
            return JSONResponse(
                status_code=200,
                content={'status': 'report received'}
            )
            
        except Exception as e:
            logger.error(f"Error handling CSP report: {e}")
            return JSONResponse(
                status_code=400,
                content={'error': 'Invalid report format'}
            )

def create_security_middleware(
    force_https: bool = None,
    csp_report_uri: str = None,
    allowed_origins: List[str] = None,
    development_mode: bool = None
) -> SecurityHeadersMiddleware:
    """Factory function to create security headers middleware"""
    
    # Auto-detect development mode if not specified
    if development_mode is None:
        development_mode = os.getenv('ENVIRONMENT', 'production').lower() != 'production'
    
    return SecurityHeadersMiddleware(
        app=None,  # Will be set during middleware registration
        force_https=force_https,
        csp_report_uri=csp_report_uri,
        allowed_origins=allowed_origins,
        development_mode=development_mode
    )

# Security configuration presets
EDUCATIONAL_SECURITY_CONFIG = {
    'force_https': True,
    'allowed_origins': [
        'http://localhost:3131',  # Development frontend
        'http://localhost:3939',  # Development API
    ],
    'development_mode': False
}

DEVELOPMENT_SECURITY_CONFIG = {
    'force_https': False,
    'allowed_origins': [
        'http://localhost:3131',
        'http://localhost:3939', 
        'http://localhost:8000',
        'http://localhost:5173',  # Vite dev server
    ],
    'development_mode': True
}