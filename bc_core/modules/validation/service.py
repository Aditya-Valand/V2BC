"""
Validation + Anomaly Detection service — Feature 7.

Server-side validation rules run on every transaction creation.
Returns warnings (not errors) — client can override and submit anyway.

Rules:
  1. amount_range       — amount must be > 0 and < 1 crore (₹1,00,00,000)
  2. outlier_detection  — amount > 5x rolling 30-day average for same type
  3. duplicate_detection— same amount+type on same day (broader than 5-min check)
  4. future_date        — transaction_date cannot be in the future
  5. gap_detection      — batch job: alerts CA if client has >3 days gap

Gap detection runs as a daily batch job (APScheduler).
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func

from core.extensions import db
from modules.businesses.models import Business
from modules.compliance.models import ComplianceAlert
from modules.statements.models import BusinessStatement

logger = logging.getLogger(__name__)

MAX_AMOUNT = 1_00_00_000  # ₹1 crore


# ------------------------------------------------------------------ #
# Per-transaction validation (called during create)
# ------------------------------------------------------------------ #

def validate_transaction(
    business_id: int,
    amount: float,
    tx_type: str,
    transaction_date: Optional[date] = None,
) -> list[dict]:
    """
    Run all validation rules against a proposed transaction.

    Returns a list of warning dicts:
      [{"rule": "amount_range", "message": "...", "severity": "high"}, ...]

    Empty list = no warnings.
    """
    warnings = []
    today = date.today()
    tx_date = transaction_date or today

    # ── Rule 1: Amount range ──────────────────────────────── #
    if amount <= 0:
        warnings.append({
            "rule": "amount_range",
            "message": "Amount must be greater than zero.",
            "severity": "high",
        })
    elif amount >= MAX_AMOUNT:
        warnings.append({
            "rule": "amount_range",
            "message": f"Amount {_fmt(amount)} seems unusually high (over 1 crore). Please confirm.",
            "severity": "high",
        })

    # ── Rule 2: Future date ───────────────────────────────── #
    if tx_date > today:
        warnings.append({
            "rule": "future_date",
            "message": "Transaction date cannot be in the future.",
            "severity": "high",
        })

    # ── Rule 3: Outlier detection ─────────────────────────── #
    if amount > 0:
        outlier_warn = _check_outlier(business_id, amount, tx_type)
        if outlier_warn:
            warnings.append(outlier_warn)

    # ── Rule 4: Duplicate detection (same-day) ────────────── #
    if amount > 0:
        dup_warn = _check_duplicate(business_id, amount, tx_type, tx_date)
        if dup_warn:
            warnings.append(dup_warn)

    return warnings


def _fmt(amount: float) -> str:
    """Format amount as Indian currency string."""
    return f"\u20b9{amount:,.0f}"


def _check_outlier(business_id: int, amount: float, tx_type: str) -> Optional[dict]:
    """
    Outlier = amount > 5x the rolling 30-day average for same type.
    Returns warning dict or None.
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    avg_result = (
        db.session.query(func.avg(BusinessStatement.amount))
        .filter(
            BusinessStatement.business_id == business_id,
            BusinessStatement.statement_type == tx_type,
            BusinessStatement.transaction_date >= thirty_days_ago,
            BusinessStatement.amount > 0,
        )
        .scalar()
    )

    if avg_result is None or avg_result == 0:
        return None  # Not enough history

    avg_amount = float(avg_result)
    if amount > avg_amount * 5:
        return {
            "rule": "outlier_detection",
            "message": (
                f"This {tx_type} of {_fmt(amount)} is much higher than your "
                f"usual average ({_fmt(avg_amount)}). Please confirm."
            ),
            "severity": "medium",
            "details": {
                "entered_amount": amount,
                "avg_30_day": round(avg_amount, 2),
                "ratio": round(amount / avg_amount, 1),
            },
        }
    return None


def _check_duplicate(
    business_id: int, amount: float, tx_type: str, tx_date: date,
) -> Optional[dict]:
    """
    Duplicate = same amount + type on the same calendar day.
    Returns warning dict or None.
    """
    dup = (
        BusinessStatement.query
        .filter(
            BusinessStatement.business_id == business_id,
            BusinessStatement.statement_type == tx_type,
            BusinessStatement.amount == amount,
            func.date(BusinessStatement.transaction_date) == tx_date,
        )
        .first()
    )
    if dup:
        return {
            "rule": "duplicate_detection",
            "message": (
                f"You already entered {_fmt(amount)} {tx_type} on "
                f"{tx_date:%d %b %Y}. Add another?"
            ),
            "severity": "low",
            "details": {
                "existing_id": dup.id,
                "existing_date": dup.created_at.isoformat() if dup.created_at else None,
            },
        }
    return None


# ------------------------------------------------------------------ #
# Gap detection — batch job (runs daily via APScheduler)
# ------------------------------------------------------------------ #

def run_gap_detection(app=None):
    """
    Daily batch job: detect clients with >3 consecutive days gap
    in transaction entries.

    Creates a ComplianceAlert (DATA_QUALITY, MEDIUM severity) for each
    gap detected.

    Call with app for APScheduler context, or None if already in app context.
    """
    def _run():
        today = date.today()
        three_days_ago = today - timedelta(days=3)

        # Find all active businesses
        active_businesses = (
            Business.query
            .filter_by(is_active=True, invite_status="active")
            .all()
        )

        alerts_created = 0

        for biz in active_businesses:
            # Find the last transaction date
            last_tx = (
                db.session.query(func.max(BusinessStatement.transaction_date))
                .filter(BusinessStatement.business_id == biz.id)
                .scalar()
            )

            if last_tx is None:
                # No transactions at all — skip (they might be new)
                continue

            # Normalize to date
            if isinstance(last_tx, datetime):
                last_tx_date = last_tx.date()
            elif isinstance(last_tx, date):
                last_tx_date = last_tx
            else:
                continue

            gap_days = (today - last_tx_date).days

            if gap_days <= 3:
                continue

            # Check if we already created an alert for this gap recently
            existing_alert = (
                ComplianceAlert.query
                .filter(
                    ComplianceAlert.business_id == biz.id,
                    ComplianceAlert.alert_type == "DATA_QUALITY",
                    ComplianceAlert.rule_that_triggered == "gap_detection",
                    ComplianceAlert.created_at >= datetime.combine(
                        today - timedelta(days=1), datetime.min.time()
                    ),
                )
                .first()
            )
            if existing_alert:
                continue  # Already alerted today

            alert = ComplianceAlert(
                business_id=biz.id,
                alert_type="DATA_QUALITY",
                severity="MEDIUM",
                reason=(
                    f"No transaction entries for {gap_days} days "
                    f"(last entry: {last_tx_date:%d %b %Y}). "
                    f"Client may need a reminder."
                ),
                rule_that_triggered="gap_detection",
                status="OPEN",
            )
            db.session.add(alert)
            alerts_created += 1

        if alerts_created:
            db.session.commit()

        logger.info(
            "Gap detection: checked %d businesses, created %d alerts.",
            len(active_businesses), alerts_created,
        )
        return alerts_created

    if app:
        with app.app_context():
            return _run()
    else:
        return _run()


# ------------------------------------------------------------------ #
# Anomaly summary for a client (used by CA dashboard)
# ------------------------------------------------------------------ #

def get_anomaly_summary(business_id: int) -> dict:
    """
    Returns anomaly/validation summary for a client.

    Includes:
      - recent_warnings: last 10 transactions with anomaly flags
      - gap_days: days since last transaction entry
      - outlier_count: transactions flagged as outliers in last 30 days
      - duplicate_count: same-day duplicate entries in last 30 days
    """
    today = date.today()
    thirty_ago = datetime.combine(today - timedelta(days=30), datetime.min.time())

    # Last transaction date
    last_tx = (
        db.session.query(func.max(BusinessStatement.transaction_date))
        .filter(BusinessStatement.business_id == business_id)
        .scalar()
    )
    if last_tx:
        if isinstance(last_tx, datetime):
            gap_days = (today - last_tx.date()).days
        else:
            gap_days = (today - last_tx).days
    else:
        gap_days = None

    # Recent transactions for outlier check
    recent_stmts = (
        BusinessStatement.query
        .filter(
            BusinessStatement.business_id == business_id,
            BusinessStatement.transaction_date >= thirty_ago,
        )
        .order_by(BusinessStatement.transaction_date.desc())
        .all()
    )

    # Compute 30-day averages per type
    avg_by_type = {}
    for tx_type in ("sale", "expense"):
        avg = (
            db.session.query(func.avg(BusinessStatement.amount))
            .filter(
                BusinessStatement.business_id == business_id,
                BusinessStatement.statement_type == tx_type,
                BusinessStatement.transaction_date >= thirty_ago,
                BusinessStatement.amount > 0,
            )
            .scalar()
        )
        avg_by_type[tx_type] = float(avg) if avg else 0

    # Flag outliers and duplicates
    outlier_count = 0
    duplicate_count = 0
    flagged_transactions = []

    seen_day_type_amount = set()

    for s in recent_stmts:
        flags = []
        amt = s.amount or 0
        avg = avg_by_type.get(s.statement_type, 0)

        # Outlier check
        if avg > 0 and amt > avg * 5:
            flags.append("outlier")
            outlier_count += 1

        # Duplicate check (same day + type + amount)
        tx_d = s.transaction_date.date() if isinstance(s.transaction_date, datetime) else s.transaction_date
        key = (tx_d, s.statement_type, amt)
        if key in seen_day_type_amount:
            flags.append("duplicate")
            duplicate_count += 1
        seen_day_type_amount.add(key)

        if flags:
            flagged_transactions.append({
                "id": s.id,
                "type": s.statement_type,
                "amount": amt,
                "transaction_date": tx_d.isoformat() if tx_d else None,
                "flags": flags,
            })

    return {
        "business_id": business_id,
        "gap_days": gap_days,
        "gap_status": (
            "ok" if gap_days is not None and gap_days <= 3
            else "warning" if gap_days is not None and gap_days <= 7
            else "critical" if gap_days is not None
            else "no_data"
        ),
        "outlier_count_30d": outlier_count,
        "duplicate_count_30d": duplicate_count,
        "flagged_transactions": flagged_transactions[:20],
        "averages": {k: round(v, 2) for k, v in avg_by_type.items()},
    }
