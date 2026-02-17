"""Transactions API endpoints for Space Money.

Read-only endpoints powering the Transactions page:
- /upcoming: recurring charges and calendar data (always current month)
- /all: transactions grouped by bucket with search and date-range filtering
- /top-merchants: top 5 merchants by total spend for date range
- /largest-purchases: top 5 largest individual transactions for date range
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional
from datetime import date, timedelta
from decimal import Decimal
import logging
import calendar

from database import get_db
from models.analytics import DerivedRecurringTransaction
from models.transactions import RawTransaction
from models.category_mappings import CategoryMapping
from models.user import UserProfile

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])
logger = logging.getLogger(__name__)


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


def _parse_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
    month: Optional[str],
) -> tuple[date, date]:
    """Parse date range from start_date/end_date or month param.
    Returns (period_start, period_end).
    Falls back to current month if nothing provided.
    """
    if start_date and end_date:
        try:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
            return sd, ed
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    if month:
        try:
            year, mon = month.split("-")
            y, m = int(year), int(mon)
            dim = calendar.monthrange(y, m)[1]
            return date(y, m, 1), date(y, m, dim)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    today = date.today()
    dim = calendar.monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, dim)


async def _best_period_for_range(
    db: AsyncSession,
    uid,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    month: Optional[str] = None,
) -> tuple[date, date]:
    """If explicit range/month given, use it. Otherwise default to current month,
    falling back to the latest month with data if current month is empty."""
    if start_date and end_date:
        return _parse_date_range(start_date, end_date, None)
    if month:
        return _parse_date_range(None, None, month)

    today = date.today()
    current_start = date(today.year, today.month, 1)
    dim = calendar.monthrange(today.year, today.month)[1]
    current_end = date(today.year, today.month, dim)

    result = await db.execute(
        select(func.count()).select_from(RawTransaction).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= current_start,
                RawTransaction.transaction_date <= current_end,
            )
        )
    )
    count = result.scalar() or 0
    if count > 0:
        return current_start, current_end

    result = await db.execute(
        select(func.max(RawTransaction.transaction_date)).where(
            RawTransaction.user_id == uid
        )
    )
    max_date = result.scalar()
    if max_date:
        fb_start = max_date.replace(day=1)
        fb_dim = calendar.monthrange(fb_start.year, fb_start.month)[1]
        return fb_start, date(fb_start.year, fb_start.month, fb_dim)

    return current_start, current_end


# ---------------------------------------------------------------------------
#  1. GET /upcoming/{user_id}
# ---------------------------------------------------------------------------

@router.get("/upcoming/{user_id}")
async def get_upcoming_transactions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Upcoming recurring charges and calendar data. Always uses the current month."""
    uid = await _resolve_user_uuid(db, user_id)
    today = date.today()
    period = date(today.year, today.month, 1)
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    period_end = period.replace(day=days_in_month)

    result = await db.execute(
        select(DerivedRecurringTransaction).where(
            and_(
                DerivedRecurringTransaction.user_id == uid,
                DerivedRecurringTransaction.status == "active",
            )
        ).order_by(DerivedRecurringTransaction.next_expected_date.asc())
    )
    recurring = result.scalars().all()

    tx_dates_result = await db.execute(
        select(
            RawTransaction.transaction_date,
            func.count().label("count"),
        ).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period,
                RawTransaction.transaction_date <= period_end,
            )
        ).group_by(RawTransaction.transaction_date)
    )
    dates_with_transactions = [
        {"date": row[0].isoformat(), "day": row[0].day, "count": row[1]}
        for row in tx_dates_result.all()
    ]

    upcoming_payments = []
    total_upcoming = 0
    for rt in recurring:
        amount = _decimal_to_float(rt.typical_amount)
        cat_style = _get_category_style(rt.lean_category or "")
        days_until = None
        if rt.next_expected_date:
            delta = rt.next_expected_date - today
            days_until = delta.days

        upcoming_payments.append({
            "id": str(rt.id),
            "merchant_name": rt.merchant_name,
            "amount": round(amount, 2),
            "category": rt.lean_category or "uncategorized",
            "lean_category": rt.lean_category or "uncategorized",
            "classification": rt.classification,
            "recurrence_type": rt.recurrence_type,
            "next_expected_date": rt.next_expected_date.isoformat() if rt.next_expected_date else None,
            "typical_day_of_month": rt.typical_day_of_month,
            "days_until_due": days_until,
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })
        total_upcoming += amount

    first_day_weekday = period.weekday()
    first_day_sunday_based = (first_day_weekday + 1) % 7
    display_month = f"{calendar.month_name[period.month]} {period.year}"

    return {
        "period_month": period.isoformat(),
        "display_month": display_month,
        "month_name": calendar.month_name[period.month],
        "year": period.year,
        "days_in_month": days_in_month,
        "first_day_offset": first_day_sunday_based,
        "today_day": today.day if (period.year == today.year and period.month == today.month) else None,
        "dates_with_transactions": dates_with_transactions,
        "upcoming_payments": upcoming_payments,
        "upcoming_count": len(upcoming_payments),
        "upcoming_total": round(total_upcoming, 2),
    }


# ---------------------------------------------------------------------------
#  2. GET /all/{user_id}?start_date=&end_date=&month=&search=
# ---------------------------------------------------------------------------

@router.get("/all/{user_id}")
async def get_all_transactions(
    user_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    month: Optional[str] = Query(None, description="YYYY-MM format (deprecated, use start_date/end_date)"),
    search: Optional[str] = Query(None, description="Search by merchant or category"),
    db: AsyncSession = Depends(get_db),
):
    """All transactions grouped by bucket (All, Flexible, Fixed)
    with optional search and date-range filtering."""
    uid = await _resolve_user_uuid(db, user_id)
    period_start, period_end = await _best_period_for_range(db, uid, start_date, end_date, month)

    base_query = select(RawTransaction).where(
        and_(
            RawTransaction.user_id == uid,
            RawTransaction.transaction_date >= period_start,
            RawTransaction.transaction_date <= period_end,
            RawTransaction.transaction_type == 'debit',
        )
    )

    if search and search.strip():
        search_term = search.strip().lower()
        base_query = base_query.where(
            or_(
                func.lower(RawTransaction.description_cleansed).contains(search_term),
                func.lower(RawTransaction.lean_insights_category).contains(search_term),
            )
        )

    result = await db.execute(
        base_query.order_by(RawTransaction.transaction_date.desc(), RawTransaction.amount.desc())
    )
    transactions = result.scalars().all()

    cat_map_result = await db.execute(
        select(CategoryMapping).where(CategoryMapping.user_id == None)
    )
    cat_mappings = {}
    for m in cat_map_result.scalars().all():
        cat_mappings[m.lean_category] = {
            "bucket": m.bucket,
            "display_name": m.display_name,
        }

    all_entries = []
    for tx in transactions:
        cat = tx.lean_insights_category or "uncategorized"
        mapping = cat_mappings.get(cat, {"bucket": "flexible", "display_name": cat.replace("_", " ").title()})
        bucket = mapping["bucket"]
        if bucket is None:
            continue
        cat_style = _get_category_style(cat)
        all_entries.append({
            "transaction_id": str(tx.transaction_id),
            "merchant_name": tx.description_cleansed or "Unknown",
            "category": mapping["display_name"],
            "lean_category": cat,
            "bucket": bucket,
            "amount": _decimal_to_float(tx.amount),
            "date": tx.transaction_date.strftime("%b %d"),
            "date_iso": tx.transaction_date.isoformat(),
            "currency_code": tx.currency_code,
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })

    flexible = [e for e in all_entries if e["bucket"] == "flexible"]
    fixed = [e for e in all_entries if e["bucket"] == "fixed"]

    all_total = sum(e["amount"] for e in all_entries)
    flexible_total = sum(e["amount"] for e in flexible)
    fixed_total = sum(e["amount"] for e in fixed)

    return {
        "period_month": period_start.isoformat(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_count": len(all_entries),
        "groups": {
            "all": {
                "label": "All Transactions",
                "count": len(all_entries),
                "total": round(all_total, 2),
                "transactions": all_entries,
            },
            "flexible": {
                "label": "Flexible",
                "count": len(flexible),
                "total": round(flexible_total, 2),
                "transactions": flexible,
            },
            "fixed": {
                "label": "Fixed",
                "count": len(fixed),
                "total": round(fixed_total, 2),
                "transactions": fixed,
            },
        },
    }


# ---------------------------------------------------------------------------
#  3. GET /top-merchants/{user_id}?start_date=&end_date=&month=
# ---------------------------------------------------------------------------

@router.get("/top-merchants/{user_id}")
async def get_top_merchants(
    user_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Top 5 merchants by total spend for the date range."""
    uid = await _resolve_user_uuid(db, user_id)
    period_start, period_end = await _best_period_for_range(db, uid, start_date, end_date, month)

    result = await db.execute(
        select(
            RawTransaction.description_cleansed,
            RawTransaction.lean_insights_category,
            func.sum(RawTransaction.amount).label("total"),
            func.count().label("payments"),
        ).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period_start,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == 'debit',
                RawTransaction.description_cleansed != None,
            )
        ).group_by(
            RawTransaction.description_cleansed,
            RawTransaction.lean_insights_category,
        ).order_by(func.sum(RawTransaction.amount).desc())
        .limit(5)
    )
    rows = result.all()

    merchants = []
    for merchant_name, lean_cat, total, payments in rows:
        cat_style = _get_category_style(lean_cat or "")
        merchants.append({
            "merchant_name": merchant_name or "Unknown",
            "lean_category": lean_cat or "",
            "total_spent": round(_decimal_to_float(total), 2),
            "payments": payments,
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })

    return {
        "period_month": period_start.isoformat(),
        "merchants": merchants,
    }


# ---------------------------------------------------------------------------
#  4. GET /largest-purchases/{user_id}?start_date=&end_date=&month=
# ---------------------------------------------------------------------------

@router.get("/largest-purchases/{user_id}")
async def get_largest_purchases(
    user_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
):
    """Top 5 largest individual transactions for the date range."""
    uid = await _resolve_user_uuid(db, user_id)
    period_start, period_end = await _best_period_for_range(db, uid, start_date, end_date, month)

    cat_map_result = await db.execute(
        select(CategoryMapping).where(CategoryMapping.user_id == None)
    )
    cat_mappings = {}
    for m in cat_map_result.scalars().all():
        cat_mappings[m.lean_category] = m.display_name

    result = await db.execute(
        select(RawTransaction).where(
            and_(
                RawTransaction.user_id == uid,
                RawTransaction.transaction_date >= period_start,
                RawTransaction.transaction_date <= period_end,
                RawTransaction.transaction_type == 'debit',
            )
        ).order_by(RawTransaction.amount.desc())
        .limit(5)
    )
    transactions = result.scalars().all()

    purchases = []
    for tx in transactions:
        cat = tx.lean_insights_category or "uncategorized"
        display_name = cat_mappings.get(cat, cat.replace("_", " ").title())
        cat_style = _get_category_style(cat)
        purchases.append({
            "transaction_id": str(tx.transaction_id),
            "merchant_name": tx.description_cleansed or "Unknown",
            "category": display_name,
            "lean_category": cat,
            "amount": _decimal_to_float(tx.amount),
            "date": tx.transaction_date.strftime("%b %d"),
            "date_iso": tx.transaction_date.isoformat(),
            "color": cat_style["color"],
            "bgColor": cat_style["bgColor"],
            "icon": cat_style["icon"],
        })

    return {
        "period_month": period_start.isoformat(),
        "purchases": purchases,
    }
