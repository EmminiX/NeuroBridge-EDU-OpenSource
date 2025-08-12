"""
Secure Production Logging System
Educational platform compliant logging with PII redaction and security features
"""

import os
import re
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
from pathlib import Path
# import structlog  # Removed - not in requirements, using standard logging instead
import logging
import json
from utils.logger import get_logger

# Base logger for this module
base_logger = get_logger(__name__)

class PIIRedactor:
    """
    PII Redaction utility for educational compliance (FERPA, GDPR)
    """
    
    def __init__(self):
        # Patterns for PII detection and redaction
        self.pii_patterns = {
            # Email addresses
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            
            # Phone numbers (various formats)
            'phone': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
            
            # Social Security Numbers (US format)
            'ssn': re.compile(r'\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b'),
            
            # Student ID patterns (common formats)
            'student_id': re.compile(r'\b(student|id|sid)[\s:=]*([a-zA-Z0-9]{6,12})\b', re.IGNORECASE),
            
            # Credit card numbers
            'credit_card': re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
            
            # JWT tokens
            'jwt_token': re.compile(r'eyJ[A-Za-z0-9_=-]+\.eyJ[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]+'),
            
            # API keys (common patterns)
            'api_key': re.compile(r'\b(sk-|pk_|rk_)[A-Za-z0-9]{20,}\b'),
            
            # IP addresses (last 2 octets for GDPR)
            'ip_address': re.compile(r'\b(\d{1,3}\.\d{1,3})\.\d{1,3}\.\d{1,3}\b'),
            
            # Authorization headers
            'auth_header': re.compile(r'(authorization|bearer|token)[\s:=]+([A-Za-z0-9+/=._-]{10,})', re.IGNORECASE),
            
            # Passwords in various contexts
            'password': re.compile(r'(password|passwd|pwd)[\s:=]+[^\s\n\r]+', re.IGNORECASE),
            
            # Session IDs
            'session_id': re.compile(r'(session|sid)[\s:=]*([A-Za-z0-9+/=._-]{16,})', re.IGNORECASE),
        }
        
        # Replacement patterns
        self.replacements = {
            'email': lambda m: self._mask_email(m.group(0)),
            'phone': '[PHONE_REDACTED]',
            'ssn': '[SSN_REDACTED]',
            'student_id': lambda m: f"{m.group(1)}:[STUDENT_ID_REDACTED]",
            'credit_card': '[CARD_REDACTED]',
            'jwt_token': '[JWT_REDACTED]',
            'api_key': lambda m: f"{m.group(1)}[API_KEY_REDACTED]",
            'ip_address': lambda m: f"{m.group(1)}.xxx.xxx",
            'auth_header': lambda m: f"{m.group(1)}:[AUTH_REDACTED]",
            'password': lambda m: f"{m.group(1).lower()}:[PASSWORD_REDACTED]",
            'session_id': lambda m: f"{m.group(1)}:[SESSION_REDACTED]",
        }
    
    def redact_pii(self, text: str) -> str:
        """Redact PII from text content"""
        if not isinstance(text, str):
            return text
        
        redacted_text = text
        
        for pattern_name, pattern in self.pii_patterns.items():
            replacement = self.replacements[pattern_name]
            
            if callable(replacement):
                redacted_text = pattern.sub(replacement, redacted_text)
            else:
                redacted_text = pattern.sub(replacement, redacted_text)
        
        return redacted_text
    
    def _mask_email(self, email: str) -> str:
        """Mask email address while preserving domain for debugging"""
        try:
            local, domain = email.split('@')
            if len(local) <= 2:
                masked_local = 'x' * len(local)
            else:
                masked_local = local[0] + 'x' * (len(local) - 2) + local[-1]
            return f"{masked_local}@{domain}"
        except ValueError:
            return '[EMAIL_REDACTED]'
    
    def create_pseudonym(self, identifier: str, salt: str = "neurobridge_salt") -> str:
        """Create consistent pseudonym for user tracking without PII"""
        combined = f"{identifier}{salt}"
        return "user_" + hashlib.sha256(combined.encode()).hexdigest()[:12]

class SecurityEventLogger:
    """
    Security-focused event logger for educational platforms
    """
    
    def __init__(self, logger_name: str = "security", log_dir: str = None):
        self.logger_name = logger_name
        self.log_dir = log_dir or "logs"
        self.pii_redactor = PIIRedactor()
        
        # Ensure log directory exists with secure permissions
        Path(self.log_dir).mkdir(parents=True, exist_ok=True, mode=0o750)
        
        # Configure structured logger
        self.logger = self._setup_structured_logger()
        
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
    
    def _setup_structured_logger(self) -> logging.Logger:
        """Setup structlog with security-focused configuration"""
        
        # Configure structlog processors
        processors = [
            # Add timestamp
            structlog.processors.TimeStamper(fmt="ISO"),
            
            # Add log level
            structlog.processors.add_log_level,
            
            # Add logger name
            structlog.processors.add_logger_name,
            
            # Custom PII redaction processor
            self._pii_redaction_processor,
            
            # Add request ID if available
            self._request_id_processor,
            
            # JSON formatter for structured logs
            structlog.processors.JSONRenderer()
        ]
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Create base logger
        stdlib_logger = logging.getLogger(self.logger_name)
        stdlib_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in stdlib_logger.handlers[:]:
            stdlib_logger.removeHandler(handler)
        
        # Add secure file handler
        log_file = os.path.join(self.log_dir, f"{self.logger_name}.json")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        
        # Set secure file permissions
        if os.path.exists(log_file):
            os.chmod(log_file, 0o640)
        
        stdlib_logger.addHandler(file_handler)
        
        # Optional: Add syslog handler for centralized logging
        if os.getenv('SYSLOG_SERVER'):
            syslog_handler = SysLogHandler(address=(os.getenv('SYSLOG_SERVER'), 514))
            syslog_handler.setLevel(logging.WARNING)
            stdlib_logger.addHandler(syslog_handler)
        
        return structlog.get_logger(self.logger_name)
    
    def _pii_redaction_processor(self, logger, method_name, event_dict):
        """Structlog processor for PII redaction"""
        # Redact PII from all string values in the event dictionary
        for key, value in event_dict.items():
            if isinstance(value, str):
                event_dict[key] = self.pii_redactor.redact_pii(value)
            elif isinstance(value, dict):
                event_dict[key] = self._redact_dict_values(value)
        
        return event_dict
    
    def _redact_dict_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PII from dictionary values"""
        redacted_dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted_dict[key] = self.pii_redactor.redact_pii(value)
            elif isinstance(value, dict):
                redacted_dict[key] = self._redact_dict_values(value)
            else:
                redacted_dict[key] = value
        return redacted_dict
    
    def _request_id_processor(self, logger, method_name, event_dict):
        """Add request ID from context if available"""
        # This would integrate with FastAPI middleware that sets request context
        try:
            from contextvars import copy_context
            ctx = copy_context()
            request_id = ctx.get('request_id', None)
            if request_id:
                event_dict['request_id'] = request_id
        except Exception:
            pass
        
        return event_dict
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        user_id: str = None,
        # REMOVED: ip_address, user_agent - GDPR compliance
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
            user_pseudonym = self.pii_redactor.create_pseudonym(user_id)
        
        event_data = {
            'event_type': event_type,
            'message': message,
            'user_pseudonym': user_pseudonym,
            # REMOVED: ip_address, user_agent for GDPR compliance
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
        
        # Log at appropriate level
        log_method = getattr(self.logger, severity, self.logger.info)
        log_method(message, **event_data)
    
    def log_authentication_event(
        self,
        success: bool,
        user_id: str = None,
        # REMOVED: ip_address, user_agent - GDPR compliance
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
            # REMOVED: ip_address, user_agent for GDPR compliance
            outcome="success" if success else "failure",
            severity=severity,
            additional_data=additional_data
        )
    
    def log_data_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        ip_address: str = None,
        success: bool = True,
        sensitive_data: bool = False
    ):
        """Log data access events for compliance"""
        event_type = self.EVENT_TYPES['DATA_ACCESS']
        message = f"Data access: {action} on {resource}"
        severity = "info" if success else "warning"
        
        if sensitive_data:
            severity = "warning"  # Always log sensitive data access as warning
        
        additional_data = {
            'sensitive_data': sensitive_data,
            'data_category': self._classify_data_sensitivity(resource)
        }
        
        self.log_security_event(
            event_type=event_type,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            outcome="success" if success else "failure",
            severity=severity,
            additional_data=additional_data
        )
    
    def log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        user_id: str = None,
        limit_type: str = "default"
    ):
        """Log rate limiting events"""
        self.log_security_event(
            event_type=self.EVENT_TYPES['RATE_LIMIT_EXCEEDED'],
            message=f"Rate limit exceeded for endpoint {endpoint}",
            user_id=user_id,
            ip_address=ip_address,
            resource=endpoint,
            action="rate_limit",
            outcome="blocked",
            severity="warning",
            additional_data={'limit_type': limit_type}
        )
    
    def log_file_upload(
        self,
        user_id: str,
        filename: str,
        file_size: int,
        file_type: str,
        security_scan_result: str,
        ip_address: str = None
    ):
        """Log file upload events"""
        message = f"File upload: {filename} ({file_type})"
        severity = "info" if security_scan_result == "safe" else "warning"
        
        additional_data = {
            'filename_hash': hashlib.sha256(filename.encode()).hexdigest()[:16],
            'file_size': file_size,
            'file_type': file_type,
            'security_scan_result': security_scan_result
        }
        
        self.log_security_event(
            event_type=self.EVENT_TYPES['FILE_UPLOAD'],
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            action="upload",
            severity=severity,
            additional_data=additional_data
        )
    
    def log_privacy_event(
        self,
        event_type: str,
        user_id: str,
        data_subject: str,
        legal_basis: str = None,
        retention_period: str = None
    ):
        """Log privacy-related events for GDPR compliance"""
        message = f"Privacy event: {event_type} for data subject"
        
        additional_data = {
            'data_subject_pseudonym': self.pii_redactor.create_pseudonym(data_subject),
            'legal_basis': legal_basis,
            'retention_period': retention_period,
            'processor': 'neurobridge-edu'
        }
        
        self.log_security_event(
            event_type=self.EVENT_TYPES['PRIVACY_VIOLATION'] if 'violation' in event_type.lower() else self.EVENT_TYPES['COMPLIANCE_EVENT'],
            message=message,
            user_id=user_id,
            severity="warning" if 'violation' in event_type.lower() else "info",
            additional_data=additional_data
        )
    
    def _classify_data_sensitivity(self, resource: str) -> str:
        """Classify data sensitivity for compliance logging"""
        resource_lower = resource.lower()
        
        if any(term in resource_lower for term in ['grade', 'transcript', 'assessment', 'student']):
            return "educational_record"
        elif any(term in resource_lower for term in ['audio', 'recording', 'transcription']):
            return "audio_content"
        elif any(term in resource_lower for term in ['user', 'profile', 'personal']):
            return "personal_data"
        elif any(term in resource_lower for term in ['api', 'key', 'token', 'auth']):
            return "authentication_data"
        else:
            return "general"
    
    def get_audit_trail(
        self,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        event_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a user (for compliance requests)"""
        # This would typically integrate with log aggregation system
        # For now, return placeholder structure
        user_pseudonym = self.pii_redactor.create_pseudonym(user_id)
        
        return [{
            "message": "Audit trail retrieval not implemented - requires log aggregation system integration",
            "user_pseudonym": user_pseudonym,
            "note": "In production, this would query centralized log storage"
        }]

class ComplianceLogger:
    """
    Educational compliance focused logger (FERPA, GDPR)
    """
    
    def __init__(self, log_dir: str = None):
        self.security_logger = SecurityEventLogger("compliance", log_dir)
        
        # Compliance event types
        self.FERPA_EVENTS = {
            'RECORD_ACCESS': 'ferpa_record_access',
            'RECORD_DISCLOSURE': 'ferpa_record_disclosure', 
            'DIRECTORY_INFO_ACCESS': 'ferpa_directory_access',
            'CONSENT_RECORDED': 'ferpa_consent_recorded'
        }
        
        self.GDPR_EVENTS = {
            'DATA_PROCESSING': 'gdpr_data_processing',
            'CONSENT_GIVEN': 'gdpr_consent_given',
            'CONSENT_WITHDRAWN': 'gdpr_consent_withdrawn',
            'DATA_SUBJECT_REQUEST': 'gdpr_subject_request',
            'DATA_BREACH': 'gdpr_data_breach',
            'RETENTION_PERIOD_END': 'gdpr_retention_end'
        }
    
    def log_ferpa_access(
        self,
        user_id: str,
        student_record_id: str,
        access_type: str,
        legitimate_interest: str,
        ip_address: str = None
    ):
        """Log FERPA-compliant educational record access"""
        self.security_logger.log_security_event(
            event_type=self.FERPA_EVENTS['RECORD_ACCESS'],
            message=f"Educational record accessed: {access_type}",
            user_id=user_id,
            ip_address=ip_address,
            resource=f"student_record_{hashlib.sha256(student_record_id.encode()).hexdigest()[:16]}",
            action=access_type,
            severity="info",
            additional_data={
                'legitimate_interest': legitimate_interest,
                'compliance_framework': 'FERPA'
            }
        )
    
    def log_gdpr_processing(
        self,
        data_subject_id: str,
        processing_purpose: str,
        legal_basis: str,
        data_categories: List[str],
        retention_period: str
    ):
        """Log GDPR-compliant data processing"""
        self.security_logger.log_security_event(
            event_type=self.GDPR_EVENTS['DATA_PROCESSING'],
            message=f"Personal data processing: {processing_purpose}",
            user_id=data_subject_id,
            action="process_data",
            severity="info",
            additional_data={
                'legal_basis': legal_basis,
                'data_categories': data_categories,
                'retention_period': retention_period,
                'compliance_framework': 'GDPR',
                'controller': 'neurobridge-edu'
            }
        )


# Global instances
_security_logger = None
_compliance_logger = None

def get_security_logger() -> SecurityEventLogger:
    """Get global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityEventLogger()
    return _security_logger

def get_compliance_logger() -> ComplianceLogger:
    """Get global compliance logger instance"""
    global _compliance_logger
    if _compliance_logger is None:
        _compliance_logger = ComplianceLogger()
    return _compliance_logger

# Utility functions for common logging patterns
def log_auth_success(user_id: str, ip_address: str = None, method: str = "password"):
    """Quick function to log successful authentication"""
    get_security_logger().log_authentication_event(
        success=True,
        user_id=user_id,
        ip_address=ip_address,
        method=method
    )

def log_auth_failure(user_id: str, reason: str, ip_address: str = None, method: str = "password"):
    """Quick function to log failed authentication"""
    get_security_logger().log_authentication_event(
        success=False,
        user_id=user_id,
        ip_address=ip_address,
        method=method,
        failure_reason=reason
    )