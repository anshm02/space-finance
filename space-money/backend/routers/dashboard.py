"""Dashboard API endpoints for Space Money.

Read-only endpoints that query pre-computed derived tables
to power the mobile dashboard/home screen.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, literal_column, text
from sqlalchemy.orm import aliased
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
import calendar

from database import get_db
from models.analytics import (
    DerivedMonthlySummary,
    AppBudget,
    AppBudgetPeriod,
    DerivedRecurringTransaction,
)
from models.accounts import UserAccount, AccountType, CreditCardDetails
from models.transactions import RawTransaction
from models.category_mappings import CategoryMapping
from models.user import UserProfile

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

async def _resolve_user_uuid(db: AsyncSession, user_id: str):
    """Resolve user_id (could be username or UUID) to DIFC UserProfile UUID."""
    import uuid as uuid_mod
    # Try as UUID first
    try:
        uid = uuid_mod.UUID(user_id)
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == uid)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile.user_id
    except ValueError:
        pass

    # Try as username
    result = await db.execute(
        select(UserProfile).where(UserProfile.username == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile.user_id

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


def _current_period() -> date:
    """Return first day of current month."""
    today = date.today()
    return today.replace(day=1)


async def _latest_transaction_period(db: AsyncSession, uid) -> date:
    """Find the latest month that has transaction data for the user.
    Falls back to current month if nothing found."""
    result = await db.execute(
        select(func.max(RawTransaction.transaction_date)).where(
            RawTransaction.user_id == uid
        )
    )
    max_date = result.scalar()
    if max_date:
        return max_date.replace(day=1)
    return _current_period()


async def _best_period(db: AsyncSession, uid) -> date:
    """Use current month if it has data, otherwise fall back to latest."""
    current = _current_period()
    # Check if current month has any transactions
    result = await db.execute(
        select(func.count()).select_from(RawTransaction).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= current,
            )
        )
    )
    count = result.scalar() or 0
    if count > 0:
        return current
    # Fall back to latest month with data
    return await _latest_transaction_period(db, uid)


def _decimal_to_float(val) -> float:
    """Convert Decimal/None to float."""
    if val is None:
        return 0.0
    return float(val)


def _format_amount(val) -> str:
    """Format a number to comma-separated string."""
    return f"{_decimal_to_float(val):,.0f}"


# ---------------------------------------------------------------------------
#  1. GET /summary/{user_id}
# ---------------------------------------------------------------------------

@router.get("/summary/{user_id}")
async def get_dashboard_summary(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns monthly summary, account balances, budget totals,
    safe-to-spend amount, and bills due count.
    """
    uid = await _resolve_user_uuid(db, user_id)
    period = await _best_period(db, uid)

    # 1) Monthly summary
    result = await db.execute(
        select(DerivedMonthlySummary).where(
            and_(
                DerivedMonthlySummary.user_id == uid,
                DerivedMonthlySummary.period_month == period,
            )
        )
    )
    summary = result.scalar_one_or_none()

    # 2) Account balances
    result = await db.execute(
        select(UserAccount).where(UserAccount.user_id == uid)
    )
    accounts_rows = result.scalars().all()

    accounts = []
    checking_balance = Decimal(0)
    credit_balance = Decimal(0)
    savings_balance = Decimal(0)

    for acct in accounts_rows:
        bal = acct.current_balance or Decimal(0)
        entry = {
            "account_id": str(acct.account_id),
            "account_name": acct.account_name,
            "account_number": getattr(acct, 'account_number', None),
            "account_type": acct.account_type.value if acct.account_type else None,
            "institution_name": acct.institution_name,
            "current_balance": _decimal_to_float(bal),
            "currency_code": acct.currency_code,
        }
        accounts.append(entry)

        if acct.account_type == AccountType.CURRENT:
            checking_balance += bal
        elif acct.account_type == AccountType.CREDIT:
            credit_balance += bal
        elif acct.account_type == AccountType.SAVINGS:
            savings_balance += bal

    net_cash = checking_balance - credit_balance

    # 3) Budget totals — sum of all active budgets
    result = await db.execute(
        select(func.sum(AppBudget.budget_amount)).where(
            and_(
                AppBudget.user_id == uid,
                AppBudget.is_active == True,
            )
        )
    )
    total_budget = result.scalar() or Decimal(0)

    # 4) Budget periods for current month → flexible budget/spend
    result = await db.execute(
        select(AppBudgetPeriod).where(
            and_(
                AppBudgetPeriod.user_id == uid,
                AppBudgetPeriod.period_month == period,
            )
        )
    )
    budget_periods = result.scalars().all()

    # Get the budget categories to know which are flexible
    budget_ids = [bp.budget_id for bp in budget_periods]
    budgets_by_id = {}
    if budget_ids:
        result = await db.execute(
            select(AppBudget).where(AppBudget.id.in_(budget_ids))
        )
        for b in result.scalars().all():
            budgets_by_id[b.id] = b

    fixed_budget = Decimal(0)
    fixed_actual = Decimal(0)
    flexible_budget = Decimal(0)
    flexible_actual = Decimal(0)
    savings_budget_amt = Decimal(0)
    savings_actual = Decimal(0)

    # We need to look up the category mapping to find the bucket
    for bp in budget_periods:
        budget = budgets_by_id.get(bp.budget_id)
        if not budget:
            continue
        cat = budget.category
        # Look up the bucket from category mappings
        result2 = await db.execute(
            select(CategoryMapping.bucket).where(
                and_(
                    CategoryMapping.lean_category == cat,
                    CategoryMapping.user_id == None,  # System defaults
                )
            ).limit(1)
        )
        bucket_row = result2.scalar_one_or_none()
        bucket = bucket_row if bucket_row else "flexible"

        bp_budget = bp.budget_amount or Decimal(0)
        bp_actual = bp.actual_amount or Decimal(0)

        if bucket == "fixed":
            fixed_budget += bp_budget
            fixed_actual += bp_actual
        elif bucket == "flexible":
            flexible_budget += bp_budget
            flexible_actual += bp_actual
        elif bucket == "savings":
            savings_budget_amt += bp_budget
            savings_actual += bp_actual

    safe_to_spend = flexible_budget - flexible_actual

    # 5) Bills due count
    result = await db.execute(
        select(func.count()).select_from(DerivedRecurringTransaction).where(
            and_(
                DerivedRecurringTransaction.user_id == uid,
                DerivedRecurringTransaction.classification == "essential_bill",
                DerivedRecurringTransaction.status == "active",
                DerivedRecurringTransaction.next_expected_date != None,
                DerivedRecurringTransaction.next_expected_date >= date.today(),
                DerivedRecurringTransaction.next_expected_date <= date.today().replace(
                    day=calendar.monthrange(date.today().year, date.today().month)[1]
                ),
            )
        )
    )
    bills_due_count = result.scalar() or 0

    # 6) Day progress — use the period month, not today's month
    today = date.today()
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    # If viewing current month, use today's day; otherwise use last day
    if period.year == today.year and period.month == today.month:
        day_of_month = today.day
    else:
        day_of_month = days_in_month  # historical month — show full month

    # If no monthly summary row exists, try to compute totals from raw transactions
    if not summary:
        # Sum income/expenses directly from raw_transactions for this period
        period_end_date = period.replace(day=days_in_month)
        tx_result = await db.execute(
            select(
                func.sum(case(
                    (RawTransaction.transaction_type == 'credit', RawTransaction.amount),
                    else_=literal_column('0')
                )).label('income'),
                func.sum(case(
                    (RawTransaction.transaction_type == 'debit', RawTransaction.amount),
                    else_=literal_column('0')
                )).label('expenses'),
            ).where(
                and_(
                    RawTransaction.user_id == uid,
                    RawTransaction.transaction_date >= period,
                    RawTransaction.transaction_date <= period_end_date,
                )
            )
        )
        tx_row = tx_result.one_or_none()
        if tx_row and (tx_row.income or tx_row.expenses):
            total_income = _decimal_to_float(tx_row.income)
            total_expenses = _decimal_to_float(tx_row.expenses)
        else:
            total_income = 0
            total_expenses = 0
        net_sav = total_income - total_expenses
        savings_rate = (net_sav / total_income * 100) if total_income > 0 else 0

        # Compute fixed/flexible from raw transactions using category mappings
        cat_map_result = await db.execute(
            select(CategoryMapping).where(CategoryMapping.user_id == None)
        )
        _cat_mappings = {m.lean_category: m.bucket for m in cat_map_result.scalars().all()}

        debit_cats_result = await db.execute(
            select(
                RawTransaction.lean_insights_category,
                func.sum(RawTransaction.amount),
            ).where(
                and_(
                    RawTransaction.user_id == uid,
                    RawTransaction.transaction_date >= period,
                    RawTransaction.transaction_date <= period_end_date,
                    RawTransaction.transaction_type == 'debit',
                )
            ).group_by(RawTransaction.lean_insights_category)
        )
        total_fixed_spent = 0.0
        total_flexible_spent = 0.0
        for cat_name, cat_sum in debit_cats_result.all():
            bucket = _cat_mappings.get(cat_name)
            amt = _decimal_to_float(cat_sum)
            if bucket == 'fixed':
                total_fixed_spent += amt
            elif bucket == 'flexible':
                total_flexible_spent += amt
            # bucket is None (TRANSFER, SALARY) → excluded

        logger.info(
            "[BUDGET] No DerivedMonthlySummary — fallback. "
            "fixed_spent=%.2f flexible_spent=%.2f (from category mappings)",
            total_fixed_spent, total_flexible_spent,
        )
    else:
        total_expenses = _decimal_to_float(summary.total_expenses)
        total_income = _decimal_to_float(summary.total_income)
        net_sav = _decimal_to_float(summary.net_savings)
        savings_rate = _decimal_to_float(summary.savings_rate)
        total_fixed_spent = _decimal_to_float(summary.total_fixed)
        total_flexible_spent = _decimal_to_float(summary.total_flexible)
        logger.info("[BUDGET] Using DerivedMonthlySummary. total_flexible=%s total_fixed=%s", total_flexible_spent, total_fixed_spent)

    # Determine if we have any real data (accounts OR transactions)
    has_data = len(accounts) > 0 or total_income > 0 or total_expenses > 0

    # ------------------------------------------------------------------
    #  BUDGET CALCULATION (5-step formula)
    # ------------------------------------------------------------------
    # Step 1: monthly_income already computed above

    # Step 2: Expected recurring bills — simple SUM of all active essential_bill + loan_payment
    recurring_result = await db.execute(
        select(DerivedRecurringTransaction).where(
            and_(
                DerivedRecurringTransaction.user_id == uid,
                DerivedRecurringTransaction.status == "active",
                DerivedRecurringTransaction.classification.in_(
                    ["essential_bill", "loan_payment"]
                ),
            )
        )
    )
    recurring_txns = recurring_result.scalars().all()

    expected_bills = 0.0
    logger.info("[FIXED BILLS] Found %d active essential_bill/loan_payment for user=%s", len(recurring_txns), user_id)
    for rt in recurring_txns:
        amount = _decimal_to_float(rt.typical_amount)
        expected_bills += amount
        logger.info(
            "[FIXED BILLS]   merchant=%s classification=%s typical_amount=%.2f recurrence=%s",
            rt.merchant_name, rt.classification, amount, rt.recurrence_type,
        )
    logger.info("[FIXED BILLS] expected_fixed_bills = %.2f (from %d bills)", expected_bills, len(recurring_txns))

    # Step 3: Savings allocation (15% of income)
    savings_allocation = total_income * 0.15 if total_income > 0 else 0

    # Step 4: Safe to spend (flexible budget)
    computed_safe_to_spend = total_income - expected_bills - savings_allocation

    # Step 5: Budget = expected_bills + safe_to_spend = income - savings_allocation
    budget = expected_bills + max(computed_safe_to_spend, 0)

    # ------------------------------------------------------------------
    #  FIXED / FLEXIBLE / SAVINGS PERCENTAGES
    # ------------------------------------------------------------------
    # Fixed circle: % of expected bills paid this month
    fixed_bills_total_count = len(recurring_txns)
    fixed_bills_paid_count = 0

    # Determine if this is a completed (past) month
    is_current_month = (period.year == today.year and period.month == today.month)
    is_completed_month = not is_current_month and period < today.replace(day=1)

    if is_completed_month:
        # Completed month — ALL bills assumed paid → 100%
        fixed_bills_paid_count = fixed_bills_total_count
    elif fixed_bills_total_count > 0 and is_current_month:
        # Current month — match merchant_name against this month's transactions
        merchant_names = [rt.merchant_name for rt in recurring_txns if rt.merchant_name]
        if merchant_names:
            period_end_date_bills = period.replace(
                day=calendar.monthrange(period.year, period.month)[1]
            )
            for mn in merchant_names:
                match_result = await db.execute(
                    select(func.count()).select_from(RawTransaction).where(
                        and_(
                            RawTransaction.user_id == uid,
                            RawTransaction.transaction_date >= period,
                            RawTransaction.transaction_date <= period_end_date_bills,
                            func.lower(RawTransaction.description_cleansed).contains(
                                mn.lower()
                            ),
                        )
                    )
                )
                if (match_result.scalar() or 0) > 0:
                    fixed_bills_paid_count += 1

    computed_fixed_pct = (
        (fixed_bills_paid_count / fixed_bills_total_count * 100)
        if fixed_bills_total_count > 0 else
        (100 if is_completed_month else 0)  # No bills detected but month is done → 100%
    )

    # Fixed circle status label: "ALL PAID" or "X LEFT" (not ON TRACK/WATCH IT/TIGHT)
    bills_remaining = fixed_bills_total_count - fixed_bills_paid_count
    if is_completed_month or bills_remaining == 0:
        fixed_status_label = "ALL PAID"
    else:
        fixed_status_label = f"{bills_remaining} LEFT"

    # Flexible circle: % of safe-to-spend used
    flexible_spent = total_flexible_spent  # from derived_monthly_summaries
    computed_flexible_pct = (
        (flexible_spent / computed_safe_to_spend * 100)
        if computed_safe_to_spend > 0 else 0
    )

    # Savings circle: overspend indicator
    if flexible_spent > computed_safe_to_spend and computed_safe_to_spend > 0:
        overspend = flexible_spent - computed_safe_to_spend
        computed_savings_pct = (
            (overspend / savings_allocation * 100) if savings_allocation > 0 else 0
        )
    else:
        computed_savings_pct = 0

    # ------------------------------------------------------------------
    #  LOG ALL COMPUTED BUDGET VALUES
    # ------------------------------------------------------------------
    logger.info(
        "[BUDGET CARD] user=%s period=%s | "
        "monthly_income=%.2f expected_fixed_bills=%.2f savings_allocation=%.2f | "
        "safe_to_spend=%.2f budget=%.2f | "
        "flexible_spent=%.2f flexible_pct=%.1f | "
        "fixed_bills_paid=%d fixed_bills_total=%d fixed_pct=%.1f | "
        "savings_pct=%.1f | total_expenses=%.2f",
        user_id, period,
        total_income, expected_bills, savings_allocation,
        computed_safe_to_spend, budget,
        flexible_spent, computed_flexible_pct,
        fixed_bills_paid_count, fixed_bills_total_count, computed_fixed_pct,
        computed_savings_pct, total_expenses,
    )

    # Status banner
    is_over_budget = total_expenses > budget
    if not is_over_budget:
        potential_savings = budget - total_expenses + savings_allocation
        status_text = f"On track to save {int(round(potential_savings)):,} AED this month"
    else:
        over_amount = total_expenses - budget
        status_text = f"Over budget by {int(round(over_amount)):,} AED"

    # Display month label (e.g., "January 2026")
    display_month = f"{calendar.month_name[period.month]} {period.year}"

    # On track savings estimate
    if day_of_month > 0:
        daily_spend_rate = total_expenses / day_of_month
        projected_expenses = daily_spend_rate * days_in_month
        projected_savings = total_income - projected_expenses
    else:
        projected_savings = 0

    return {
        "has_data": has_data,
        "period_month": period.isoformat(),
        "day_of_month": day_of_month,
        "days_in_month": days_in_month,
        "display_month": display_month,
        # Monthly totals
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_savings": net_sav,
        "savings_rate": savings_rate,
        "total_fixed_spent": total_fixed_spent,
        "total_flexible_spent": total_flexible_spent,
        "projected_savings": round(projected_savings, 0),
        # Budget (5-step calculation)
        "monthly_income": total_income,
        "expected_fixed_bills": round(expected_bills, 2),
        "expected_bills": round(expected_bills, 2),  # keep legacy alias
        "savings_allocation": round(savings_allocation, 2),
        "budget": round(budget, 2),
        "safe_to_spend": round(computed_safe_to_spend, 2),
        "is_over_budget": is_over_budget,
        "status_text": status_text,
        # Budget card circle data
        "fixed_bills_paid_count": fixed_bills_paid_count,
        "fixed_bills_total_count": fixed_bills_total_count,
        "fixed_pct": round(computed_fixed_pct, 1),
        "fixed_status_label": fixed_status_label,
        "flexible_spent": round(flexible_spent, 2),
        "flexible_pct": round(computed_flexible_pct, 1),
        "savings_pct": round(computed_savings_pct, 1),
        # Accounts
        "accounts": accounts,
        "checking_balance": _decimal_to_float(checking_balance),
        "credit_balance": _decimal_to_float(credit_balance),
        "savings_balance": _decimal_to_float(savings_balance),
        "net_cash": _decimal_to_float(net_cash),
        # Legacy budgets (from AppBudget table)
        "total_budget": _decimal_to_float(total_budget),
        "fixed_budget": _decimal_to_float(fixed_budget),
        "fixed_actual": _decimal_to_float(fixed_actual),
        "flexible_budget": _decimal_to_float(flexible_budget),
        "flexible_actual": _decimal_to_float(flexible_actual),
        "savings_budget": _decimal_to_float(savings_budget_amt),
        "savings_actual": _decimal_to_float(savings_actual),
        "bills_due_count": bills_due_count,
        # Status
        "is_on_track": not is_over_budget,
    }


# ---------------------------------------------------------------------------
#  2. GET /subscriptions/{user_id}
# ---------------------------------------------------------------------------

@router.get("/subscriptions/{user_id}")
async def get_dashboard_subscriptions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Returns active subscriptions with next_expected_date."""
    uid = await _resolve_user_uuid(db, user_id)

    result = await db.execute(
        select(DerivedRecurringTransaction).where(
            and_(
                DerivedRecurringTransaction.user_id == uid,
                DerivedRecurringTransaction.classification == "subscription",
                DerivedRecurringTransaction.status == "active",
            )
        ).order_by(DerivedRecurringTransaction.next_expected_date.asc())
    )
    subs = result.scalars().all()

    today = date.today()
    subscriptions = []
    total_monthly_cost = Decimal(0)

    for sub in subs:
        amount = sub.typical_amount or Decimal(0)
        total_monthly_cost += amount

        # Calculate days until next charge
        days_until = None
        if sub.next_expected_date:
            delta = sub.next_expected_date - today
            days_until = delta.days  # negative = overdue

        # Try to extract a domain for the logo
        merchant = sub.merchant_name or ""
        domain = _guess_domain(merchant)

        subscriptions.append({
            "id": str(sub.id),
            "merchant_name": merchant,
            "amount": _decimal_to_float(amount),
            "next_expected_date": sub.next_expected_date.isoformat() if sub.next_expected_date else None,
            "days_until_next": days_until,
            "logo_url": f"https://logo.clearbit.com/{domain}" if domain else None,
            "recurrence_type": sub.recurrence_type,
        })

    return {
        "subscriptions": subscriptions,
        "total_monthly_cost": _decimal_to_float(total_monthly_cost),
    }


def _guess_domain(merchant_name: str) -> Optional[str]:
    """Try to guess a domain for clearbit logo from merchant name."""
    known = {
        "netflix": "netflix.com",
        "spotify": "spotify.com",
        "apple": "apple.com",
        "apple one": "apple.com",
        "apple music": "apple.com",
        "adobe": "adobe.com",
        "adobe cc": "adobe.com",
        "chatgpt": "openai.com",
        "openai": "openai.com",
        "youtube": "youtube.com",
        "youtube premium": "youtube.com",
        "amazon prime": "amazon.com",
        "amazon": "amazon.com",
        "disney": "disneyplus.com",
        "disney+": "disneyplus.com",
        "hulu": "hulu.com",
        "hbo": "hbomax.com",
        "microsoft": "microsoft.com",
        "google": "google.com",
        "dropbox": "dropbox.com",
        "slack": "slack.com",
        "notion": "notion.so",
        "figma": "figma.com",
        "github": "github.com",
        "linkedin": "linkedin.com",
    }
    lower = merchant_name.lower().strip()
    for key, domain in known.items():
        if key in lower:
            return domain
    # Fallback: try merchant_name.com
    clean = lower.replace(" ", "").replace("'", "").replace("-", "")
    if clean:
        return f"{clean}.com"
    return None


# ---------------------------------------------------------------------------
#  3. GET /transactions/{user_id}?month=YYYY-MM
# ---------------------------------------------------------------------------

@router.get("/transactions/{user_id}")
async def get_dashboard_transactions(
    user_id: str,
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Returns current month transactions grouped by bucket."""
    uid = await _resolve_user_uuid(db, user_id)

    if month:
        try:
            year, mon = month.split("-")
            period_start = date(int(year), int(mon), 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    else:
        period_start = await _best_period(db, uid)

    days_in_m = calendar.monthrange(period_start.year, period_start.month)[1]
    period_end = period_start.replace(day=days_in_m)

    # Get transactions for the month (only debits/expenses)
    result = await db.execute(
        select(RawTransaction).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period_start,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == "debit",
            )
        ).order_by(RawTransaction.amount.desc())
    )
    transactions = result.scalars().all()

    # Build category → bucket mapping
    result = await db.execute(
        select(CategoryMapping).where(
            CategoryMapping.user_id == None  # System defaults
        )
    )
    mappings = result.scalars().all()
    cat_map = {}
    for m in mappings:
        cat_map[m.lean_category] = {
            "bucket": m.bucket,
            "display_name": m.display_name,
        }

    # Group by bucket
    buckets = {"fixed": [], "flexible": [], "savings": []}
    bucket_totals = {"fixed": 0.0, "flexible": 0.0, "savings": 0.0}

    for tx in transactions:
        cat = tx.lean_insights_category or "uncategorized"
        mapping = cat_map.get(cat, {"bucket": "flexible", "display_name": cat.replace("_", " ").title()})
        bucket = mapping["bucket"]

        amount = _decimal_to_float(tx.amount)
        entry = {
            "transaction_id": str(tx.transaction_id),
            "merchant_name": tx.description_cleansed or "Unknown",
            "category": mapping["display_name"],
            "lean_category": cat,
            "amount": amount,
            "date": tx.transaction_date.isoformat(),
            "currency_code": tx.currency_code,
        }

        # Skip excluded categories (bucket=None, e.g. TRANSFER, SALARY_AND_REVENUE)
        if bucket is None:
            continue
        if bucket in buckets:
            buckets[bucket].append(entry)
            bucket_totals[bucket] += amount
        else:
            buckets["flexible"].append(entry)
            bucket_totals["flexible"] += amount

    return {
        "period_month": period_start.isoformat(),
        "buckets": {
            "fixed": {
                "label": "Fixed",
                "total": round(bucket_totals["fixed"], 2),
                "transactions": buckets["fixed"],
            },
            "flexible": {
                "label": "Flexible",
                "total": round(bucket_totals["flexible"], 2),
                "transactions": buckets["flexible"],
            },
            "savings": {
                "label": "Savings",
                "total": round(bucket_totals["savings"], 2),
                "transactions": buckets["savings"],
            },
        },
    }


# ---------------------------------------------------------------------------
#  4. GET /spending-trend/{user_id}?month=YYYY-MM
# ---------------------------------------------------------------------------

@router.get("/spending-trend/{user_id}")
async def get_spending_trend(
    user_id: str,
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Returns daily cumulative spending for the line chart."""
    uid = await _resolve_user_uuid(db, user_id)

    if month:
        try:
            year, mon = month.split("-")
            period_start = date(int(year), int(mon), 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    else:
        period_start = await _best_period(db, uid)

    days_in_m = calendar.monthrange(period_start.year, period_start.month)[1]
    period_end = period_start.replace(day=days_in_m)

    # Get daily spending aggregates
    result = await db.execute(
        select(
            RawTransaction.transaction_date,
            func.sum(RawTransaction.amount),
        ).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period_start,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == "debit",
            )
        ).group_by(RawTransaction.transaction_date)
        .order_by(RawTransaction.transaction_date)
    )
    daily_rows = result.all()

    # Build cumulative daily data
    daily_map = {row[0]: _decimal_to_float(row[1]) for row in daily_rows}
    
    data_points = []
    cumulative = 0.0
    # Only go up to today if current month, else full month
    today = date.today()
    last_day = min(today.day, days_in_m) if period_start.month == today.month and period_start.year == today.year else days_in_m

    for day in range(1, last_day + 1):
        d = period_start.replace(day=day)
        daily_amount = daily_map.get(d, 0.0)
        cumulative += daily_amount
        data_points.append({
            "day": day,
            "date": d.isoformat(),
            "daily_amount": round(daily_amount, 2),
            "cumulative": round(cumulative, 2),
        })

    return {
        "period_month": period_start.isoformat(),
        "days_in_month": days_in_m,
        "data_points": data_points,
    }
