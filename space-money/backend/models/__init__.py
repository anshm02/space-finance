"""
SQLAlchemy models for Space Money database.

All models are organized by PostgreSQL schema:
- user: User profiles, demographics, consent, data ingestion config
- accounts: Bank accounts, balances, credit card details
- transactions: Raw transaction data with enrichment
- system: Audit logs

DIFC Compliance Notes:
- Field-level encryption with AES-256 for PII (email, account numbers, IBAN, descriptions, tokens)
- SHA-256 hashing for IP addresses
- AWS RDS encryption at rest
- Comprehensive audit logging
"""
from database import Base

# Import all models for Alembic autodiscovery
from models.user import (
    UserProfile,
    UserDemographics,
    ConsentRecord,
    DataIngestionConfig,
    AccountStatus as UserAccountStatus,
    Sex,
    IncomeSource,
    ConsentType,
    IngestionMethod,
    SyncStatus
)

from models.accounts import (
    UserAccount,
    AccountBalance,
    CreditCardDetails,
    AccountType,
    AccountStatus
)

from models.transactions import (
    RawTransaction,
    TransactionType
)

from models.system import (
    AuditLog,
    EventType,
    EntityType
)

# Legacy models from old models.py for backward compatibility
# These use the old 'transactions' schema for Lean integration
import sys
import os
import importlib.util

# Calculate path to legacy models.py (parent directory of this package)
current_dir = os.path.dirname(os.path.abspath(__file__))
legacy_models_path = os.path.join(os.path.dirname(current_dir), "models.py")

spec = importlib.util.spec_from_file_location("legacy_models", legacy_models_path)
legacy = importlib.util.module_from_spec(spec)
sys.modules["legacy_models"] = legacy
spec.loader.exec_module(legacy)

# Export legacy models
User = legacy.User
LeanCustomer = legacy.LeanCustomer  
LeanEntity = legacy.LeanEntity
LeanAccount = legacy.LeanAccount
LeanSyncLog = legacy.LeanSyncLog
BalanceHistory = legacy.BalanceHistory
RecurringTransaction = legacy.RecurringTransaction

__all__ = [
    "Base",
    # User schema
    "UserProfile",
    "UserDemographics",
    "ConsentRecord",
    "DataIngestionConfig",
    "UserAccountStatus",
    "Sex",
    "IncomeSource",
    "ConsentType",
    "IngestionMethod",
    "SyncStatus",
    # Accounts schema
    "UserAccount",
    "AccountBalance",
    "CreditCardDetails",
    "AccountType",
    "AccountStatus",
    # Transactions schema
    "RawTransaction",
    "TransactionType",
    # System schema
    "AuditLog",
    "EventType",
    "EntityType",
    # Legacy Lean integration models
    "User",
    "LeanCustomer",
    "LeanEntity",
    "LeanAccount",
    "LeanSyncLog",
    "BalanceHistory",
    "RecurringTransaction",
]
