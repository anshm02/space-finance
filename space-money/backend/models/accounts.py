"""
DIFC Compliance: Accounts schema models for Space Money.

This module contains account-related tables with field-level encryption
for sensitive financial information.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Enum, CheckConstraint, ForeignKey, Index, DECIMAL, Date
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum

from database import Base
from utils.encryption import EncryptedType


# Enums for accounts schema
class AccountType(str, enum.Enum):
    """Bank account type."""
    CURRENT = "CURRENT"
    SAVINGS = "SAVINGS"
    CREDIT = "CREDIT"


class AccountStatus(str, enum.Enum):
    """Account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"


class UserAccount(Base):
    """
    User bank accounts from Lean Technologies.
    
    DIFC Compliance: Account numbers and IBANs are encrypted with AES-256.
    """
    __tablename__ = "user_accounts"
    __table_args__ = (
        Index("idx_user_accounts_user_id", "user_id"),
        Index("idx_user_accounts_lean_account_id", "lean_account_id"),
        {"schema": "accounts"}
    )
    
    account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    lean_account_id = Column(UUID(as_uuid=True))
    institution_name = Column(String(100), nullable=False)
    account_name = Column(String(100), nullable=False)
    account_number = Column(EncryptedType(500))  # Encrypted
    iban = Column(EncryptedType(500))  # Encrypted
    account_type = Column(
        Enum(AccountType, name="account_type_enum", create_type=True),
        nullable=False
    )
    currency_code = Column(String(3), default="AED", nullable=False)
    account_status = Column(
        Enum(AccountStatus, name="account_status_enum", create_type=True),
        default=AccountStatus.ACTIVE
    )
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True))


class AccountBalance(Base):
    """
    Account balance snapshots for historical tracking.
    
    Stores balance at each sync point for trend analysis.
    """
    __tablename__ = "account_balances"
    __table_args__ = (
        Index("idx_account_balances_account_timestamp", "account_id", "snapshot_timestamp", postgresql_ops={"snapshot_timestamp": "DESC"}),
        {"schema": "accounts"}
    )
    
    balance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.user_accounts.account_id", ondelete="CASCADE"),
        nullable=False
    )
    snapshot_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    balance = Column(DECIMAL(12, 2), nullable=False)
    currency_code = Column(String(3), nullable=False)


class CreditCardDetails(Base):
    """
    Credit card specific details.
    
    DIFC Compliance: Card last four digits are encrypted.
    """
    __tablename__ = "credit_card_details"
    __table_args__ = (
        CheckConstraint("credit_limit > 0", name="credit_limit_check"),
        CheckConstraint("next_payment_due_amount >= 0", name="payment_due_amount_check"),
        {"schema": "accounts"}
    )
    
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.user_accounts.account_id", ondelete="CASCADE"),
        primary_key=True
    )
    card_last_four = Column(EncryptedType(100))  # Encrypted
    credit_limit = Column(DECIMAL(10, 2), nullable=False)
    next_payment_due_date = Column(Date)
    next_payment_due_amount = Column(DECIMAL(10, 2))
