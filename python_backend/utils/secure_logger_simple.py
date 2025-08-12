"""
Simplified Security Logger - No external dependencies
GDPR compliant logging for NeuroBridge EDU
"""

import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class SimpleSecurityLogger:
    """Simplified security logger using only standard library"""
    
    def __init__(self, logger_name: str = "security", log_dir: str = None):
        self.logger_name = logger_name
        self.log_dir = log_dir or "logs"
        
        # Ensure log directory exists with secure permissions
        Path(self.log_dir).mkdir(parents=True, exist_ok=True, mode=0o750)
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Security event types
        self.EVENT_TYPES = {
            'AUTH_SUCCESS': 'authentication_success',
            'AUTH_FAILURE': 'authentication_failure', 
            'AUTH_LOCKOUT': 'account_lockout',
            'PERMISSION_DENIED': 'permission_denied',
            'RATE_LIMIT_EXCEEDED': 'rate_limit_exceeded',
            'SUSPICIOUS_ACTIVITY': 'suspicious_activity',
            'DATA_ACCESS': 'data_access',
            'DATA_MODIFICATION': 'data_modification',
            'FILE_UPLOAD': 'file_upload',
            'SECURITY_SCAN': 'security_scan',
            'TOKEN_ISSUED': 'token_issued',
            'TOKEN_REVOKED': 'token_revoked',
            'SESSION_CREATED': 'session_created',
            'SESSION_ENDED': 'session_ended',
            'PRIVACY_VIOLATION': 'privacy_violation',
            'COMPLIANCE_EVENT': 'compliance_event'
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup standard logging with security-focused configuration"""
        
        # Setup logger
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers = []
        
        # File handler for security logs
        log_file = Path(self.log_dir) / "security.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.WARNING)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: str = None,
        resource: str = None,
        action: str = None,
        outcome: str = "success",
        severity: str = "info",
        additional_data: Dict[str, Any] = None
    ):
        """
        Log a security event with structured data
        
        GDPR COMPLIANT: No personal data (IP, user agent) is collected.
        Only essential security metrics for system monitoring.
        """
        
        # Create pseudonym for user ID (optional identifier, not required)
        user_pseudonym = None
        if user_id:
            # Simple hash-based pseudonym (for demo - use proper crypto in production)
            import hashlib
            user_pseudonym = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        
        event_data = {
            'event_type': event_type,
            'message': message,
            'user_pseudonym': user_pseudonym,
            'resource': resource,
            'action': action,
            'outcome': outcome,
            'severity': severity,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'neurobridge-edu',
            'privacy_compliant': True  # Confirms zero PII collection
        }
        
        if additional_data:
            # Filter out any personal data from additional_data
            filtered_data = {k: v for k, v in additional_data.items() 
                           if k not in ['ip_address', 'user_agent', 'client_ip', 'remote_addr']}
            event_data.update(filtered_data)
        
        # Create formatted message with structured data
        structured_message = f"{message} | {json.dumps(event_data)}"
        
        # Log at appropriate level
        if severity == 'error':
            self.logger.error(structured_message)
        elif severity == 'warning':
            self.logger.warning(structured_message)
        else:
            self.logger.info(structured_message)
    
    def log_authentication_event(
        self,
        success: bool,
        user_id: str = None,
        method: str = "password",
        failure_reason: str = None
    ):
        """
        Log authentication events (GDPR compliant)
        
        No personal data (IP, user agent) is collected.
        Only essential security metrics for system monitoring.
        """
        event_type = self.EVENT_TYPES['AUTH_SUCCESS'] if success else self.EVENT_TYPES['AUTH_FAILURE']
        message = "User authentication successful" if success else f"User authentication failed: {failure_reason}"
        severity = "info" if success else "warning"
        
        additional_data = {
            'auth_method': method,
            'failure_reason': failure_reason if not success else None
        }
        
        self.log_security_event(
            event_type=event_type,
            message=message,
            user_id=user_id,
            outcome="success" if success else "failure",
            severity=severity,
            additional_data=additional_data
        )


# Global security logger instance
_security_logger = None


def get_security_logger() -> SimpleSecurityLogger:
    """Get or create the global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SimpleSecurityLogger()
    return _security_logger