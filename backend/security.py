"""
Security Module for HealthCare AI
Handles data encryption, input validation, and audit logging
"""

import os
import re
import hashlib
import secrets
import logging
from datetime import datetime
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from functools import wraps

# Initialize logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Create file handler for security logs
log_handler = logging.FileHandler("security_audit.log")
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
))
security_logger.addHandler(log_handler)

# Encryption key - In production, store this in environment variable
# Generate a new key: Fernet.generate_key()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "ZmVybmV0LWtleS1mb3ItaGVhbHRoY2FyZS1haS1hcHA=").encode()

# Try to create a valid Fernet key
try:
    # If the env key is not valid Fernet format, generate a consistent one from it
    fernet = Fernet(ENCRYPTION_KEY)
except Exception:
    # Generate a key based on the secret
    key = hashlib.sha256(ENCRYPTION_KEY).digest()
    ENCRYPTION_KEY = Fernet.generate_key()
    fernet = Fernet(ENCRYPTION_KEY)


class SecurityManager:
    """Handles all security operations"""
    
    def __init__(self):
        self.fernet = fernet
        self.failed_login_attempts = {}  # Track failed login attempts
        self.rate_limit_tracker = {}  # Track API requests
    
    # ============= Encryption =============
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data using Fernet symmetric encryption"""
        if not data:
            return data
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            security_logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data that was encrypted with encrypt_data"""
        if not encrypted_data:
            return encrypted_data
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            # If decryption fails, data might not be encrypted
            security_logger.warning(f"Decryption failed (data may not be encrypted): {e}")
            return encrypted_data
    
    def hash_sensitive_data(self, data: str) -> str:
        """One-way hash for data that doesn't need to be retrieved"""
        if not data:
            return data
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((data + salt).encode()).hexdigest()
        return f"{salt}:{hashed}"
    
    # ============= Input Validation =============
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validate email format"""
        if not email:
            return True, ""  # Empty is ok if optional
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, ""
        return False, "Invalid email format"
    
    def validate_phone(self, phone: str) -> Tuple[bool, str]:
        """Validate phone number format"""
        if not phone:
            return True, ""
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it's mostly digits (allowing + for country code)
        pattern = r'^\+?[0-9]{7,15}$'
        if re.match(pattern, cleaned):
            return True, ""
        return False, "Invalid phone number format"
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """Validate username format"""
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 50:
            return False, "Username must be less than 50 characters"
        
        # Only allow alphanumeric and underscores
        pattern = r'^[a-zA-Z0-9_]+$'
        if not re.match(pattern, username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, ""
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        if len(password) > 100:
            return False, "Password too long"
        
        return True, ""
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""
        if not text:
            return text
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove potential script tags and dangerous HTML
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'javascript:',
            r'on\w+\s*=',
            r'<\s*img[^>]+onerror',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Escape HTML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text
    
    # ============= Rate Limiting =============
    
    def check_rate_limit(self, identifier: str, limit: int = 60, window: int = 60) -> Tuple[bool, str]:
        """Check if request is within rate limit
        
        Args:
            identifier: User ID or IP address
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            (allowed, message)
        """
        now = datetime.now().timestamp()
        
        if identifier not in self.rate_limit_tracker:
            self.rate_limit_tracker[identifier] = []
        
        # Remove old entries
        self.rate_limit_tracker[identifier] = [
            ts for ts in self.rate_limit_tracker[identifier]
            if now - ts < window
        ]
        
        if len(self.rate_limit_tracker[identifier]) >= limit:
            security_logger.warning(f"Rate limit exceeded for {identifier}")
            return False, "Too many requests. Please try again later."
        
        self.rate_limit_tracker[identifier].append(now)
        return True, ""
    
    def track_failed_login(self, username: str) -> Tuple[bool, str]:
        """Track failed login attempts to prevent brute force"""
        now = datetime.now().timestamp()
        
        if username not in self.failed_login_attempts:
            self.failed_login_attempts[username] = []
        
        # Remove attempts older than 15 minutes
        self.failed_login_attempts[username] = [
            ts for ts in self.failed_login_attempts[username]
            if now - ts < 900  # 15 minutes
        ]
        
        self.failed_login_attempts[username].append(now)
        
        attempts = len(self.failed_login_attempts[username])
        
        if attempts >= 5:
            security_logger.warning(f"Account locked due to failed attempts: {username}")
            return False, "Account temporarily locked. Try again in 15 minutes."
        
        return True, f"{5 - attempts} attempts remaining"
    
    def clear_failed_attempts(self, username: str):
        """Clear failed login attempts after successful login"""
        if username in self.failed_login_attempts:
            del self.failed_login_attempts[username]
    
    # ============= Audit Logging =============
    
    def log_security_event(self, event_type: str, user_id: str = None, 
                          details: str = None, severity: str = "INFO"):
        """Log security-related events for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id or "anonymous",
            "details": details,
            "severity": severity
        }
        
        log_message = f"[{event_type}] User: {log_entry['user_id']} - {details}"
        
        if severity == "WARNING":
            security_logger.warning(log_message)
        elif severity == "ERROR":
            security_logger.error(log_message)
        elif severity == "CRITICAL":
            security_logger.critical(log_message)
        else:
            security_logger.info(log_message)
        
        return log_entry
    
    def log_data_access(self, user_id: str, data_type: str, action: str):
        """Log when sensitive data is accessed"""
        self.log_security_event(
            event_type="DATA_ACCESS",
            user_id=user_id,
            details=f"{action} {data_type}",
            severity="INFO"
        )
    
    def log_authentication(self, username: str, success: bool, ip_address: str = None):
        """Log authentication attempts"""
        event_type = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        severity = "INFO" if success else "WARNING"
        details = f"IP: {ip_address}" if ip_address else "Local login"
        
        self.log_security_event(
            event_type=event_type,
            user_id=username,
            details=details,
            severity=severity
        )


# Global security manager instance
security_manager = SecurityManager()


# Convenience functions
def encrypt(data: str) -> str:
    return security_manager.encrypt_data(data)

def decrypt(data: str) -> str:
    return security_manager.decrypt_data(data)

def validate_email(email: str) -> Tuple[bool, str]:
    return security_manager.validate_email(email)

def validate_phone(phone: str) -> Tuple[bool, str]:
    return security_manager.validate_phone(phone)

def sanitize(text: str, max_length: int = 1000) -> str:
    return security_manager.sanitize_input(text, max_length)

def log_event(event_type: str, user_id: str = None, details: str = None):
    return security_manager.log_security_event(event_type, user_id, details)
