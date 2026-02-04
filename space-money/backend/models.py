"""Database models for Space Money."""
from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Integer
from sqlalchemy.sql import func
from database import Base
import uuid


class User(Base):
    """User account model."""
    __tablename__ = "users"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeanCustomer(Base):
    """Lean customer entity mapping."""
    __tablename__ = "lean_customers"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("transactions.users.id"), nullable=False, index=True)
    customer_id = Column(String, nullable=False, unique=True, index=True)
    app_user_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeanEntity(Base):
    """Linked bank account (entity) from Lean."""
    __tablename__ = "lean_entities"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("transactions.lean_customers.id"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, unique=True, index=True)
    bank_identifier = Column(String)
    status = Column(String, default="PENDING")  # PENDING, ACTIVE, ERROR
    permissions = Column(JSON)
    last_synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeanAccount(Base):
    """Bank account from Lean entity."""
    __tablename__ = "lean_accounts"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(String, ForeignKey("transactions.lean_entities.id"), nullable=False, index=True)
    account_id = Column(String, nullable=False, unique=True, index=True)
    account_number = Column(String)
    account_type = Column(String)
    currency = Column(String)
    balance = Column(String)
    available_balance = Column(String)
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeanSyncLog(Base):
    """Log of data sync operations."""
    __tablename__ = "lean_sync_logs"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(String, ForeignKey("transactions.lean_entities.id"), nullable=False, index=True)
    sync_type = Column(String, nullable=False)  # identity, accounts, balance, transactions
    status = Column(String, nullable=False)  # success, error, pending
    file_path = Column(String)
    error_message = Column(String)
    records_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BalanceHistory(Base):
    """Historical balance tracking for accounts."""
    __tablename__ = "balance_history"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False, index=True)  # Lean account_id (not FK to avoid constraint issues)
    entity_id = Column(String, ForeignKey("transactions.lean_entities.id"), nullable=False, index=True)
    balance = Column(String, nullable=False)  # Store as string to preserve precision
    available_balance = Column(String)
    currency_code = Column(String)
    account_name = Column(String)
    account_type = Column(String)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    raw_data = Column(JSON)  # Store full balance response


class RecurringTransaction(Base):
    """Detected recurring transactions/subscriptions."""
    __tablename__ = "recurring_transactions"
    __table_args__ = {"schema": "transactions"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False, index=True)
    entity_id = Column(String, ForeignKey("transactions.lean_entities.id"), nullable=False, index=True)
    merchant_name = Column(String, nullable=False)
    category = Column(String)
    frequency = Column(String)  # DAILY, WEEKLY, MONTHLY, YEARLY
    average_amount = Column(String)
    currency_code = Column(String)
    last_transaction_date = Column(DateTime(timezone=True))
    predicted_next_date = Column(DateTime(timezone=True))
    transaction_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    confidence_score = Column(String)  # How confident we are this is recurring
    transaction_ids = Column(JSON)  # List of transaction IDs that match this pattern
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
