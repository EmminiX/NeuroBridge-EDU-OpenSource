"""
Security Configuration for NeuroBridge EDU
Centralized security settings and validation
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import Field, validator

try:
    # Try pydantic v2
    from pydantic_settings import BaseSettings
except ImportError:
    # Fall back to pydantic v1
    from pydantic import BaseSettings

class SecuritySettings(BaseSettings):
    """Security configuration with environment variable support"""
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, description="Access token expiration in minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration in days")
    JWT_ALGORITHM: str = Field(default="EdDSA", description="JWT signing algorithm")
    JWT_ISSUER: str = Field(default="neurobridge-edu", description="JWT issuer")
    JWT_AUDIENCE: str = Field(default="neurobridge-users", description="JWT audience")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL for rate limiting and caching")
    RATE_LIMIT_DEFAULT_REQUESTS: int = Field(default=100, description="Default rate limit per hour")
    RATE_LIMIT_BURST_MULTIPLIER: float = Field(default=1.5, description="Burst multiplier for rate limits")
    
    # Security Headers
    FORCE_HTTPS: bool = Field(default=True, description="Force HTTPS redirects")
    CSP_REPORT_URI: Optional[str] = Field(default=None, description="CSP violation report URI")
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, description="Enable security headers")
    
    # Content Security Policy
    CSP_SCRIPT_SRC_NONCE: bool = Field(default=True, description="Use nonce for script CSP")
    CSP_STYLE_SRC_UNSAFE_INLINE: bool = Field(default=True, description="Allow unsafe-inline for styles (Tailwind CSS)")
    
    # CORS Configuration
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    CORS_MAX_AGE: int = Field(default=86400, description="CORS preflight cache time")
    
    # File Upload Security
    MAX_FILE_SIZE_MB: int = Field(default=50, description="Maximum file upload size in MB")
    ALLOWED_AUDIO_FORMATS: List[str] = Field(
        default=['wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac'],
        description="Allowed audio file formats"
    )
    AUDIO_SCAN_ENABLED: bool = Field(default=True, description="Enable audio file security scanning")
    FFMPEG_TIMEOUT_SECONDS: int = Field(default=30, description="FFmpeg analysis timeout")
    
    # Logging Security
    LOG_PII_REDACTION: bool = Field(default=True, description="Enable PII redaction in logs")
    LOG_SECURITY_EVENTS: bool = Field(default=True, description="Enable security event logging")
    LOG_RETENTION_DAYS: int = Field(default=365, description="Log retention period in days")
    STRUCTURED_LOGGING: bool = Field(default=True, description="Use structured JSON logging")
    
    # Session Management
    SESSION_TIMEOUT_HOURS: int = Field(default=8, description="Default session timeout in hours")
    CLASSROOM_SESSION_TIMEOUT_HOURS: int = Field(default=4, description="Classroom session timeout")
    ADMIN_SESSION_TIMEOUT_HOURS: int = Field(default=2, description="Admin session timeout")
    DEVICE_FINGERPRINTING: bool = Field(default=True, description="Enable device fingerprinting")
    
    # Educational Compliance
    FERPA_COMPLIANCE_MODE: bool = Field(default=True, description="Enable FERPA compliance features")
    GDPR_COMPLIANCE_MODE: bool = Field(default=True, description="Enable GDPR compliance features")
    AUDIT_TRAIL_ENABLED: bool = Field(default=True, description="Enable audit trail logging")
    DATA_RETENTION_POLICY_DAYS: int = Field(default=2555, description="Data retention period (7 years)")
    
    # API Security
    API_KEY_ENCRYPTION_ENABLED: bool = Field(default=True, description="Encrypt stored API keys")
    API_KEY_ROTATION_DAYS: int = Field(default=90, description="Recommended API key rotation period")
    API_RATE_LIMIT_PER_KEY: int = Field(default=1000, description="Rate limit per API key per hour")
    
    # Database Security
    DB_CONNECTION_ENCRYPTION: bool = Field(default=True, description="Use encrypted database connections")
    DB_QUERY_LOGGING: bool = Field(default=False, description="Log database queries (development only)")
    
    # Development vs Production
    ENVIRONMENT: str = Field(default="production", description="Environment: development, staging, production")
    DEBUG_MODE: bool = Field(default=False, description="Enable debug mode")
    SECURITY_TESTING_MODE: bool = Field(default=False, description="Enable security testing features")
    
    # Security Monitoring
    FAILED_LOGIN_THRESHOLD: int = Field(default=5, description="Failed login attempts before lockout")
    LOCKOUT_DURATION_MINUTES: int = Field(default=30, description="Account lockout duration")
    SUSPICIOUS_ACTIVITY_THRESHOLD: int = Field(default=10, description="Threshold for suspicious activity alerts")
    
    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        """Validate environment setting"""
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
    
    @validator('JWT_ALGORITHM')
    def validate_jwt_algorithm(cls, v):
        """Validate JWT algorithm"""
        allowed_algorithms = ['EdDSA', 'ES256', 'ES384', 'ES512', 'RS256', 'RS384', 'RS512']
        if v not in allowed_algorithms:
            raise ValueError(f'JWT algorithm must be one of {allowed_algorithms}')
        return v
    
    @validator('FORCE_HTTPS')
    def validate_https_in_production(cls, v, values):
        """Ensure HTTPS is forced in production"""
        environment = values.get('ENVIRONMENT', 'production')
        if environment == 'production' and not v:
            raise ValueError('HTTPS must be enforced in production')
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == 'development'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == 'production'
    
    def get_max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins from environment"""
        cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3131,http://localhost:3939')
        return [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'enabled': self.RATE_LIMIT_ENABLED,
            'redis_url': self.REDIS_URL,
            'default_requests': self.RATE_LIMIT_DEFAULT_REQUESTS,
            'burst_multiplier': self.RATE_LIMIT_BURST_MULTIPLIER,
            'per_api_key': self.API_RATE_LIMIT_PER_KEY
        }
    
    def get_security_headers_config(self) -> Dict[str, Any]:
        """Get security headers configuration"""
        return {
            'enabled': self.SECURITY_HEADERS_ENABLED,
            'force_https': self.FORCE_HTTPS,
            'csp_report_uri': self.CSP_REPORT_URI,
            'allowed_origins': self.get_cors_origins(),
            'development_mode': self.is_development
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration"""
        return {
            'access_token_expire_minutes': self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            'refresh_token_expire_days': self.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
            'algorithm': self.JWT_ALGORITHM,
            'issuer': self.JWT_ISSUER,
            'audience': self.JWT_AUDIENCE
        }
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get session management configuration"""
        return {
            'default_timeout_hours': self.SESSION_TIMEOUT_HOURS,
            'classroom_timeout_hours': self.CLASSROOM_SESSION_TIMEOUT_HOURS,
            'admin_timeout_hours': self.ADMIN_SESSION_TIMEOUT_HOURS,
            'device_fingerprinting': self.DEVICE_FINGERPRINTING
        }
    
    def get_compliance_config(self) -> Dict[str, Any]:
        """Get compliance configuration"""
        return {
            'ferpa_enabled': self.FERPA_COMPLIANCE_MODE,
            'gdpr_enabled': self.GDPR_COMPLIANCE_MODE,
            'audit_trail': self.AUDIT_TRAIL_ENABLED,
            'data_retention_days': self.DATA_RETENTION_POLICY_DAYS,
            'pii_redaction': self.LOG_PII_REDACTION
        }
    
    def validate_security_configuration(self) -> List[str]:
        """Validate security configuration and return warnings"""
        warnings = []
        
        # Production security checks
        if self.is_production:
            if not self.FORCE_HTTPS:
                warnings.append("HTTPS should be enforced in production")
            
            if self.DEBUG_MODE:
                warnings.append("Debug mode should be disabled in production")
            
            if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 60:
                warnings.append("Access token expiration should be <= 60 minutes in production")
            
            if not self.RATE_LIMIT_ENABLED:
                warnings.append("Rate limiting should be enabled in production")
            
            if not self.LOG_SECURITY_EVENTS:
                warnings.append("Security event logging should be enabled in production")
        
        # General security warnings
        if self.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 30:
            warnings.append("Refresh token expiration should be <= 30 days")
        
        if self.MAX_FILE_SIZE_MB > 100:
            warnings.append("Large file uploads may impact performance")
        
        if self.SESSION_TIMEOUT_HOURS > 24:
            warnings.append("Long session timeouts may pose security risks")
        
        return warnings
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Global security settings instance
security_settings = SecuritySettings()

def get_security_config() -> SecuritySettings:
    """Get global security configuration"""
    return security_settings

def validate_security_setup() -> bool:
    """Validate security setup and log warnings"""
    from utils.logger import get_logger
    logger = get_logger(__name__)
    
    warnings = security_settings.validate_security_configuration()
    
    if warnings:
        logger.warning(f"Security configuration warnings: {warnings}")
    
    logger.info(
        f"Security configuration loaded",
        extra={
            'environment': security_settings.ENVIRONMENT,
            'https_enforced': security_settings.FORCE_HTTPS,
            'rate_limiting': security_settings.RATE_LIMIT_ENABLED,
            'security_headers': security_settings.SECURITY_HEADERS_ENABLED,
            'compliance_mode': {
                'ferpa': security_settings.FERPA_COMPLIANCE_MODE,
                'gdpr': security_settings.GDPR_COMPLIANCE_MODE
            }
        }
    )
    
    return len(warnings) == 0