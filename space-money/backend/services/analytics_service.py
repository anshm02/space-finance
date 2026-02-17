"""
Analytics service for computing derived financial insights.

Contains all computation functions for the analytics pipeline:
- compute_monthly_summaries: monthly income/expense/savings totals
- compute_category_summaries: per-category spending with rolling averages
- generate_auto_budgets: auto-create budgets from income/spending data
- compute_budget_periods: monthly budget vs actual tracking
- detect_recurring_transactions: find subscriptions & recurring bills
- compute_health_score: composite financial health score
- run_health_checkup_pipeline: orchestrator for all steps
- on_transaction_sync: hook for post-Lean-sync trigger
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict, Counter
from decimal import Decimal
from statistics import median, stdev
import math
import logging

from sqlalchemy import select, func, and_, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.transactions import RawTransaction
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
from models.accounts import UserAccount, CreditCardDetails, AccountType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _month_start(d: date) -> date:
    """Return the first day of the month for a given date."""
    return date(d.year, d.month, 1)


def _prev_month(d: date) -> date:
    """Return the first day of the previous month."""
    return _month_start(d - relativedelta(months=1))


def _get_effective_mappings(mappings, user_id: str) -> dict:
    """Build effective mapping dict: lean_category -> mapping row."""
    system = {m.lean_category: m for m in mappings if m.user_id is None}
    user = {m.lean_category: m for m in mappings if m.user_id is not None and str(m.user_id) == str(user_id)}
    effective = system.copy()
    effective.update(user)
    return effective


# ===========================================================================
#  1. compute_monthly_summaries  (existing, preserved)
# ===========================================================================

async def compute_monthly_summaries(
    session: AsyncSession,
    user_id: str,
    period_month: Optional[date] = None
) -> None:
    """
    Compute and upsert monthly summaries for a user.
    """
    # Fetch category mappings
    stmt = select(CategoryMapping).where(
        (CategoryMapping.user_id == user_id) | (CategoryMapping.user_id.is_(None))
    )
    result = await session.execute(stmt)
    mappings = result.scalars().all()
    effective_mappings = _get_effective_mappings(mappings, user_id)

    # Query transactions
    query = select(RawTransaction).where(RawTransaction.user_id == user_id)
    if period_month:
        query = query.where(func.date_trunc('month', RawTransaction.transaction_date) == period_month)

    result = await session.execute(query)
    transactions = result.scalars().all()

    class MonthStats:
        def __init__(self):
            self.total_income = Decimal(0)
            self.total_expenses = Decimal(0)
            self.total_fixed = Decimal(0)
            self.total_flexible = Decimal(0)
            self.total_savings_allocated = Decimal(0)
            self.transaction_count = 0
            self.income_transaction_count = 0
            self.expense_transaction_count = 0

    stats_by_month = defaultdict(MonthStats)

    for tx in transactions:
        month_start = _month_start(tx.transaction_date)
        stats = stats_by_month[month_start]
        stats.transaction_count += 1

        cat_key = tx.lean_insights_category
        mapping = effective_mappings.get(cat_key)

        if mapping:
            if mapping.is_income:
                stats.total_income += tx.amount
                stats.income_transaction_count += 1
                continue
            if mapping.exclude_from_expenses:
                continue
            stats.total_expenses += tx.amount
            stats.expense_transaction_count += 1
            if mapping.bucket == 'fixed':
                stats.total_fixed += tx.amount
            elif mapping.bucket == 'flexible':
                stats.total_flexible += tx.amount
            elif mapping.bucket == 'savings':
                stats.total_savings_allocated += tx.amount

    for month_date, stats in stats_by_month.items():
        income = stats.total_income
        expenses = stats.total_expenses
        net_savings = income - expenses
        savings_rate = (net_savings / income * 100) if income > 0 else None
        fixed_pct = (stats.total_fixed / income * 100) if income > 0 else None
        flexible_pct = (stats.total_flexible / income * 100) if income > 0 else None
        savings_pct = (stats.total_savings_allocated / income * 100) if income > 0 else None

        summary_data = {
            "user_id": user_id,
            "period_month": month_date,
            "total_income": income,
            "total_expenses": expenses,
            "net_savings": net_savings,
            "savings_rate": savings_rate,
            "total_fixed": stats.total_fixed,
            "total_flexible": stats.total_flexible,
            "total_savings_allocated": stats.total_savings_allocated,
            "fixed_pct": fixed_pct,
            "flexible_pct": flexible_pct,
            "savings_pct": savings_pct,
            "transaction_count": stats.transaction_count,
            "income_transaction_count": stats.income_transaction_count,
            "expense_transaction_count": stats.expense_transaction_count,
        }

        stmt = insert(DerivedMonthlySummary).values(summary_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'period_month'],
            set_={k: stmt.excluded[k] for k in summary_data if k not in ('user_id', 'period_month')}
        )
        await session.execute(stmt)

    await session.flush()


# ===========================================================================
#  2. compute_category_summaries
# ===========================================================================

async def compute_category_summaries(
    session: AsyncSession,
    user_id: str,
    period_month: Optional[date] = None
) -> None:
    """Aggregate raw_transactions by category per month, compute stats & rolling avgs, upsert."""

    # Fetch mappings
    stmt = select(CategoryMapping).where(
        (CategoryMapping.user_id == user_id) | (CategoryMapping.user_id.is_(None))
    )
    result = await session.execute(stmt)
    mappings = result.scalars().all()
    effective = _get_effective_mappings(mappings, user_id)

    # Get income/transfer categories to exclude
    exclude_cats = {cat for cat, m in effective.items() if m.is_income or m.exclude_from_expenses}

    # Query transactions
    query = select(RawTransaction).where(RawTransaction.user_id == user_id)
    if period_month:
        query = query.where(func.date_trunc('month', RawTransaction.transaction_date) == period_month)
    result = await session.execute(query)
    transactions = result.scalars().all()

    # Group by (month, lean_category)
    CatStats = lambda: {"amounts": [], "count": 0}
    grouped: Dict[tuple, dict] = defaultdict(CatStats)

    for tx in transactions:
        cat = tx.lean_insights_category
        if not cat or cat in exclude_cats:
            continue
        key = (_month_start(tx.transaction_date), cat)
        grouped[key]["amounts"].append(tx.amount)
        grouped[key]["count"] += 1

    # Upsert each group
    for (month_dt, lean_cat), stats in grouped.items():
        amounts = [float(a) for a in stats["amounts"]]
        total = sum(amounts)
        count = stats["count"]
        avg_tx = total / count if count else 0
        max_tx = max(amounts) if amounts else 0
        min_tx = min(amounts) if amounts else 0

        mapping = effective.get(lean_cat)
        display_cat = mapping.display_name if mapping else lean_cat
        bucket = mapping.bucket if mapping else None

        # Prev month amount (look up from DB)
        prev = _prev_month(month_dt)
        prev_stmt = select(DerivedCategorySummary).where(
            DerivedCategorySummary.user_id == user_id,
            DerivedCategorySummary.period_month == prev,
            DerivedCategorySummary.lean_category == lean_cat,
        )
        prev_row = (await session.execute(prev_stmt)).scalar_one_or_none()
        prev_amount = float(prev_row.total_amount) if prev_row and prev_row.total_amount else None
        pct_change = None
        if prev_amount and prev_amount != 0:
            pct_change = round((total - prev_amount) / prev_amount * 100, 2)

        # Rolling averages from prior months in DB
        async def _rolling_avg(n_months: int) -> Optional[float]:
            start_month = month_dt - relativedelta(months=n_months)
            r = await session.execute(
                select(func.avg(DerivedCategorySummary.total_amount)).where(
                    DerivedCategorySummary.user_id == user_id,
                    DerivedCategorySummary.lean_category == lean_cat,
                    DerivedCategorySummary.period_month >= start_month,
                    DerivedCategorySummary.period_month < month_dt,
                )
            )
            val = r.scalar()
            return float(val) if val is not None else None

        rolling_3 = await _rolling_avg(3)
        rolling_6 = await _rolling_avg(6)

        row_data = {
            "user_id": user_id,
            "period_month": month_dt,
            "lean_category": lean_cat,
            "display_category": display_cat,
            "bucket": bucket,
            "total_amount": Decimal(str(round(total, 2))),
            "transaction_count": count,
            "avg_transaction": Decimal(str(round(avg_tx, 2))),
            "max_transaction": Decimal(str(round(max_tx, 2))),
            "min_transaction": Decimal(str(round(min_tx, 2))),
            "prev_month_amount": Decimal(str(round(prev_amount, 2))) if prev_amount is not None else None,
            "pct_change_mom": Decimal(str(pct_change)) if pct_change is not None else None,
            "rolling_3m_avg": Decimal(str(round(rolling_3, 2))) if rolling_3 is not None else None,
            "rolling_6m_avg": Decimal(str(round(rolling_6, 2))) if rolling_6 is not None else None,
        }

        stmt = insert(DerivedCategorySummary).values(row_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'period_month', 'lean_category'],
            set_={k: stmt.excluded[k] for k in row_data if k not in ('user_id', 'period_month', 'lean_category')}
        )
        await session.execute(stmt)

    await session.flush()


# ===========================================================================
#  3. generate_auto_budgets
# ===========================================================================

async def generate_auto_budgets(
    session: AsyncSession,
    user_id: str,
    period_month: date,
) -> int:
    """
    Auto-generate budgets from income/spending data.
    Returns count of budgets created/updated.
    """
    period_month = _month_start(period_month)
    count = 0

    # Read monthly summary
    ms_stmt = select(DerivedMonthlySummary).where(
        DerivedMonthlySummary.user_id == user_id,
        DerivedMonthlySummary.period_month == period_month,
    )
    ms = (await session.execute(ms_stmt)).scalar_one_or_none()

    total_income = Decimal(0)
    total_fixed = Decimal(0)

    if ms and ms.total_income > 0:
        total_income = ms.total_income
        total_fixed = ms.total_fixed
    else:
        # Fallback: average of last 6 months total_expenses
        six_ago = period_month - relativedelta(months=6)
        avg_r = await session.execute(
            select(func.avg(DerivedMonthlySummary.total_expenses)).where(
                DerivedMonthlySummary.user_id == user_id,
                DerivedMonthlySummary.period_month >= six_ago,
                DerivedMonthlySummary.period_month < period_month,
            )
        )
        avg_exp = avg_r.scalar()
        if avg_exp:
            total_income = Decimal(str(avg_exp))

    if total_income <= 0:
        return 0

    # --- SAVINGS budget ---
    savings_stmt = select(AppBudget).where(
        AppBudget.user_id == user_id,
        AppBudget.category == 'SAVINGS',
        AppBudget.is_active == True,
    )
    existing_savings = (await session.execute(savings_stmt)).scalar_one_or_none()
    if existing_savings:
        savings_amount = existing_savings.budget_amount
    else:
        savings_amount = total_income * Decimal('0.15')
        savings_data = {
            "user_id": user_id,
            "category": "SAVINGS",
            "display_name": "Monthly Savings Target",
            "budget_amount": savings_amount,
            "is_auto_generated": True,
            "is_active": True,
        }
        stmt = insert(AppBudget).values(savings_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'category'],
            index_where=AppBudget.is_active == True,
            set_={"budget_amount": stmt.excluded.budget_amount, "display_name": stmt.excluded.display_name},
        )
        await session.execute(stmt)
        count += 1

    # --- Flexible category budgets ---
    flexible_budget = total_income - total_fixed - savings_amount
    if flexible_budget <= 0:
        flexible_budget = Decimal(0)

    # Get flexible categories with rolling_6m_avg
    cat_stmt = select(DerivedCategorySummary).where(
        DerivedCategorySummary.user_id == user_id,
        DerivedCategorySummary.period_month == period_month,
        DerivedCategorySummary.bucket == 'flexible',
    )
    cats = (await session.execute(cat_stmt)).scalars().all()

    total_rolling = Decimal(0)
    for c in cats:
        val = c.rolling_6m_avg or c.total_amount or Decimal(0)
        total_rolling += val

    for c in cats:
        val = c.rolling_6m_avg or c.total_amount or Decimal(0)
        proportion = (val / total_rolling) if total_rolling > 0 else Decimal(1) / Decimal(max(len(cats), 1))
        cat_budget = flexible_budget * proportion
        if cat_budget <= 0:
            continue

        # Get display name from mappings
        mapping_stmt = select(CategoryMapping).where(
            CategoryMapping.lean_category == c.lean_category,
            (CategoryMapping.user_id == user_id) | (CategoryMapping.user_id.is_(None))
        ).order_by(CategoryMapping.user_id.desc().nulls_last()).limit(1)
        mapping_row = (await session.execute(mapping_stmt)).scalar_one_or_none()
        display = mapping_row.display_name if mapping_row else c.lean_category

        budget_data = {
            "user_id": user_id,
            "category": c.lean_category,
            "display_name": display,
            "budget_amount": cat_budget,
            "is_auto_generated": True,
            "is_active": True,
        }

        # Only upsert auto-generated budgets
        # First check if there's a manual budget for this category
        manual_check = select(AppBudget).where(
            AppBudget.user_id == user_id,
            AppBudget.category == c.lean_category,
            AppBudget.is_active == True,
            AppBudget.is_auto_generated == False,
        )
        manual = (await session.execute(manual_check)).scalar_one_or_none()
        if manual:
            continue  # Never overwrite manual budgets

        stmt = insert(AppBudget).values(budget_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'category'],
            index_where=AppBudget.is_active == True,
            set_={"budget_amount": stmt.excluded.budget_amount, "display_name": stmt.excluded.display_name},
        )
        await session.execute(stmt)
        count += 1

    await session.flush()
    return count


# ===========================================================================
#  4. compute_budget_periods
# ===========================================================================

async def compute_budget_periods(
    session: AsyncSession,
    user_id: str,
    period_month: date,
) -> None:
    """Compute budget vs actual for each active budget."""
    period_month = _month_start(period_month)
    today = date.today()

    # Next month start for days remaining
    next_month = period_month + relativedelta(months=1)
    if today < period_month:
        days_rem = (next_month - period_month).days
    elif today >= next_month:
        days_rem = 0
    else:
        days_rem = (next_month - today).days

    # Fetch all active budgets
    budgets_stmt = select(AppBudget).where(
        AppBudget.user_id == user_id,
        AppBudget.is_active == True,
    )
    budgets = (await session.execute(budgets_stmt)).scalars().all()

    for b in budgets:
        # Get actual amount
        if b.category == 'SAVINGS':
            # Use total_savings_allocated from monthly summary
            ms_stmt = select(DerivedMonthlySummary.total_savings_allocated).where(
                DerivedMonthlySummary.user_id == user_id,
                DerivedMonthlySummary.period_month == period_month,
            )
            actual_val = (await session.execute(ms_stmt)).scalar() or Decimal(0)
        else:
            # Pull from category summaries
            cs_stmt = select(DerivedCategorySummary.total_amount).where(
                DerivedCategorySummary.user_id == user_id,
                DerivedCategorySummary.period_month == period_month,
                DerivedCategorySummary.lean_category == b.category,
            )
            actual_val = (await session.execute(cs_stmt)).scalar() or Decimal(0)

        budget_amt = b.budget_amount
        remaining = budget_amt - actual_val
        util_pct = (actual_val / budget_amt * 100) if budget_amt > 0 else Decimal(0)
        daily_pace = (remaining / Decimal(max(days_rem, 1)))

        if util_pct > 100:
            status = "over_budget"
        elif util_pct >= 80:
            status = "warning"
        else:
            status = "on_track"

        period_data = {
            "budget_id": b.id,
            "user_id": user_id,
            "period_month": period_month,
            "budget_amount": budget_amt,
            "actual_amount": actual_val,
            "remaining": remaining,
            "utilization_pct": util_pct,
            "daily_pace_remaining": daily_pace,
            "days_remaining": days_rem,
            "status": status,
        }

        stmt = insert(AppBudgetPeriod).values(period_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['budget_id', 'period_month'],
            set_={k: stmt.excluded[k] for k in period_data if k not in ('budget_id', 'period_month')}
        )
        await session.execute(stmt)

    await session.flush()


# ===========================================================================
#  5. detect_recurring_transactions
# ===========================================================================

def _classify_interval(med_interval: float) -> Optional[str]:
    """Classify median interval between charges into recurrence type."""
    if 5 <= med_interval <= 9:
        return "weekly"
    elif 12 <= med_interval <= 16:
        return "biweekly"
    elif 26 <= med_interval <= 35:
        return "monthly"
    elif 85 <= med_interval <= 100:
        return "quarterly"
    elif 350 <= med_interval <= 380:
        return "annual"
    return None


def _confidence_by_count(n: int) -> Decimal:
    """Map transaction count to confidence score."""
    if n >= 5:
        return Decimal("0.95")
    elif n == 4:
        return Decimal("0.85")
    elif n == 3:
        return Decimal("0.70")
    elif n == 2:
        return Decimal("0.50")
    return Decimal("0.00")


def _auto_classify(lean_category: Optional[str], typical_amount: float) -> str:
    """Auto-classify recurring transaction type."""
    if lean_category in ("RENT_AND_SERVICES", "GOVERNMENT"):
        return "essential_bill"
    if lean_category == "ENTERTAINMENT" and typical_amount < 100:
        return "subscription"
    if lean_category == "LOANS_AND_INVESTMENTS":
        return "loan_payment"
    return "unclassified"


async def detect_recurring_transactions(
    session: AsyncSession,
    user_id: str,
) -> int:
    """Detect recurring transactions from transaction history. Returns count detected."""
    result = await session.execute(
        select(RawTransaction).where(
            RawTransaction.user_id == user_id,
            RawTransaction.description_cleansed.isnot(None),
        ).order_by(RawTransaction.description_cleansed, RawTransaction.transaction_date)
    )
    transactions = result.scalars().all()

    # Group by description_cleansed
    by_merchant: Dict[str, List] = defaultdict(list)
    for tx in transactions:
        key = tx.description_cleansed.strip()
        if key:
            by_merchant[key].append(tx)

    detected = 0

    for merchant, txns in by_merchant.items():
        if len(txns) < 2:
            continue

        # Sort by date
        txns.sort(key=lambda t: t.transaction_date)

        # Calculate intervals between consecutive charges
        intervals = []
        for i in range(1, len(txns)):
            delta = (txns[i].transaction_date - txns[i-1].transaction_date).days
            intervals.append(delta)

        if not intervals:
            continue

        med_interval = median(intervals)
        recurrence = _classify_interval(med_interval)
        if not recurrence:
            continue

        amounts = [float(t.amount) for t in txns]
        typ_amount = median(amounts)
        amt_var = stdev(amounts) if len(amounts) >= 2 else 0.0

        # typical_day_of_month = mode of days
        days = [t.transaction_date.day for t in txns]
        day_mode = Counter(days).most_common(1)[0][0]

        conf = _confidence_by_count(len(txns))
        last_date = txns[-1].transaction_date
        lean_cat = txns[-1].lean_insights_category

        # next_expected_date
        interval_map = {
            "weekly": timedelta(days=7),
            "biweekly": timedelta(days=14),
            "monthly": relativedelta(months=1),
            "quarterly": relativedelta(months=3),
            "annual": relativedelta(years=1),
        }
        next_date = last_date + interval_map[recurrence]

        classification = _auto_classify(lean_cat, typ_amount)

        # Payment tracking
        on_time = 0
        late = 0
        missed = 0
        if recurrence == "monthly":
            for i, tx in enumerate(txns):
                expected_day = day_mode
                diff = abs(tx.transaction_date.day - expected_day)
                if diff <= 3:
                    on_time += 1
                elif diff <= 10:
                    late += 1
                else:
                    missed += 1

        row_data = {
            "user_id": user_id,
            "merchant_name": merchant,
            "lean_category": lean_cat,
            "recurrence_type": recurrence,
            "typical_amount": Decimal(str(round(typ_amount, 2))),
            "amount_variance": Decimal(str(round(amt_var, 2))),
            "typical_day_of_month": day_mode,
            "status": "active",
            "classification": classification,
            "last_charge_date": last_date,
            "next_expected_date": next_date,
            "times_detected": len(txns),
            "times_paid_on_time": on_time,
            "times_paid_late": late,
            "times_missed": missed,
            "confidence": conf,
        }

        stmt = insert(DerivedRecurringTransaction).values(row_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'merchant_name', 'recurrence_type'],
            set_={k: stmt.excluded[k] for k in row_data if k not in ('user_id', 'merchant_name', 'recurrence_type')}
        )
        await session.execute(stmt)
        detected += 1

    await session.flush()
    return detected


# ===========================================================================
#  6. compute_health_score
# ===========================================================================

async def compute_health_score(
    session: AsyncSession,
    user_id: str,
    period_month: date,
) -> None:
    """Compute composite financial health score and driver rows."""
    period_month = _month_start(period_month)

    # --- Credit Utilization ---
    cu_stmt = (
        select(
            func.sum(UserAccount.current_balance).label("total_balance"),
            func.sum(CreditCardDetails.credit_limit).label("total_limit"),
        )
        .join(CreditCardDetails, CreditCardDetails.account_id == UserAccount.account_id)
        .where(
            UserAccount.user_id == user_id,
            UserAccount.account_type == AccountType.CREDIT,
        )
    )
    cu_result = (await session.execute(cu_stmt)).first()
    total_cc_balance = float(cu_result.total_balance or 0) if cu_result else 0
    total_cc_limit = float(cu_result.total_limit or 0) if cu_result else 0
    credit_util_pct = (total_cc_balance / total_cc_limit * 100) if total_cc_limit > 0 else 0

    if credit_util_pct <= 10:
        cu_score = 100
    elif credit_util_pct <= 20:
        cu_score = 90
    elif credit_util_pct <= 30:
        cu_score = 75
    elif credit_util_pct <= 50:
        cu_score = 50
    elif credit_util_pct <= 75:
        cu_score = 25
    else:
        cu_score = 0

    risk_high_cu = credit_util_pct > 50

    # --- Savings Rate ---
    ms_stmt = select(DerivedMonthlySummary).where(
        DerivedMonthlySummary.user_id == user_id,
        DerivedMonthlySummary.period_month == period_month,
    )
    ms = (await session.execute(ms_stmt)).scalar_one_or_none()
    savings_rate = float(ms.savings_rate) if ms and ms.savings_rate is not None else 0

    if savings_rate >= 30:
        sr_score = 100
    elif savings_rate >= 25:
        sr_score = 90
    elif savings_rate >= 20:
        sr_score = 80
    elif savings_rate >= 15:
        sr_score = 65
    elif savings_rate >= 10:
        sr_score = 50
    elif savings_rate >= 5:
        sr_score = 35
    elif savings_rate >= 0:
        sr_score = 20
    else:
        sr_score = 0

    risk_neg_cf = savings_rate < 0

    # --- Budget Adherence ---
    bp_stmt = select(AppBudgetPeriod).join(
        AppBudget, AppBudget.id == AppBudgetPeriod.budget_id
    ).where(
        AppBudgetPeriod.user_id == user_id,
        AppBudgetPeriod.period_month == period_month,
        AppBudget.category != 'SAVINGS',
    )
    bps = (await session.execute(bp_stmt)).scalars().all()

    if bps:
        bp_scores = []
        over_budget_cats = []
        for bp in bps:
            util = float(bp.utilization_pct or 0)
            if util <= 100:
                bp_scores.append(100)
            elif util <= 110:
                bp_scores.append(70)
            elif util <= 125:
                bp_scores.append(40)
            else:
                bp_scores.append(0)
                over_budget_cats.append(bp)
        ba_score = int(sum(bp_scores) / len(bp_scores))
        budget_adherence_pct = sum(float(bp.utilization_pct or 0) for bp in bps) / len(bps)
    else:
        ba_score = 50
        budget_adherence_pct = 0
        over_budget_cats = []

    # --- Bill Payment ---
    rec_stmt = select(DerivedRecurringTransaction).where(
        DerivedRecurringTransaction.user_id == user_id,
        DerivedRecurringTransaction.status == 'active',
    )
    recs = (await session.execute(rec_stmt)).scalars().all()

    risk_delinquency = False
    if recs:
        total_on = sum(r.times_paid_on_time or 0 for r in recs)
        total_late = sum(r.times_paid_late or 0 for r in recs)
        total_missed = sum(r.times_missed or 0 for r in recs)
        total_pays = total_on + total_late + total_missed
        on_time_pct = (total_on / total_pays * 100) if total_pays > 0 else 100

        if on_time_pct >= 100:
            bill_score = 100
        elif on_time_pct >= 95:
            bill_score = 90
        elif on_time_pct >= 85:
            bill_score = 70
        elif on_time_pct >= 70:
            bill_score = 45
        else:
            bill_score = 20

        # Risk flag: bill due in 7 days and CURRENT balance < typical_amount
        today = date.today()
        for r in recs:
            if r.next_expected_date and (r.next_expected_date - today).days <= 7:
                # Check current account balance
                bal_stmt = select(func.sum(UserAccount.current_balance)).where(
                    UserAccount.user_id == user_id,
                    UserAccount.account_type == AccountType.CURRENT,
                )
                bal = (await session.execute(bal_stmt)).scalar() or Decimal(0)
                if r.typical_amount and bal < r.typical_amount:
                    risk_delinquency = True
                    break
    else:
        bill_score = 80
        on_time_pct = 100

    # --- Composite ---
    composite = int(round(cu_score * 0.25 + sr_score * 0.25 + ba_score * 0.25 + bill_score * 0.25))
    composite = max(0, min(100, composite))

    if composite >= 90:
        label = "Excellent"
    elif composite >= 75:
        label = "Great"
    elif composite >= 60:
        label = "Good"
    elif composite >= 40:
        label = "Needs Work"
    else:
        label = "Critical"

    # --- Lifestyle Creep ---
    risk_lifestyle = False
    six_ago = period_month - relativedelta(months=6)
    ms_hist_stmt = select(DerivedMonthlySummary).where(
        DerivedMonthlySummary.user_id == user_id,
        DerivedMonthlySummary.period_month >= six_ago,
        DerivedMonthlySummary.period_month <= period_month,
    ).order_by(DerivedMonthlySummary.period_month)
    ms_hist = (await session.execute(ms_hist_stmt)).scalars().all()
    if len(ms_hist) >= 2:
        first_exp = float(ms_hist[0].total_expenses or 0)
        last_exp = float(ms_hist[-1].total_expenses or 0)
        first_inc = float(ms_hist[0].total_income or 0)
        last_inc = float(ms_hist[-1].total_income or 0)
        if first_exp > 0:
            exp_growth = (last_exp - first_exp) / first_exp
            inc_growth = (last_inc - first_inc) / first_inc if first_inc > 0 else 0
            if exp_growth > 0.10 and exp_growth > inc_growth:
                risk_lifestyle = True

    # --- Prior month comparison ---
    prev = _prev_month(period_month)
    prev_hs_stmt = select(DerivedHealthScore).where(
        DerivedHealthScore.user_id == user_id,
        DerivedHealthScore.period_month == prev,
    )
    prev_hs = (await session.execute(prev_hs_stmt)).scalar_one_or_none()
    prev_composite = prev_hs.composite_score if prev_hs else None
    score_delta = (composite - prev_composite) if prev_composite is not None else None

    # Upsert health score
    hs_data = {
        "user_id": user_id,
        "period_month": period_month,
        "composite_score": composite,
        "composite_label": label,
        "credit_utilization_score": cu_score,
        "savings_rate_score": sr_score,
        "budget_adherence_score": ba_score,
        "bill_payment_score": bill_score,
        "credit_utilization_pct": Decimal(str(round(credit_util_pct, 2))),
        "savings_rate_pct": Decimal(str(round(savings_rate, 2))),
        "budget_adherence_pct": Decimal(str(round(budget_adherence_pct, 2))),
        "bills_on_time_pct": Decimal(str(round(on_time_pct, 2))),
        "prev_composite_score": prev_composite,
        "score_delta": score_delta,
        "risk_high_credit_utilization": risk_high_cu,
        "risk_negative_cash_flow": risk_neg_cf,
        "risk_bill_delinquency": risk_delinquency,
        "risk_lifestyle_creep": risk_lifestyle,
    }

    stmt = insert(DerivedHealthScore).values(hs_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['user_id', 'period_month'],
        set_={k: stmt.excluded[k] for k in hs_data if k not in ('user_id', 'period_month')}
    )
    await session.execute(stmt)
    await session.flush()

    # Fetch the health score id for drivers
    hs_row = (await session.execute(
        select(DerivedHealthScore).where(
            DerivedHealthScore.user_id == user_id,
            DerivedHealthScore.period_month == period_month,
        )
    )).scalar_one()

    # --- Drivers ---
    # Delete existing drivers for this health score (then re-insert)
    await session.execute(
        delete(DerivedHealthScoreDriver).where(
            DerivedHealthScoreDriver.health_score_id == hs_row.id
        )
    )

    prev_scores = {}
    if prev_hs:
        prev_scores = {
            "credit_utilization": prev_hs.credit_utilization_score,
            "savings_rate": prev_hs.savings_rate_score,
            "budget_adherence": prev_hs.budget_adherence_score,
            "bill_payment": prev_hs.bill_payment_score,
        }

    components = {
        "credit_utilization": {
            "current": cu_score,
            "explanation": f"Credit utilization at {credit_util_pct:.1f}%"
                           + (f" of {total_cc_limit:.0f} limit" if total_cc_limit else ""),
        },
        "savings_rate": {
            "current": sr_score,
            "explanation": f"Savings rate at {savings_rate:.1f}%",
        },
        "budget_adherence": {
            "current": ba_score,
            "explanation": (
                f"{len(over_budget_cats)} budget(s) over limit"
                if over_budget_cats
                else "All budgets on track"
            ) if bps else "No budgets set",
        },
        "bill_payment": {
            "current": bill_score,
            "explanation": f"{on_time_pct:.0f}% bills paid on time"
                           + (f" ({len(recs)} recurring tracked)" if recs else ""),
        },
    }

    max_impact_name = None
    max_impact_val = 0

    for comp_name, info in components.items():
        prev_sub = prev_scores.get(comp_name)
        delta = (info["current"] - prev_sub) if prev_sub is not None else None
        weighted = (delta * 0.25) if delta is not None else None
        if weighted is not None and abs(weighted) > max_impact_val:
            max_impact_val = abs(weighted)
            max_impact_name = comp_name

        driver = DerivedHealthScoreDriver(
            health_score_id=hs_row.id,
            user_id=user_id,
            component_name=comp_name,
            current_sub_score=info["current"],
            previous_sub_score=prev_sub,
            score_delta=delta,
            weighted_impact=Decimal(str(round(weighted, 2))) if weighted is not None else None,
            explanation_text=info["explanation"],
            explanation_context={"raw_pct": comp_name},
        )
        session.add(driver)

    # Update primary_change_driver on health score
    if max_impact_name:
        hs_row.primary_change_driver = max_impact_name
        hs_data["primary_change_driver"] = max_impact_name

    await session.flush()


# ===========================================================================
#  7. Orchestrator
# ===========================================================================

async def run_health_checkup_pipeline(
    session: AsyncSession,
    user_id: str,
    period_month: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Run the full analytics pipeline:
      1) compute_monthly_summaries
      2) compute_category_summaries
      3) generate_auto_budgets
      4) compute_budget_periods
      5) detect_recurring_transactions
      6) compute_health_score

    Returns result dict.
    """
    if period_month is None:
        period_month = _month_start(date.today())
    else:
        period_month = _month_start(period_month)

    result: Dict[str, Any] = {
        "user_id": str(user_id),
        "period_month": str(period_month),
        "success": False,
        "error": None,
        "composite_score": None,
        "composite_label": None,
        "sub_scores": {},
        "risk_flags": {},
        "budgets_generated": 0,
        "recurring_detected": 0,
    }

    try:
        # 1. Monthly summaries (all months)
        await compute_monthly_summaries(session, user_id, period_month=None)

        # 2. Category summaries (all months)
        await compute_category_summaries(session, user_id, period_month=None)

        # 3. Auto budgets
        budgets_count = await generate_auto_budgets(session, user_id, period_month)
        result["budgets_generated"] = budgets_count

        # 4. Budget periods
        await compute_budget_periods(session, user_id, period_month)

        # 5. Recurring transactions
        recurring_count = await detect_recurring_transactions(session, user_id)
        result["recurring_detected"] = recurring_count

        # 6. Health score
        await compute_health_score(session, user_id, period_month)

        # Read back health score for result
        hs = (await session.execute(
            select(DerivedHealthScore).where(
                DerivedHealthScore.user_id == user_id,
                DerivedHealthScore.period_month == period_month,
            )
        )).scalar_one_or_none()

        if hs:
            result["composite_score"] = hs.composite_score
            result["composite_label"] = hs.composite_label
            result["sub_scores"] = {
                "credit_utilization": hs.credit_utilization_score,
                "savings_rate": hs.savings_rate_score,
                "budget_adherence": hs.budget_adherence_score,
                "bill_payment": hs.bill_payment_score,
            }
            result["risk_flags"] = {
                "high_credit_utilization": hs.risk_high_credit_utilization,
                "negative_cash_flow": hs.risk_negative_cash_flow,
                "bill_delinquency": hs.risk_bill_delinquency,
                "lifestyle_creep": hs.risk_lifestyle_creep,
            }

        await session.commit()
        result["success"] = True

    except Exception as e:
        logger.error(f"Pipeline failed for user {user_id}: {e}", exc_info=True)
        await session.rollback()
        result["error"] = str(e)

    return result


# ===========================================================================
#  8. Post-sync hook
# ===========================================================================

async def on_transaction_sync(
    session: AsyncSession,
    user_id: str,
) -> Dict[str, Any]:
    """
    Called after a successful Lean sync to refresh all derived analytics.
    Runs the full pipeline for the current month.
    """
    return await run_health_checkup_pipeline(session, user_id, period_month=None)
