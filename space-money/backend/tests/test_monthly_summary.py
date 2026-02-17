"""
Test for derived monthly summaries.
"""
import asyncio
import os
from cryptography.fernet import Fernet

# Set encryption key for tests before importing models
if not os.getenv("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import uuid
import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import get_settings
from models.user import UserProfile
from models.accounts import UserAccount, AccountType
from models.transactions import RawTransaction, TransactionType
from models.category_mappings import CategoryMapping
from models.analytics import DerivedMonthlySummary
from services.analytics_service import compute_monthly_summaries

settings = get_settings()

@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    # Use the same DB as config (likely local postgres)
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_compute_monthly_summaries(db_session):
    """
    Test computation of monthly summaries.
    """
    # 1. Setup Data
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    print(f"\nSetting up test data for user {user_id}...")

    # Create User
    user = UserProfile(
        user_id=user_id,
        username=f"test_summary_{user_id.hex[:8]}",
        email=f"test_{user_id.hex[:8]}@example.com",
        password_hash="hash",
        country_code="AE",
        account_status="ACTIVE"
    )
    db_session.add(user)
    await db_session.flush()
    print(f"User inserted: {user.user_id}")
    
    # Create Account
    account = UserAccount(
        account_id=account_id,
        user_id=user_id,
        institution_name="Test Bank",
        account_name="Test Account",
        account_type=AccountType.CURRENT,
        currency_code="AED"
    )
    db_session.add(account)
    await db_session.flush()

    # Insert Category Mappings (System Defaults)
    # We do this manually to ensure test isolation/determinism even if migration didn't run or DB is empty
    defaults = [
        ('RENT_AND_SERVICES', 'fixed', False, False),
        ('GOVERNMENT', 'fixed', False, False), # Unused in test but part of defaults
        ('LOANS_AND_INVESTMENTS', 'fixed', False, False), # Unused
        ('GROCERIES', 'flexible', False, False),
        ('HEALTH_AND_WELLBEING', 'flexible', False, False), # Unused
        ('RESTAURANTS_DINING', 'flexible', False, False),
        ('ENTERTAINMENT', 'flexible', False, False), # Unused
        ('RETAIL', 'flexible', False, False), # Unused
        ('SALARY_AND_REVENUE', 'savings', True, True),
        ('TRANSFER', 'savings', False, True)
    ]
    
    for lean_cat, bucket, is_inc, exc_exp in defaults:
        # Check if exists (system default user_id is NULL)
        stmt = select(CategoryMapping).where(
            CategoryMapping.user_id.is_(None),
            CategoryMapping.lean_category == lean_cat
        )
        res = await db_session.execute(stmt)
        if not res.scalar_one_or_none():
            db_session.add(CategoryMapping(
                user_id=None,
                lean_category=lean_cat,
                display_name=lean_cat,
                bucket=bucket,
                is_income=is_inc,
                exclude_from_expenses=exc_exp
            ))
    
    await db_session.flush()

    # Insert Transactions
    # All in Jan 2024
    tx_date = date(2024, 1, 15)
    
    transactions_data = [
        # Income: 2x 7500 = 15000
        ('SALARY_AND_REVENUE', 7500, 'credit'),
        ('SALARY_AND_REVENUE', 7500, 'credit'),
        
        # Fixed: 2x 3500 = 7000
        ('RENT_AND_SERVICES', 3500, 'debit'),
        ('RENT_AND_SERVICES', 3500, 'debit'),
        
        # Flexible: 3x 200 + 1x 400 = 1000
        ('RESTAURANTS_DINING', 200, 'debit'),
        ('RESTAURANTS_DINING', 200, 'debit'),
        ('RESTAURANTS_DINING', 200, 'debit'),
        ('GROCERIES', 400, 'debit'),
        
        # Excluded from expenses (TRANSFER): 2x 1000 = 2000
        ('TRANSFER', 1000, 'debit'),
        ('TRANSFER', 1000, 'debit'),
    ]
    
    for cat, amount, tx_type in transactions_data:
        tx = RawTransaction(
            transaction_id=uuid.uuid4(),
            user_id=user_id,
            account_id=account_id,
            transaction_date=tx_date,
            amount=Decimal(amount),
            currency_code="AED",
            transaction_type=TransactionType[tx_type.upper()],
            lean_insights_category=cat,
            description="Test Transaction"
        )
        db_session.add(tx)
        
    await db_session.commit()
    print("✓ Test data inserted.")

    # 2. Run Computation
    print("Running computation...")
    await compute_monthly_summaries(db_session, user_id, date(2024, 1, 1))

    # 3. Assertions
    print("Verifying results...")
    stmt = select(DerivedMonthlySummary).where(
        DerivedMonthlySummary.user_id == user_id,
        DerivedMonthlySummary.period_month == date(2024, 1, 1)
    )
    result = await db_session.execute(stmt)
    summary = result.scalar_one_or_none()
    
    assert summary is not None, "Summary record not created"
    
    print(f"  Income: {summary.total_income} (Expected 15000.00)")
    assert summary.total_income == Decimal('15000.00')
    
    print(f"  Expenses: {summary.total_expenses} (Expected 8000.00)")
    assert summary.total_expenses == Decimal('8000.00')
    
    print(f"  Fixed: {summary.total_fixed} (Expected 7000.00)")
    assert summary.total_fixed == Decimal('7000.00')
    
    print(f"  Flexible: {summary.total_flexible} (Expected 1000.00)")
    assert summary.total_flexible == Decimal('1000.00')
    
    print(f"  Net Savings: {summary.net_savings} (Expected 7000.00)")
    assert summary.net_savings == Decimal('7000.00')
    
    # 7000 / 15000 * 100 = 46.6666... -> 46.67
    print(f"  Savings Rate: {summary.savings_rate} (Expected 46.67)")
    # Compare with slight tolerance or precise decimal match depending on rounding implementation in DB/Service
    # DB stores 5,2 so it should be rounded.
    assert summary.savings_rate == Decimal('46.67')
    
    print("✓ All assertions passed.")

    # Cleanup
    # Delete User (Cascade should handle the rest)
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
    await db_session.commit()

if __name__ == "__main__":
    asyncio.run(test_compute_monthly_summaries(None)) # Helper for manual run if needed, though pytest handles fixture
