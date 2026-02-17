"""
Analytics models for Space Money.

Contains derived tables for financial insights:
- DerivedMonthlySummary: monthly income/expense/savings totals
- DerivedCategorySummary: per-category spending stats with rolling averages
- AppBudget: user budgets (auto-generated or manual)
- AppBudgetPeriod: monthly budget vs actual tracking
- DerivedRecurringTransaction: detected recurring charges
- DerivedHealthScore: composite financial health score
- DerivedHealthScoreDriver: per-component health score breakdown
"""
from sqlalchemy import (
    Column, Date, DECIMAL, Integer, SmallInteger, DateTime, ForeignKey,
    UniqueConstraint, Index, CheckConstraint, Boolean, String, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import text
from database import Base
import uuid


class DerivedMonthlySummary(Base):
    """
    Derived monthly financial summaries for users.
    Computed from raw_transactions and app_category_mappings.
    """
    __tablename__ = "derived_monthly_summaries"
    __table_args__ = (
        UniqueConstraint('user_id', 'period_month', name='uq_monthly_summary_user_period'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    period_month = Column(Date, nullable=False)  # First day of the month

    # Financial totals
    total_income = Column(DECIMAL(12, 2), nullable=False, server_default="0")
    total_expenses = Column(DECIMAL(12, 2), nullable=False, server_default="0")
    net_savings = Column(DECIMAL(12, 2), nullable=False, server_default="0")
    savings_rate = Column(DECIMAL(9, 2), nullable=True)  # Nullable if income is 0

    # Budget bucket totals
    total_fixed = Column(DECIMAL(12, 2), nullable=False, server_default="0")
    total_flexible = Column(DECIMAL(12, 2), nullable=False, server_default="0")
    total_savings_allocated = Column(DECIMAL(12, 2), nullable=False, server_default="0")

    # Budget bucket percentages (of income)
    fixed_pct = Column(DECIMAL(9, 2), nullable=True)
    flexible_pct = Column(DECIMAL(9, 2), nullable=True)
    savings_pct = Column(DECIMAL(9, 2), nullable=True)

    # Transaction counts
    transaction_count = Column(Integer, nullable=False, server_default="0")
    income_transaction_count = Column(Integer, nullable=False, server_default="0")
    expense_transaction_count = Column(Integer, nullable=False, server_default="0")

    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DerivedCategorySummary(Base):
    """
    Per-category spending summaries with rolling averages and MoM change.
    """
    __tablename__ = "derived_category_summaries"
    __table_args__ = (
        UniqueConstraint('user_id', 'period_month', 'lean_category',
                         name='uq_category_summary_user_period_cat'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    period_month = Column(Date, nullable=False)
    lean_category = Column(String(50), nullable=False)
    display_category = Column(String(50))
    bucket = Column(String(20))

    # Spending stats
    total_amount = Column(DECIMAL(12, 2), server_default="0")
    transaction_count = Column(Integer, server_default="0")
    avg_transaction = Column(DECIMAL(10, 2))
    max_transaction = Column(DECIMAL(10, 2))
    min_transaction = Column(DECIMAL(10, 2))

    # Month-over-month
    prev_month_amount = Column(DECIMAL(12, 2))
    pct_change_mom = Column(DECIMAL(9, 2))

    # Rolling averages
    rolling_3m_avg = Column(DECIMAL(12, 2))
    rolling_6m_avg = Column(DECIMAL(12, 2))

    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AppBudget(Base):
    """
    User budgets — auto-generated from income/spending or manually set.
    """
    __tablename__ = "app_budgets"
    __table_args__ = (
        CheckConstraint("budget_amount > 0", name="ck_budget_amount_positive"),
        Index('uq_active_user_category', 'user_id', 'category',
              unique=True, postgresql_where=text("is_active = true")),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    category = Column(String(50), nullable=False)
    display_name = Column(String(100))
    budget_amount = Column(DECIMAL(10, 2), nullable=False)
    is_auto_generated = Column(Boolean, server_default="true")
    is_active = Column(Boolean, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AppBudgetPeriod(Base):
    """
    Monthly budget vs actual tracking for each budget.
    """
    __tablename__ = "app_budget_periods"
    __table_args__ = (
        UniqueConstraint('budget_id', 'period_month', name='uq_budget_period'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    budget_id = Column(UUID(as_uuid=True), ForeignKey("public.app_budgets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    period_month = Column(Date, nullable=False)
    budget_amount = Column(DECIMAL(10, 2))
    actual_amount = Column(DECIMAL(10, 2), server_default="0")
    remaining = Column(DECIMAL(10, 2))
    utilization_pct = Column(DECIMAL(9, 2), server_default="0")
    daily_pace_remaining = Column(DECIMAL(10, 2))
    days_remaining = Column(SmallInteger)
    status = Column(String(20))  # on_track / warning / over_budget
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DerivedRecurringTransaction(Base):
    """
    Detected recurring charges (subscriptions, bills, loan payments).
    """
    __tablename__ = "derived_recurring_transactions"
    __table_args__ = (
        UniqueConstraint('user_id', 'merchant_name', 'recurrence_type',
                         name='uq_recurring_user_merchant_type'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    merchant_name = Column(String(255), nullable=False)
    lean_category = Column(String(50))
    recurrence_type = Column(String(20))  # weekly/biweekly/monthly/quarterly/annual
    typical_amount = Column(DECIMAL(10, 2))
    amount_variance = Column(DECIMAL(10, 2), server_default="0")
    typical_day_of_month = Column(SmallInteger)
    status = Column(String(20), server_default="active")
    classification = Column(String(20), server_default="unclassified")  # essential_bill/subscription/loan_payment/unclassified
    last_charge_date = Column(Date)
    next_expected_date = Column(Date)
    times_detected = Column(Integer, server_default="1")
    times_paid_on_time = Column(Integer, server_default="0")
    times_paid_late = Column(Integer, server_default="0")
    times_missed = Column(Integer, server_default="0")
    user_marked_keep = Column(Boolean, nullable=True)
    first_detected_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    confidence = Column(DECIMAL(3, 2))


class DerivedHealthScore(Base):
    """
    Composite financial health score with sub-components and risk flags.
    """
    __tablename__ = "derived_health_scores"
    __table_args__ = (
        UniqueConstraint('user_id', 'period_month', name='uq_health_score_user_period'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())
    period_month = Column(Date, nullable=False)

    # Composite
    composite_score = Column(SmallInteger)
    composite_label = Column(String(20))

    # Sub-scores
    credit_utilization_score = Column(SmallInteger)
    savings_rate_score = Column(SmallInteger)
    budget_adherence_score = Column(SmallInteger)
    bill_payment_score = Column(SmallInteger)

    # Raw percentages
    credit_utilization_pct = Column(DECIMAL(9, 2))
    savings_rate_pct = Column(DECIMAL(9, 2))
    budget_adherence_pct = Column(DECIMAL(9, 2))
    bills_on_time_pct = Column(DECIMAL(9, 2))

    # Comparison to prior month
    prev_composite_score = Column(SmallInteger)
    score_delta = Column(SmallInteger)
    primary_change_driver = Column(String(50))

    # Risk flags
    risk_high_credit_utilization = Column(Boolean, server_default="false")
    risk_negative_cash_flow = Column(Boolean, server_default="false")
    risk_bill_delinquency = Column(Boolean, server_default="false")
    risk_lifestyle_creep = Column(Boolean, server_default="false")

    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DerivedHealthScoreDriver(Base):
    """
    Per-component breakdown explaining health score changes.
    """
    __tablename__ = "derived_health_score_drivers"
    __table_args__ = (
        Index('idx_drivers_health_score_id', 'health_score_id'),
        {"schema": "public"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    health_score_id = Column(UUID(as_uuid=True), ForeignKey("public.derived_health_scores.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=False)
    component_name = Column(String(50), nullable=False)
    current_sub_score = Column(SmallInteger)
    previous_sub_score = Column(SmallInteger, nullable=True)
    score_delta = Column(SmallInteger)
    weighted_impact = Column(DECIMAL(9, 2))
    explanation_text = Column(Text)
    explanation_context = Column(JSONB)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
