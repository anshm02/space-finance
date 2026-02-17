"""
Full pipeline integration test for Space Money analytics.

Sets up a complete user scenario with 3 accounts, 50+ transactions across
3 months, and validates all derived tables, budgets, recurring detection,
and health scores.
"""
import asyncio
import os
from cryptography.fernet import Fernet

# Set encryption key before importing models
if not os.getenv("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import uuid
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import text, select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import get_settings
from models.user import UserProfile
from models.accounts import UserAccount, CreditCardDetails, AccountType
from models.transactions import RawTransaction, TransactionType
from models.category_mappings import CategoryMapping
from models.analytics import (
    DerivedMonthlySummary,
    DerivedCategorySummary,
    AppBudget,
    AppBudgetPeriod,
    DerivedRecurringTransaction,
    DerivedHealthScore,
    DerivedHealthScoreDriver,
)
from services.analytics_service import run_health_checkup_pipeline

settings = get_settings()


@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
    await engine.dispose()


def _make_tx(user_id, account_id, tx_date, amount, category, description_cleansed=None, tx_type=None):
    """Helper to create a raw transaction."""
    if tx_type is None:
        tx_type = TransactionType.CREDIT if category == "SALARY_AND_REVENUE" else TransactionType.DEBIT
    return RawTransaction(
        transaction_id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        transaction_date=tx_date,
        amount=Decimal(str(amount)),
        currency_code="AED",
        transaction_type=tx_type,
        lean_insights_category=category,
        description="Test",
        description_cleansed=description_cleansed,
    )


@pytest.mark.asyncio
async def test_full_pipeline(db_session):
    """
    Full pipeline integration test:
    - 3 accounts (CURRENT, SAVINGS, CREDIT)
    - 50+ transactions across 3 months
    - Validates all derived tables
    """
    user_id = uuid.uuid4()
    current_account_id = uuid.uuid4()
    savings_account_id = uuid.uuid4()
    credit_account_id = uuid.uuid4()

    print(f"\n{'='*60}")
    print(f"FULL PIPELINE TEST — user {user_id}")
    print(f"{'='*60}")

    # ---------------------------------------------------------------
    #  SETUP
    # ---------------------------------------------------------------

    # 1. User
    user = UserProfile(
        user_id=user_id,
        username=f"test_pipeline_{user_id.hex[:8]}",
        email=f"pipeline_{user_id.hex[:8]}@test.com",
        password_hash="hash",
        country_code="AE",
        account_status="ACTIVE",
    )
    db_session.add(user)
    await db_session.flush()

    # 2. Accounts
    current = UserAccount(
        account_id=current_account_id,
        user_id=user_id,
        institution_name="Test Bank",
        account_name="Current Account",
        account_type=AccountType.CURRENT,
        currency_code="AED",
        current_balance=Decimal("15000.00"),
    )
    savings = UserAccount(
        account_id=savings_account_id,
        user_id=user_id,
        institution_name="Test Bank",
        account_name="Savings Account",
        account_type=AccountType.SAVINGS,
        currency_code="AED",
        current_balance=Decimal("5000.00"),
    )
    credit = UserAccount(
        account_id=credit_account_id,
        user_id=user_id,
        institution_name="Test Bank",
        account_name="Credit Card",
        account_type=AccountType.CREDIT,
        currency_code="AED",
        current_balance=Decimal("2800.00"),
    )
    db_session.add_all([current, savings, credit])
    await db_session.flush()

    # 3. Credit card details
    cc = CreditCardDetails(
        account_id=credit_account_id,
        card_last_four="1234",
        credit_limit=Decimal("10000.00"),
    )
    db_session.add(cc)
    await db_session.flush()

    # 4. Category mappings (ensure system defaults exist)
    defaults = [
        ("RENT_AND_SERVICES", "Rent & Services", "fixed", False, False),
        ("GOVERNMENT", "Government", "fixed", False, False),
        ("LOANS_AND_INVESTMENTS", "Loans & Investments", "fixed", False, False),
        ("GROCERIES", "Groceries", "flexible", False, False),
        ("HEALTH_AND_WELLBEING", "Health & Wellbeing", "flexible", False, False),
        ("RESTAURANTS_DINING", "Restaurants & Dining", "flexible", False, False),
        ("ENTERTAINMENT", "Entertainment", "flexible", False, False),
        ("RETAIL", "Retail", "flexible", False, False),
        ("SALARY_AND_REVENUE", "Salary & Revenue", "savings", True, True),
        ("TRANSFER", "Transfer", "savings", False, True),
    ]
    for lean, display, bucket, is_inc, exc in defaults:
        exists = await db_session.execute(
            select(CategoryMapping).where(
                CategoryMapping.user_id.is_(None),
                CategoryMapping.lean_category == lean,
            )
        )
        if not exists.scalar_one_or_none():
            db_session.add(CategoryMapping(
                user_id=None, lean_category=lean, display_name=display,
                bucket=bucket, is_income=is_inc, exclude_from_expenses=exc,
            ))
    await db_session.flush()

    # 5. Transactions — 3 months: Dec 2025, Jan 2026, Feb 2026
    txns = []
    months = [
        (date(2025, 12, 1), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 10)),
    ]

    for m_idx, (m_start, m_end) in enumerate(months):
        # Salary — 1x per month
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 1),
                             15000, "SALARY_AND_REVENUE", "SALARY CORP"))

        # Rent — 1x per month
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 5),
                             4500, "RENT_AND_SERVICES", "RENT PAYMENT"))

        # DEWA — 1x per month (monthly bill for recurring detection)
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 10),
                             450, "RENT_AND_SERVICES", "DEWA PAYMENT"))

        # Groceries — 3x per month
        for day in [7, 14, 21]:
            d = date(m_start.year, m_start.month, min(day, 28))
            txns.append(_make_tx(user_id, current_account_id, d,
                                 350 + m_idx * 10, "GROCERIES", f"CARREFOUR #{day}"))

        # Restaurants — 2x per month
        for day in [8, 18]:
            d = date(m_start.year, m_start.month, min(day, 28))
            txns.append(_make_tx(user_id, current_account_id, d,
                                 150 + m_idx * 5, "RESTAURANTS_DINING"))

        # Entertainment — 1x per month (non-Netflix)
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 20),
                             200, "ENTERTAINMENT"))

        # Retail — 1x per month
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 15),
                             300 + m_idx * 20, "RETAIL"))

        # Transfer — 1x per month (excluded from expenses)
        txns.append(_make_tx(user_id, current_account_id, date(m_start.year, m_start.month, 2),
                             1000, "TRANSFER", "SAVINGS TRANSFER"))

    # Netflix charges — 4 monthly charges (Nov, Dec, Jan, Feb) for recurring detection
    netflix_dates = [date(2025, 11, 15), date(2025, 12, 15), date(2026, 1, 15), date(2026, 2, 15)]
    for nd in netflix_dates:
        txns.append(_make_tx(user_id, credit_account_id, nd,
                             55, "ENTERTAINMENT", "NETFLIX"))

    # Nov transactions — provide more history
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 1),
                         15000, "SALARY_AND_REVENUE", "SALARY CORP"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 5),
                         4500, "RENT_AND_SERVICES", "RENT PAYMENT"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 10),
                         450, "RENT_AND_SERVICES", "DEWA PAYMENT"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 7),
                         340, "GROCERIES", "CARREFOUR #7"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 14),
                         320, "GROCERIES", "CARREFOUR #14"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 21),
                         310, "GROCERIES", "CARREFOUR #21"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 8),
                         140, "RESTAURANTS_DINING"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 18),
                         145, "RESTAURANTS_DINING"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 20),
                         180, "ENTERTAINMENT"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 15),
                         280, "RETAIL"))
    txns.append(_make_tx(user_id, current_account_id, date(2025, 11, 2),
                         1000, "TRANSFER", "SAVINGS TRANSFER"))
    # Extra charges for more coverage
    txns.append(_make_tx(user_id, credit_account_id, date(2025, 12, 22),
                         85, "ENTERTAINMENT", "CINEMA TICKET"))
    txns.append(_make_tx(user_id, credit_account_id, date(2026, 1, 22),
                         90, "ENTERTAINMENT", "CINEMA TICKET"))
    txns.append(_make_tx(user_id, credit_account_id, date(2026, 2, 5),
                         120, "RETAIL", "AMAZON AE"))

    db_session.add_all(txns)
    await db_session.commit()
    print(f"✓ Setup complete: {len(txns)} transactions across 4 months")

    # ---------------------------------------------------------------
    #  RUN PIPELINE
    # ---------------------------------------------------------------
    print("\nRunning pipeline...")
    result = await run_health_checkup_pipeline(db_session, str(user_id), period_month=date(2026, 2, 1))

    print(f"\n{'='*40}")
    print("PIPELINE RESULT:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"{'='*40}\n")

    # ---------------------------------------------------------------
    #  ASSERTIONS
    # ---------------------------------------------------------------

    # 1. Pipeline success
    assert result["success"] is True, f"Pipeline failed: {result['error']}"

    # 2. Monthly summaries exist for each month
    ms_count = (await db_session.execute(
        select(func.count()).select_from(DerivedMonthlySummary).where(
            DerivedMonthlySummary.user_id == user_id
        )
    )).scalar()
    print(f"Monthly summaries: {ms_count}")
    assert ms_count >= 3, f"Expected ≥3 monthly summaries, got {ms_count}"

    # Check a specific month
    jan_ms = (await db_session.execute(
        select(DerivedMonthlySummary).where(
            DerivedMonthlySummary.user_id == user_id,
            DerivedMonthlySummary.period_month == date(2026, 1, 1),
        )
    )).scalar_one_or_none()
    assert jan_ms is not None, "January 2026 monthly summary missing"
    assert jan_ms.total_income > 0, f"Expected income > 0, got {jan_ms.total_income}"
    print(f"  Jan 2026: income={jan_ms.total_income}, expenses={jan_ms.total_expenses}, savings_rate={jan_ms.savings_rate}%")

    # 3. Category summaries
    cs_count = (await db_session.execute(
        select(func.count()).select_from(DerivedCategorySummary).where(
            DerivedCategorySummary.user_id == user_id
        )
    )).scalar()
    print(f"Category summaries: {cs_count}")
    assert cs_count >= 5, f"Expected ≥5 category summaries, got {cs_count}"

    # 4. Auto budgets generated
    budget_count = (await db_session.execute(
        select(func.count()).select_from(AppBudget).where(
            AppBudget.user_id == user_id,
            AppBudget.is_active == True,
        )
    )).scalar()
    print(f"Active budgets: {budget_count}")
    assert budget_count >= 1, f"Expected ≥1 budget, got {budget_count}"

    # Check SAVINGS budget
    savings_budget = (await db_session.execute(
        select(AppBudget).where(
            AppBudget.user_id == user_id,
            AppBudget.category == "SAVINGS",
            AppBudget.is_active == True,
        )
    )).scalar_one_or_none()
    assert savings_budget is not None, "SAVINGS budget not created"
    print(f"  SAVINGS budget: {savings_budget.budget_amount}")

    # 5. Budget periods
    bp_count = (await db_session.execute(
        select(func.count()).select_from(AppBudgetPeriod).where(
            AppBudgetPeriod.user_id == user_id,
        )
    )).scalar()
    print(f"Budget periods: {bp_count}")
    assert bp_count >= 1, f"Expected ≥1 budget period, got {bp_count}"

    # Check status values
    bps = (await db_session.execute(
        select(AppBudgetPeriod).where(AppBudgetPeriod.user_id == user_id)
    )).scalars().all()
    for bp in bps:
        assert bp.status in ("on_track", "warning", "over_budget"), f"Invalid status: {bp.status}"
        print(f"  Budget period: budget_amount={bp.budget_amount}, actual={bp.actual_amount}, status={bp.status}")

    # 6. Recurring transactions
    rec_count = (await db_session.execute(
        select(func.count()).select_from(DerivedRecurringTransaction).where(
            DerivedRecurringTransaction.user_id == user_id,
        )
    )).scalar()
    print(f"Recurring transactions detected: {rec_count}")
    assert rec_count >= 2, f"Expected ≥2 recurring, got {rec_count}"

    # Check Netflix → subscription
    netflix = (await db_session.execute(
        select(DerivedRecurringTransaction).where(
            DerivedRecurringTransaction.user_id == user_id,
            DerivedRecurringTransaction.merchant_name == "NETFLIX",
        )
    )).scalar_one_or_none()
    assert netflix is not None, "Netflix recurring not detected"
    assert netflix.classification == "subscription", f"Netflix should be subscription, got {netflix.classification}"
    assert netflix.recurrence_type == "monthly", f"Netflix should be monthly, got {netflix.recurrence_type}"
    print(f"  Netflix: type={netflix.recurrence_type}, class={netflix.classification}, amount={netflix.typical_amount}, confidence={netflix.confidence}")

    # Check DEWA → essential_bill
    dewa = (await db_session.execute(
        select(DerivedRecurringTransaction).where(
            DerivedRecurringTransaction.user_id == user_id,
            DerivedRecurringTransaction.merchant_name == "DEWA PAYMENT",
        )
    )).scalar_one_or_none()
    assert dewa is not None, "DEWA recurring not detected"
    assert dewa.classification == "essential_bill", f"DEWA should be essential_bill, got {dewa.classification}"
    print(f"  DEWA: type={dewa.recurrence_type}, class={dewa.classification}, amount={dewa.typical_amount}, confidence={dewa.confidence}")

    # 7. Health scores
    hs = (await db_session.execute(
        select(DerivedHealthScore).where(
            DerivedHealthScore.user_id == user_id,
            DerivedHealthScore.period_month == date(2026, 2, 1),
        )
    )).scalar_one_or_none()
    assert hs is not None, "Health score not created"
    assert 0 <= hs.composite_score <= 100, f"Invalid composite score: {hs.composite_score}"
    assert hs.composite_label in ("Excellent", "Great", "Good", "Needs Work", "Critical")
    print(f"  Composite: {hs.composite_score} ({hs.composite_label})")
    print(f"  Sub-scores: CU={hs.credit_utilization_score}, SR={hs.savings_rate_score}, BA={hs.budget_adherence_score}, BP={hs.bill_payment_score}")
    print(f"  Risk flags: CU={hs.risk_high_credit_utilization}, NCF={hs.risk_negative_cash_flow}, BD={hs.risk_bill_delinquency}, LC={hs.risk_lifestyle_creep}")

    # 8. Health score drivers — 4 components
    drivers = (await db_session.execute(
        select(DerivedHealthScoreDriver).where(
            DerivedHealthScoreDriver.health_score_id == hs.id,
        )
    )).scalars().all()
    assert len(drivers) == 4, f"Expected 4 drivers, got {len(drivers)}"
    driver_names = {d.component_name for d in drivers}
    assert driver_names == {"credit_utilization", "savings_rate", "budget_adherence", "bill_payment"}
    for d in drivers:
        print(f"  Driver: {d.component_name} = {d.current_sub_score} | {d.explanation_text}")

    print(f"\n{'='*60}")
    print("✅ ALL ASSERTIONS PASSED")
    print(f"{'='*60}\n")

    # ---------------------------------------------------------------
    #  CLEANUP
    # ---------------------------------------------------------------
    await db_session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
    await db_session.commit()
    print("✓ Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
