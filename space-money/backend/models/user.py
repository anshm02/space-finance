"""
DIFC Compliance: User schema models for Space Money.

This module contains user-related tables with field-level encryption
for personal information as required for DIFC compliance.
"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, CheckConstraint, ForeignKey, Index, DECIMAL, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum

from database import Base
from utils.encryption import EncryptedType, hash_value


# Enums for user schema
class AccountStatus(str, enum.Enum):
    """User account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Sex(str, enum.Enum):
    """User sex/gender."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class IncomeSource(str, enum.Enum):
    """Source of income estimate."""
    USER_PROVIDED = "user_provided"
    AUTO_DETECTED = "auto_detected"


class ConsentType(str, enum.Enum):
    """Types of user consent."""
    DATA_PROCESSING = "data_processing"
    OPEN_FINANCE_ACCESS = "open_finance_access"
    MARKETING = "marketing"
    ANALYTICS = "analytics"


class IngestionMethod(str, enum.Enum):
    """Data ingestion method."""
    REAL_TIME = "real_time"
    MANUAL = "manual"


class SyncStatus(str, enum.Enum):
    """Sync status for data ingestion."""
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    EXPIRED = "expired"


class UserProfile(Base):
    """
    User account profiles.
    
    DIFC Compliance: Email is encrypted with AES-256.
    """
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "user"}
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(EncryptedType(500), nullable=False, unique=True, index=True)  # Encrypted
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))
    account_status = Column(
        Enum(AccountStatus, name="account_status_enum", create_type=True),
        default=AccountStatus.ACTIVE,
        nullable=False
    )
    country_code = Column(String(2), nullable=False)


class UserDemographics(Base):
    """
    User demographic information.
    
    Linked 1:1 with UserProfile.
    """
    __tablename__ = "user_demographics"
    __table_args__ = (
        CheckConstraint("age >= 18 AND age <= 100", name="age_check"),
        CheckConstraint("income_estimate >= 0", name="income_estimate_check"),
        {"schema": "user"}
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    age = Column(Integer, nullable=False)
    sex = Column(Enum(Sex, name="sex_enum", create_type=True))
    income_estimate = Column(DECIMAL(10, 2))
    income_source = Column(Enum(IncomeSource, name="income_source_enum", create_type=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConsentRecord(Base):
    """
    User consent records for DIFC compliance.
    
    DIFC Compliance: IP addresses are hashed with SHA-256.
    Records all consent grants and revocations.
    """
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("idx_consent_user_type_revoked", "user_id", "consent_type", "revoked_at"),
        {"schema": "user"}
    )
    
    consent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    consent_type = Column(
        Enum(ConsentType, name="consent_type_enum", create_type=True),
        nullable=False
    )
    consent_text_version = Column(String(50), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    ip_address = Column(String(64), nullable=False)  # Hashed SHA-256
    
    def set_ip_address(self, ip: str):
        """Set IP address (automatically hashed)."""
        self.ip_address = hash_value(ip)


class DataIngestionConfig(Base):
    """
    User data ingestion configuration.
    
    DIFC Compliance: Lean access tokens are encrypted with AES-256.
    """
    __tablename__ = "data_ingestion_config"
    __table_args__ = {"schema": "user"}
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    ingestion_method = Column(
        Enum(IngestionMethod, name="ingestion_method_enum", create_type=True),
        nullable=False
    )
    open_finance_provider = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    lean_access_token = Column(EncryptedType(1000))  # Encrypted
    token_expires_at = Column(DateTime(timezone=True))
    last_sync_timestamp = Column(DateTime(timezone=True))
    sync_status = Column(
        Enum(SyncStatus, name="sync_status_enum", create_type=True),
        default=SyncStatus.ACTIVE
    )
