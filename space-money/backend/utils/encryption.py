"""
DIFC Compliance: Field-level encryption utilities for PII data.

This module provides AES-256 encryption for sensitive personal information
and SHA-256 hashing for IP addresses as required for DIFC compliance.

Encryption at rest is enabled at the database level (AWS RDS).
Field-level encryption provides additional security for highly sensitive PII.
"""
import os
import hashlib
from typing import Any, Optional
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String


def get_encryption_key() -> bytes:
    """
    Get encryption key from environment variable.
    
    Returns:
        Encryption key as bytes
        
    Raises:
        ValueError: If ENCRYPTION_KEY is not set
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return key.encode()


# Initialize Fernet cipher for AES-256 encryption
_cipher = None

def _get_cipher() -> Fernet:
    """Get or create Fernet cipher instance."""
    global _cipher
    if _cipher is None:
        _cipher = Fernet(get_encryption_key())
    return _cipher


def hash_value(value: str) -> str:
    """
    Hash a value using SHA-256.
    
    Used for IP addresses where we need to log but not store plaintext.
    
    Args:
        value: String to hash
        
    Returns:
        SHA-256 hash as hex string
    """
    return hashlib.sha256(value.encode()).hexdigest()


class EncryptedType(TypeDecorator):
    """
    SQLAlchemy custom type for AES-256 encrypted string fields.
    
    Automatically encrypts values on write and decrypts on read.
    Stores encrypted data as base64-encoded string in database.
    
    Usage:
        email = Column(EncryptedType(255), nullable=False)
    """
    impl = String
    cache_ok = True
    
    def __init__(self, length: int = 255, **kwargs):
        """
        Initialize encrypted type.
        
        Args:
            length: Maximum length of encrypted string in database
            **kwargs: Additional SQLAlchemy column arguments
        """
        super().__init__(length=length, **kwargs)
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Encrypt value before storing in database.
        
        Args:
            value: Plaintext value to encrypt
            dialect: Database dialect
            
        Returns:
            Encrypted value as base64 string, or None if value is None
        """
        if value is None:
            return None
        
        cipher = _get_cipher()
        encrypted = cipher.encrypt(value.encode())
        return encrypted.decode()
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Decrypt value when reading from database.
        
        Args:
            value: Encrypted base64 string from database
            dialect: Database dialect
            
        Returns:
            Decrypted plaintext value, or None if value is None
        """
        if value is None:
            return None
        
        cipher = _get_cipher()
        decrypted = cipher.decrypt(value.encode())
        return decrypted.decode()
