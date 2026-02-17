"""Budget API endpoints for Space Money.

Read-only endpoints powering the Budget page:
- /summary: left-for-spending, fixed/flexible/savings breakdown
- /breakdown: per-category spending vs budget (donut chart)
- /largest-purchases: top 5 transactions by amount
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, literal_column
from typing import Optional
from datetime import date
from decimal import Decimal
import logging
import calendar

from database import get_db
from models.analytics import (
    DerivedMonthlySummary,
    DerivedCategorySummary,
    AppBudget,
    AppBudgetPeriod,
    DerivedRecurringTransaction,
)
from models.transactions import RawTransaction
from models.category_mappings import CategoryMapping
from models.user import UserProfile

router = APIRouter(prefix="/api/v1/budget", tags=["budget"])
logger = logging.getLogger(__name__)


async def _resolve_user_uuid(db: AsyncSession, user_id: str):
    import uuid as uuid_mod
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
    result = await db.execute(
        select(UserProfile).where(UserProfile.username == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        return profile.user_id
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def _decimal_to_float(val) -> float:
    if val is None:
        return 0.0
    return float(val)


async def _best_period(db: AsyncSession, uid, month: Optional[str] = None) -> date:
    if month:
        try:
            year, mon = month.split("-")
            return date(int(year), int(mon), 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    today = date.today()
    current = today.replace(day=1)
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
    result = await db.execute(
        select(func.max(RawTransaction.transaction_date)).where(
            RawTransaction.user_id == uid
        )
    )
    max_date = result.scalar()
    if max_date:
        return max_date.replace(day=1)
    return current


# ---------------------------------------------------------------------------
#  Category color mapping (matches Figma design tokens)
# ---------------------------------------------------------------------------
CATEGORY_COLORS = {
    "SHOPPING": {"color": "#D4A12A", "bgColor": "#FEF3C7", "icon": "shopping-bag"},
    "AUTO_AND_TRANSPORT": {"color": "#10D9A5", "bgColor": "#D1FAE5", "icon": "car"},
    "ENTERTAINMENT_AND_RECREATION": {"color": "#FFB155", "bgColor": "#FEF3C7", "icon": "sparkles"},
    "FOOD_AND_DINING": {"color": "#D4A12A", "bgColor": "#FEF3C7", "icon": "utensils"},
    "GROCERIES": {"color": "#FFB155", "bgColor": "#FEF3C7", "icon": "shopping-cart"},
    "BILLS_AND_UTILITIES": {"color": "#6366F1", "bgColor": "#E0E7FF", "icon": "zap"},
    "HEALTH_AND_WELLNESS": {"color": "#3B82F6", "bgColor": "#DBEAFE", "icon": "heart"},
    "EDUCATION": {"color": "#F59E0B", "bgColor": "#FEF3C7", "icon": "graduation-cap"},
    "PERSONAL_CARE": {"color": "#EC4899", "bgColor": "#FCE7F3", "icon": "scissors"},
    "TRAVEL": {"color": "#6366F1", "bgColor": "#E0E7FF", "icon": "plane"},
    "LOAN_PAYMENT": {"color": "#8B8D97", "bgColor": "#F9FAFB", "icon": "building"},
    "RENT": {"color": "#8B8D97", "bgColor": "#F9FAFB", "icon": "home"},
    "INSURANCE": {"color": "#0EA5E9", "bgColor": "#E0F2FE", "icon": "shield"},
    "BUSINESS_SERVICES": {"color": "#0EA5E9", "bgColor": "#E0F2FE", "icon": "briefcase"},
    "CASH_AND_CHECKS": {"color": "#10B981", "bgColor": "#D1FAE5", "icon": "banknote"},
    "FEES_AND_CHARGES": {"color": "#F56565", "bgColor": "#FED7D7", "icon": "alert-circle"},
    "GIFTS_AND_DONATIONS": {"color": "#A855F7", "bgColor": "#E9D5FF", "icon": "gift"},
    "HOME_IMPROVEMENT": {"color": "#059669", "bgColor": "#D1FAE5", "icon": "home"},
    "FINANCIAL_SERVICES": {"color": "#8B8D97", "bgColor": "#F9FAFB", "icon": "wallet"},
}

DEFAULT_COLOR = {"color": "#8B8D97", "bgColor": "#F9FAFB", "icon": "circle"}


def _get_category_style(lean_category: str) -> dict:
    return CATEGORY_COLORS.get(lean_category, DEFAULT_COLOR)


# ---------------------------------------------------------------------------
#  1. GET /summary/{user_id}?month=YYYY-MM
# ---------------------------------------------------------------------------

@router.get("/summary/{user_id}")
async def get_budget_summary(
    user_id: str,
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Budget page main summary: left-for-spending, fixed/flexible/savings
    breakdown with amounts and percentages, plus category-level data
    for the donut chart.
    """
    uid = await _resolve_user_uuid(db, user_id)
    period = await _best_period(db, uid, month)
    today = date.today()
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    period_end = period.replace(day=days_in_month)
    is_current_month = (period.year == today.year and period.month == today.month)
    is_completed_month = not is_current_month and period < today.replace(day=1)

    # Monthly summary
    result = await db.execute(
        select(DerivedMonthlySummary).where(
            and_(
                DerivedMonthlySummary.user_id == uid,
                DerivedMonthlySummary.period_month == period,
            )
        )
    )
    summary = result.scalar_one_or_none()

    # Compute income/expenses
    if summary:
        total_income = _decimal_to_float(summary.total_income)
        total_expenses = _decimal_to_float(summary.total_expenses)
        total_fixed_spent = _decimal_to_float(summary.total_fixed)
        total_flexible_spent = _decimal_to_float(summary.total_flexible)
    else:
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
                    RawTransaction.transaction_date <= period_end,
                )
            )
        )
        tx_row = tx_result.one_or_none()
        total_income = _decimal_to_float(tx_row.income) if tx_row else 0
        total_expenses = _decimal_to_float(tx_row.expenses) if tx_row else 0

        # Compute fixed/flexible from raw transactions
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
                    RawTransaction.transaction_date <= period_end,
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

    # Expected recurring bills
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
    expected_bills = sum(_decimal_to_float(rt.typical_amount) for rt in recurring_txns)

    # Budget formula
    savings_allocation = total_income * 0.15 if total_income > 0 else 0
    safe_to_spend = total_income - expected_bills - savings_allocation
    budget = expected_bills + max(safe_to_spend, 0)

    # Left for spending = safe_to_spend - flexible_spent
    left_for_spending = max(safe_to_spend - total_flexible_spent, 0)

    # Fixed bills status
    fixed_bills_total = len(recurring_txns)
    fixed_bills_paid = 0
    if is_completed_month:
        fixed_bills_paid = fixed_bills_total
    elif is_current_month and fixed_bills_total > 0:
        for rt in recurring_txns:
            if rt.merchant_name:
                match_result = await db.execute(
                    select(func.count()).select_from(RawTransaction).where(
                        and_(
                            RawTransaction.user_id == uid,
                            RawTransaction.transaction_date >= period,
                            RawTransaction.transaction_date <= period_end,
                            func.lower(RawTransaction.description_cleansed).contains(
                                rt.merchant_name.lower()
                            ),
                        )
                    )
                )
                if (match_result.scalar() or 0) > 0:
                    fixed_bills_paid += 1

    bills_remaining = fixed_bills_total - fixed_bills_paid
    fixed_status = "All Paid" if bills_remaining == 0 else f"{bills_remaining} Bill Due"

    # Flexible status
    flexible_status = "Safe to spend"

    # Savings status
    overspend = max(total_flexible_spent - safe_to_spend, 0)
    savings_remaining = max(savings_allocation - overspend, 0)
    savings_status = "Untouched" if overspend == 0 else "Dipping in"
    savings_pct = (overspend / savings_allocation * 100) if savings_allocation > 0 else 0

    # Fixed progress: fixed_spent / expected_bills
    fixed_progress = (total_fixed_spent / expected_bills * 100) if expected_bills > 0 else 0
    # Flexible progress: flexible_spent / safe_to_spend
    flexible_progress = (total_flexible_spent / safe_to_spend * 100) if safe_to_spend > 0 else 0
    # Budget usage progress
    budget_progress = (total_expenses / budget * 100) if budget > 0 else 0

    display_month = f"{calendar.month_name[period.month]} {period.year}"

    # Category breakdown for donut chart
    cat_summary_result = await db.execute(
        select(DerivedCategorySummary).where(
            and_(
                DerivedCategorySummary.user_id == uid,
                DerivedCategorySummary.period_month == period,
                DerivedCategorySummary.bucket.in_(["fixed", "flexible"]),
            )
        ).order_by(DerivedCategorySummary.total_amount.desc())
    )
    cat_summaries = cat_summary_result.scalars().all()

    # If no derived category summaries, compute from raw transactions
    categories = []
    if cat_summaries:
        for cs in cat_summaries:
            cat_style = _get_category_style(cs.lean_category)
            budget_result = await db.execute(
                select(AppBudgetPeriod.budget_amount).join(
                    AppBudget, AppBudgetPeriod.budget_id == AppBudget.id
                ).where(
                    and_(
                        AppBudgetPeriod.user_id == uid,
                        AppBudgetPeriod.period_month == period,
                        AppBudget.category == cs.lean_category,
                    )
                )
            )
            cat_budget = _decimal_to_float(budget_result.scalar_one_or_none())
            spent = _decimal_to_float(cs.total_amount)
            if spent <= 0:
                continue
            categories.append({
                "lean_category": cs.lean_category,
                "display_name": cs.display_category or cs.lean_category.replace("_", " ").title(),
                "bucket": cs.bucket,
                "spent": round(spent, 2),
                "budget": round(cat_budget, 2) if cat_budget > 0 else round(spent * 1.3, 2),
                "percentage_of_spend": 0,
                "color": cat_style["color"],
                "bgColor": cat_style["bgColor"],
                "icon": cat_style["icon"],
            })
    else:
        cat_map_result = await db.execute(
            select(CategoryMapping).where(CategoryMapping.user_id == None)
        )
        cat_mappings = {m.lean_category: m for m in cat_map_result.scalars().all()}
        debit_cats_result = await db.execute(
            select(
                RawTransaction.lean_insights_category,
                func.sum(RawTransaction.amount).label("total"),
            ).where(
                and_(
                    RawTransaction.user_id == uid,
                    RawTransaction.transaction_date >= period,
                    RawTransaction.transaction_date <= period_end,
                    RawTransaction.transaction_type == 'debit',
                )
            ).group_by(RawTransaction.lean_insights_category)
            .order_by(func.sum(RawTransaction.amount).desc())
        )
        for cat_name, cat_sum in debit_cats_result.all():
            mapping = cat_mappings.get(cat_name)
            if not mapping or mapping.bucket is None or mapping.exclude_from_expenses:
                continue
            spent = _decimal_to_float(cat_sum)
            if spent <= 0:
                continue
            cat_style = _get_category_style(cat_name)
            categories.append({
                "lean_category": cat_name,
                "display_name": mapping.display_name if mapping else cat_name.replace("_", " ").title(),
                "bucket": mapping.bucket if mapping else "flexible",
                "spent": round(spent, 2),
                "budget": round(spent * 1.3, 2),
                "percentage_of_spend": 0,
                "color": cat_style["color"],
                "bgColor": cat_style["bgColor"],
                "icon": cat_style["icon"],
            })

    # Compute percentage_of_spend for each category
    total_cat_spend = sum(c["spent"] for c in categories)
    for c in categories:
        c["percentage_of_spend"] = round(
            (c["spent"] / total_cat_spend * 100) if total_cat_spend > 0 else 0, 1
        )

    return {
        "period_month": period.isoformat(),
        "display_month": display_month,
        "month_name": calendar.month_name[period.month],
        # Left for spending
        "left_for_spending": round(left_for_spending, 2),
        "budget": round(budget, 2),
        "total_expenses": round(total_expenses, 2),
        "budget_progress": round(min(budget_progress, 100), 1),
        # Fixed breakdown
        "fixed": {
            "label": "Fixed",
            "status": fixed_status,
            "spent": round(total_fixed_spent, 2),
            "budget": round(expected_bills, 2),
            "subtitle": f"of {int(expected_bills):,} spent",
            "progress": round(min(fixed_progress, 100), 1),
        },
        # Flexible breakdown
        "flexible": {
            "label": "Flexible",
            "status": flexible_status,
            "spent": round(total_flexible_spent, 2),
            "budget": round(max(safe_to_spend, 0), 2),
            "remaining": round(left_for_spending, 2),
            "subtitle": f"of {int(max(safe_to_spend, 0)):,} left",
            "progress": round(min(flexible_progress, 100), 1),
        },
        # Savings breakdown
        "savings": {
            "label": "Savings",
            "status": savings_status,
            "spent": round(overspend, 2),
            "budget": round(savings_allocation, 2),
            "remaining": round(savings_remaining, 2),
            "subtitle": f"of {int(savings_allocation):,} left",
            "progress": round(min(savings_pct, 100), 1),
        },
        # Safe to spend
        "safe_to_spend": round(max(safe_to_spend, 0), 2),
        "monthly_income": round(total_income, 2),
        "expected_bills": round(expected_bills, 2),
        "savings_allocation": round(savings_allocation, 2),
        # Donut chart categories
        "categories": categories,
        "total_category_spend": round(total_cat_spend, 2),
    }


# ---------------------------------------------------------------------------
#  2. GET /breakdown/{user_id}?month=YYYY-MM
# ---------------------------------------------------------------------------

@router.get("/breakdown/{user_id}")
async def get_budget_breakdown(
    user_id: str,
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Per-category spending with budget, percentage, and remaining."""
    uid = await _resolve_user_uuid(db, user_id)
    period = await _best_period(db, uid, month)
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    period_end = period.replace(day=days_in_month)

    # Get category mappings
    cat_map_result = await db.execute(
        select(CategoryMapping).where(CategoryMapping.user_id == None)
    )
    cat_mappings = {m.lean_category: m for m in cat_map_result.scalars().all()}

    # Get spending per category
    debit_cats = await db.execute(
        select(
            RawTransaction.lean_insights_category,
            func.sum(RawTransaction.amount).label("total"),
            func.count().label("count"),
        ).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == 'debit',
            )
        ).group_by(RawTransaction.lean_insights_category)
        .order_by(func.sum(RawTransaction.amount).desc())
    )

    # Get budget periods for amounts
    bp_result = await db.execute(
        select(AppBudgetPeriod, AppBudget.category).join(
            AppBudget, AppBudgetPeriod.budget_id == AppBudget.id
        ).where(
            and_(
                AppBudgetPeriod.user_id == uid,
                AppBudgetPeriod.period_month == period,
            )
        )
    )
    budget_by_category = {}
    for bp, cat in bp_result.all():
        budget_by_category[cat] = _decimal_to_float(bp.budget_amount)

    breakdown = []
    for cat_name, total, count in debit_cats.all():
        mapping = cat_mappings.get(cat_name)
        if not mapping or mapping.bucket is None or mapping.exclude_from_expenses:
            continue
        spent = _decimal_to_float(total)
        if spent <= 0:
            continue
        cat_budget = budget_by_category.get(cat_name, spent * 1.3)
        remaining = max(cat_budget - spent, 0)
        pct = (spent / cat_budget * 100) if cat_budget > 0 else 0
        cat_style = _get_category_style(cat_name)
        breakdown.append({
            "lean_category": cat_name,
            "display_name": mapping.display_name if mapping else cat_name.replace("_", " ").title(),
            "bucket": mapping.bucket if mapping else "flexible",
            "spent": round(spent, 2),
            "budget": round(cat_budget, 2),
            "remaining": round(remaining, 2),
            "percentage": round(min(pct, 100), 1),
            "transaction_count": count,
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })

    return {
        "period_month": period.isoformat(),
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
#  3. GET /largest-purchases/{user_id}?month=YYYY-MM
# ---------------------------------------------------------------------------

@router.get("/largest-purchases/{user_id}")
async def get_largest_purchases(
    user_id: str,
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Top 5 largest individual transactions for the month."""
    uid = await _resolve_user_uuid(db, user_id)
    period = await _best_period(db, uid, month)
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    period_end = period.replace(day=days_in_month)

    cat_map_result = await db.execute(
        select(CategoryMapping).where(CategoryMapping.user_id == None)
    )
    cat_mappings = {m.lean_category: m for m in cat_map_result.scalars().all()}

    result = await db.execute(
        select(RawTransaction).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == 'debit',
            )
        ).order_by(RawTransaction.amount.desc()).limit(5)
    )
    txns = result.scalars().all()

    purchases = []
    for tx in txns:
        cat = tx.lean_insights_category or "uncategorized"
        mapping = cat_mappings.get(cat)
        cat_style = _get_category_style(cat)
        purchases.append({
            "transaction_id": str(tx.transaction_id),
            "merchant_name": tx.description_cleansed or "Unknown",
            "category": mapping.display_name if mapping else cat.replace("_", " ").title(),
            "lean_category": cat,
            "amount": _decimal_to_float(tx.amount),
            "date": tx.transaction_date.strftime("%B %d"),
            "date_iso": tx.transaction_date.isoformat(),
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })

    return {
        "period_month": period.isoformat(),
        "purchases": purchases,
    }
