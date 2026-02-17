"""
DIFC Compliance: Transactions schema models for Space Money.

This module contains transaction-related tables with field-level encryption
for transaction descriptions.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Enum, CheckConstraint, ForeignKey, Index, DECIMAL, Date, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import enum

from database import Base
from utils.encryption import EncryptedType


# Enums for transactions schema
class TransactionType(str, enum.Enum):
    """Transaction type."""
    DEBIT = "debit"
    CREDIT = "credit"


class RawTransaction(Base):
    """
    Raw transaction data from Lean Technologies with enrichment.
    
    DIFC Compliance: Transaction descriptions are encrypted with AES-256.
    Includes Lean Insights categorization data.
    """
    __tablename__ = "raw_transactions"
    __table_args__ = (
        CheckConstraint(
            "lean_category_confidence >= 0 AND lean_category_confidence <= 1",
            name="category_confidence_check"
        ),
        Index("idx_raw_transactions_user_date", "user_id", "transaction_date", postgresql_ops={"transaction_date": "DESC"}),
        Index("idx_raw_transactions_account_date", "account_id", "transaction_date", postgresql_ops={"transaction_date": "DESC"}),
        Index("idx_raw_transactions_lean_id", "lean_transaction_id"),
        {"schema": "transactions"}
    )
    
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.user_accounts.account_id", ondelete="CASCADE"),
        nullable=False
    )
    lean_transaction_id = Column(UUID(as_uuid=True), unique=True)
    transaction_date = Column(Date, nullable=False)
    transaction_timestamp = Column(DateTime(timezone=True))  # Full timestamp from Lean API
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    description = Column(EncryptedType(2000))  # Encrypted raw description
    description_cleansed = Column(String(255))  # Cleansed/normalized description (not encrypted)
    transaction_type = Column(
        Enum(TransactionType, name="transaction_type_enum", create_type=True),
        nullable=False
    )
    is_pending = Column(Boolean, default=False)
    transaction_reference = Column(String(100))
    
    # Lean Insights enrichment fields
    lean_insights_category = Column(String(50))
    lean_insights_type = Column(String(50))
    lean_category_confidence = Column(DECIMAL(3, 2))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
