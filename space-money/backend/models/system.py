"""
DIFC Compliance: System schema models for Space Money.

This module contains system and audit tables for DIFC compliance.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum

from database import Base
from utils.encryption import hash_value


# Enums for system schema
class EventType(str, enum.Enum):
    """Audit event types."""
    USER_LOGIN = "user_login"
    DATA_EXPORT = "data_export"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    ACCOUNT_DELETED = "account_deleted"
    ADMIN_ACCESS = "admin_access"
    LEAN_SYNC = "lean_sync"


class EntityType(str, enum.Enum):
    """Entity types for audit logging."""
    TRANSACTION = "transaction"
    ACCOUNT = "account"
    USER_PROFILE = "user_profile"
    CONSENT_RECORD = "consent_record"


class AuditLog(Base):
    """
    Audit log for DIFC compliance.
    
    DIFC Compliance: IP addresses are hashed with SHA-256.
    Records all significant events in the system.
    """
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_log_user_timestamp", "user_id", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_audit_log_event_timestamp", "event_type", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        {"schema": "system"}
    )
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="SET NULL"),
        nullable=True
    )
    event_type = Column(
        Enum(EventType, name="event_type_enum", create_type=True),
        nullable=False
    )
    entity_type = Column(Enum(EntityType, name="entity_type_enum", create_type=True))
    entity_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(64), nullable=False)  # Hashed SHA-256
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def set_ip_address(self, ip: str):
        """Set IP address (automatically hashed)."""
        self.ip_address = hash_value(ip)
