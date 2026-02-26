"""
Deadlines service — Feature 6.

Compliance Calendar + Deadline Management for Indian micro-businesses.

Covers:
  - generate_deadlines()  — auto-create next 12 months of deadlines for a client
  - get_client_deadlines() / get_upcoming_deadlines() — read APIs
  - complete_deadline() / acknowledge_deadline() — status transitions
  - send_bulk_reminders() — CA triggers bulk push
  - run_daily_reminder_job() — APScheduler daily at 9 AM IST
  - mark_missed_deadlines() — auto-mark overdue deadlines as missed

Hard-coded Indian compliance dates (Year 1 scope):
  GSTR-1 monthly      → 11th of next month  (regular scheme, >₹5Cr turnover)
  GSTR-1 quarterly    → 13th of month after quarter end  (QRMP scheme)
  GSTR-3B             → 20th of next month  (all regular filers)
  CMP-08              → 18th of month after quarter end  (composition scheme)
  Advance Tax Q1-Q4   → Jun 15, Sep 15, Dec 15, Mar 15
  FSSAI Renewal       → 30 days before expiry (food sector)
"""
import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

from core.extensions import db
from modules.auth.models import User
from modules.businesses.models import Business
from modules.deadlines.models import ComplianceDeadline
from modules.reminders.service import _send_fcm_push

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Hard-coded Indian compliance calendar
# ------------------------------------------------------------------ #

ADVANCE_TAX_DATES = [
    ("advance_tax_q1", 6, 15, "Advance Tax — Q1 (Jun 15)"),
    ("advance_tax_q2", 9, 15, "Advance Tax — Q2 (Sep 15)"),
    ("advance_tax_q3", 12, 15, "Advance Tax — Q3 (Dec 15)"),
    ("advance_tax_q4", 3, 15, "Advance Tax — Q4 (Mar 15)"),
]

QUARTER_END_MONTHS = [3, 6, 9, 12]

VALID_STATUSES = {"pending", "reminded", "acknowledged", "completed", "missed"}


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _infer_gst_scheme(biz: Business) -> Optional[str]:
    """
    Infer GST scheme from Business fields.

    Returns:
      "regular"             — monthly filer (GSTIN + turnover >₹5Cr)
      "regular_quarterly"   — QRMP scheme  (GSTIN + turnover ≤₹5Cr)
      None                  — no GSTIN, no GST filings
    """
    if not biz.gstin:
        return None
    turnover = biz.expected_turnover or 0
    if turnover > 5_00_00_000:   # ₹5 crore
        return "regular"
    return "regular_quarterly"


def _is_food_sector(biz: Business) -> bool:
    bt = (biz.business_type or "").lower()
    return any(kw in bt for kw in ("food", "restaurant", "cafe", "bakery",
                                    "dhaba", "canteen", "catering", "tiffin",
                                    "sweet", "snack", "juice"))


def _next_month(y: int, m: int):
    """Return (year, month) of the next month."""
    if m == 12:
        return y + 1, 1
    return y, m + 1


def _month_bounds(y: int, m: int):
    """Return (first_day, last_day) of the month."""
    first = date(y, m, 1)
    last = date(y, m, monthrange(y, m)[1])
    return first, last


# ------------------------------------------------------------------ #
# 1. Generate deadlines for a client (next 12 months)
# ------------------------------------------------------------------ #

def generate_deadlines(business_id: int, org_id: int) -> int:
    """
    Auto-generate the next 12 months of applicable deadlines.

    Called when:
      - A client is created / activated
      - CA manually triggers refresh

    Skips any deadline that already exists (same client + type + due_date)
    to allow safe re-generation without duplicates.

    Returns count of newly created deadlines.
    """
    biz = Business.query.get(business_id)
    if not biz:
        raise ValueError("Business not found.")

    scheme = _infer_gst_scheme(biz)
    is_food = _is_food_sector(biz)
    today = date.today()
    created_count = 0

    def _add(dtype, desc, due, period_s=None, period_e=None):
        nonlocal created_count
        # Skip duplicates
        exists = ComplianceDeadline.query.filter_by(
            client_id=business_id,
            deadline_type=dtype,
            due_date=due,
        ).first()
        if exists:
            return
        dl = ComplianceDeadline(
            client_id=business_id,
            org_id=org_id,
            deadline_type=dtype,
            description=desc,
            due_date=due,
            period_start=period_s,
            period_end=period_e,
            status="pending",
        )
        db.session.add(dl)
        created_count += 1

    # Iterate next 12 months
    for offset in range(12):
        y, m = today.year, today.month + offset
        if m > 12:
            y += m // 12 if m % 12 != 0 else (m // 12 - 1)
            m = m % 12 or 12

        period_start, period_end = _month_bounds(y, m)
        ny, nm = _next_month(y, m)

        if scheme == "regular":
            # GSTR-1 monthly — due 11th of next month
            _add(
                "gstr1_monthly",
                f"GSTR-1 Monthly Filing — {period_start:%b %Y}",
                date(ny, nm, 11),
                period_start, period_end,
            )
            # GSTR-3B — due 20th of next month
            _add(
                "gstr3b",
                f"GSTR-3B Filing — {period_start:%b %Y}",
                date(ny, nm, 20),
                period_start, period_end,
            )

        elif scheme == "regular_quarterly":
            # GSTR-3B — still monthly, due 20th of next month
            _add(
                "gstr3b",
                f"GSTR-3B Filing — {period_start:%b %Y}",
                date(ny, nm, 20),
                period_start, period_end,
            )
            # GSTR-1 quarterly — only at quarter ends (Mar, Jun, Sep, Dec)
            if m in QUARTER_END_MONTHS:
                # Quarter start is 3 months back
                qs_m = m - 2
                qs_y = y
                if qs_m <= 0:
                    qs_m += 12
                    qs_y -= 1
                q_start = date(qs_y, qs_m, 1)
                _add(
                    "gstr1_quarterly",
                    f"GSTR-1 Quarterly (QRMP) — Q ending {period_start:%b %Y}",
                    date(ny, nm, 13),
                    q_start, period_end,
                )

    # Advance Tax — fixed dates, add if within next 12 months
    for dtype, atm, atd, desc in ADVANCE_TAX_DATES:
        for year_offset in range(2):
            at_year = today.year + year_offset
            at_date = date(at_year, atm, atd)
            if today <= at_date <= today + timedelta(days=365):
                # Determine FY period
                if atm >= 4:
                    fy_start = date(at_year, 4, 1)
                    fy_end = date(at_year + 1, 3, 31)
                else:
                    fy_start = date(at_year - 1, 4, 1)
                    fy_end = date(at_year, 3, 31)
                _add(dtype, desc, at_date, fy_start, fy_end)

    # FSSAI Renewal — 30 days notice for food sector
    if is_food:
        # Create a yearly reminder, 30 days before today + 1 year
        # (placeholder — in production, would use fssai_expiry from client profile)
        fssai_due = date(today.year + 1, today.month, min(today.day, 28))
        fssai_warn = fssai_due - timedelta(days=30)
        if fssai_warn >= today:
            _add(
                "fssai_renewal",
                "FSSAI License Renewal — apply before expiry",
                fssai_warn,
                None, fssai_due,
            )

    db.session.commit()
    logger.info(
        "Generated %d deadlines for business_id=%d (scheme=%s, food=%s)",
        created_count, business_id, scheme, is_food,
    )
    return created_count


# ------------------------------------------------------------------ #
# 2. Read APIs
# ------------------------------------------------------------------ #

def get_client_deadlines(
    org_id: int,
    business_id: int,
    status_filter: Optional[str] = None,
) -> dict:
    """
    All deadlines for a client. Optionally filter by status.
    Returns {client, deadlines[], summary}.
    """
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        raise ValueError("Client not found in your organization.")

    query = ComplianceDeadline.query.filter_by(
        client_id=business_id, org_id=org_id,
    )
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)

    deadlines = query.order_by(ComplianceDeadline.due_date.asc()).all()

    # Summary counts
    pending  = sum(1 for d in deadlines if d.status == "pending")
    reminded = sum(1 for d in deadlines if d.status == "reminded")
    acked    = sum(1 for d in deadlines if d.status == "acknowledged")
    done     = sum(1 for d in deadlines if d.status == "completed")
    missed   = sum(1 for d in deadlines if d.status == "missed")

    # Overdue count (pending/reminded past due_date)
    today = date.today()
    overdue = sum(
        1 for d in deadlines
        if d.status in ("pending", "reminded") and d.due_date < today
    )

    return {
        "client": {
            "id":   biz.id,
            "name": biz.name,
            "gstin": biz.gstin,
            "business_type": biz.business_type,
        },
        "deadlines": [d.to_dict() for d in deadlines],
        "summary": {
            "total":        len(deadlines),
            "pending":      pending,
            "reminded":     reminded,
            "acknowledged": acked,
            "completed":    done,
            "missed":       missed,
            "overdue":      overdue,
        },
    }


def get_upcoming_deadlines(org_id: int, days: int = 30) -> dict:
    """
    CA view: all client deadlines in the next N days.
    Returns {deadlines[], summary, period}.
    """
    today = date.today()
    end = today + timedelta(days=days)

    deadlines = (
        ComplianceDeadline.query
        .filter(
            ComplianceDeadline.org_id == org_id,
            ComplianceDeadline.due_date >= today,
            ComplianceDeadline.due_date <= end,
            ComplianceDeadline.status.in_(["pending", "reminded", "acknowledged"]),
        )
        .order_by(ComplianceDeadline.due_date.asc())
        .all()
    )

    # Enrich with client name
    biz_ids = list({d.client_id for d in deadlines})
    biz_map = {}
    if biz_ids:
        for b in Business.query.filter(Business.id.in_(biz_ids)).all():
            biz_map[b.id] = b.name

    items = []
    for d in deadlines:
        dd = d.to_dict()
        dd["client_name"] = biz_map.get(d.client_id, "Unknown")
        items.append(dd)

    # Group by week
    this_week = [i for i in items if i["due_date"] and
                 date.fromisoformat(i["due_date"]) <= today + timedelta(days=7)]
    next_week = [i for i in items if i["due_date"] and
                 today + timedelta(days=7) < date.fromisoformat(i["due_date"])
                 <= today + timedelta(days=14)]
    later = [i for i in items if i["due_date"] and
             date.fromisoformat(i["due_date"]) > today + timedelta(days=14)]

    # Also fetch overdue
    overdue = (
        ComplianceDeadline.query
        .filter(
            ComplianceDeadline.org_id == org_id,
            ComplianceDeadline.due_date < today,
            ComplianceDeadline.status.in_(["pending", "reminded"]),
        )
        .order_by(ComplianceDeadline.due_date.asc())
        .all()
    )
    overdue_items = []
    for d in overdue:
        dd = d.to_dict()
        dd["client_name"] = biz_map.get(d.client_id) or "Unknown"
        # re-fetch name if not in map
        if dd["client_name"] == "Unknown":
            b = Business.query.get(d.client_id)
            dd["client_name"] = b.name if b else "Unknown"
        dd["days_overdue"] = (today - d.due_date).days
        overdue_items.append(dd)

    return {
        "period": {
            "from": today.isoformat(),
            "to":   end.isoformat(),
            "days": days,
        },
        "overdue":   overdue_items,
        "this_week": this_week,
        "next_week": next_week,
        "later":     later,
        "summary": {
            "total_upcoming":  len(items),
            "overdue":         len(overdue_items),
            "this_week":       len(this_week),
            "next_week":       len(next_week),
            "later":           len(later),
            "unique_clients":  len(biz_ids),
        },
    }


# ------------------------------------------------------------------ #
# 3. Status transitions
# ------------------------------------------------------------------ #

def complete_deadline(
    deadline_id: int,
    user_id: int,
    org_id: int,
    notes: Optional[str] = None,
) -> dict:
    """
    CA marks a deadline as completed (filed).

    Returns the updated deadline dict.
    """
    dl = ComplianceDeadline.query.get(deadline_id)
    if not dl:
        raise ValueError("Deadline not found.")
    if dl.org_id != org_id:
        raise PermissionError("This deadline does not belong to your organization.")
    if dl.status == "completed":
        raise ValueError("Deadline is already completed.")
    if dl.status == "missed":
        # Allow re-completion of missed deadlines (late filing)
        pass

    dl.status = "completed"
    dl.completed_at = datetime.utcnow()
    dl.completed_by = user_id
    if notes:
        dl.notes = notes
    db.session.commit()

    logger.info(
        "Deadline %d completed by user %s (type=%s, client=%d)",
        dl.id, user_id, dl.deadline_type, dl.client_id,
    )
    return dl.to_dict()


def acknowledge_deadline(
    deadline_id: int,
    user_id: int,
    business_id: Optional[int] = None,
) -> dict:
    """
    Client acknowledges a reminder ("Got it").

    business_id is used for access control (client can only ack own deadlines).
    """
    dl = ComplianceDeadline.query.get(deadline_id)
    if not dl:
        raise ValueError("Deadline not found.")

    # If client role, verify they own this business
    if business_id is not None and dl.client_id != business_id:
        raise PermissionError("This deadline does not belong to your business.")

    if dl.status in ("completed", "missed"):
        raise ValueError(f"Cannot acknowledge a {dl.status} deadline.")

    dl.status = "acknowledged"
    dl.acknowledged_at = datetime.utcnow()
    db.session.commit()

    logger.info(
        "Deadline %d acknowledged by user %s (type=%s)",
        dl.id, user_id, dl.deadline_type,
    )
    return dl.to_dict()


# ------------------------------------------------------------------ #
# 4. Bulk reminders
# ------------------------------------------------------------------ #

def send_bulk_reminders(
    org_id: int,
    client_ids,
    message: str,
    deadline_type: Optional[str] = None,
) -> dict:
    """
    CA triggers immediate reminder push to selected clients about deadlines.

    If deadline_type specified, only remind about that type.
    Otherwise sends the custom message.

    Returns {sent, failed, skipped, total, details[]}.
    """
    if not message or not message.strip():
        raise ValueError("Message cannot be empty.")

    today = date.today()

    # Resolve target businesses
    if client_ids == "all":
        businesses = (
            Business.query
            .filter_by(org_id=org_id, invite_status="active", is_active=True)
            .all()
        )
    else:
        if not isinstance(client_ids, list) or len(client_ids) == 0:
            raise ValueError("client_ids must be a non-empty list or 'all'.")
        if len(client_ids) > 500:
            raise ValueError("Cannot send to more than 500 clients at once.")
        businesses = (
            Business.query
            .filter(Business.id.in_(client_ids), Business.org_id == org_id)
            .all()
        )
        found_ids = {b.id for b in businesses}
        bad = [cid for cid in client_ids if cid not in found_ids]
        if bad:
            raise ValueError(f"Client IDs not found in your org: {bad[:5]}")

    results = []

    for biz in businesses:
        base = {"client_id": biz.id, "client_name": biz.name}

        if not biz.owner_user_id:
            results.append({**base, "status": "skipped",
                            "reason": "No user account linked (invite not accepted)"})
            continue

        user = User.query.get(biz.owner_user_id)
        if not user:
            results.append({**base, "status": "failed",
                            "reason": "User record not found"})
            continue

        if not user.fcm_token:
            results.append({**base, "status": "no_token",
                            "reason": "Device not registered for notifications"})
            continue

        # Build notification body
        if deadline_type:
            # Find next upcoming deadline of this type
            next_dl = (
                ComplianceDeadline.query
                .filter_by(client_id=biz.id, deadline_type=deadline_type)
                .filter(
                    ComplianceDeadline.due_date >= today,
                    ComplianceDeadline.status.in_(["pending", "reminded"]),
                )
                .order_by(ComplianceDeadline.due_date.asc())
                .first()
            )
            if next_dl:
                body = (
                    f"{next_dl.description or next_dl.deadline_type} is due "
                    f"{next_dl.due_date:%d %b %Y}. {message}"
                )
                # Mark as reminded
                next_dl.status = "reminded"
                next_dl.reminder_sent_at = datetime.utcnow()
            else:
                body = message
        else:
            body = message

        ok, reason = _send_fcm_push(
            user.fcm_token,
            "Compliance Reminder",
            body,
            "deadline",
        )
        results.append({
            **base,
            "status": "delivered" if ok else "failed",
            "reason": reason,
        })

    db.session.commit()

    sent    = sum(1 for r in results if r["status"] in ("delivered",))
    failed  = sum(1 for r in results if r["status"] == "failed")
    skipped = len(results) - sent - failed

    return {
        "sent":    sent,
        "failed":  failed,
        "skipped": skipped,
        "total":   len(results),
        "details": results,
    }


# ------------------------------------------------------------------ #
# 5. Scheduled jobs (APScheduler)
# ------------------------------------------------------------------ #

def mark_missed_deadlines():
    """
    Mark overdue deadlines (pending/reminded, past due_date) as 'missed'.
    Called daily by scheduler.
    """
    today = date.today()
    overdue = (
        ComplianceDeadline.query
        .filter(
            ComplianceDeadline.due_date < today,
            ComplianceDeadline.status.in_(["pending", "reminded"]),
        )
        .all()
    )
    count = 0
    for dl in overdue:
        dl.status = "missed"
        count += 1

    if count:
        db.session.commit()
        logger.info("Marked %d overdue deadlines as missed.", count)
    return count


def run_daily_reminder_job(app):
    """
    Daily at 9 AM IST — send push reminders for upcoming deadlines.

    Logic:
      - 7-day notice: all pending deadlines due in 7 days
      - 3-day urgent:  all non-completed deadlines due in 3 days
      - Mark reminded
      - Also mark missed overdue deadlines
    """
    with app.app_context():
        logger.info("Running daily deadline reminder job...")

        # 1. Mark missed first
        missed_count = mark_missed_deadlines()

        today = date.today()
        seven_day = today + timedelta(days=7)
        three_day = today + timedelta(days=3)

        # 2. Seven-day notice
        seven_day_dls = (
            ComplianceDeadline.query
            .filter(
                ComplianceDeadline.due_date == seven_day,
                ComplianceDeadline.status == "pending",
            )
            .all()
        )

        sent_7 = 0
        for dl in seven_day_dls:
            biz = Business.query.get(dl.client_id)
            if not biz or not biz.owner_user_id:
                continue
            user = User.query.get(biz.owner_user_id)
            if not user or not user.fcm_token:
                continue

            body = (
                f"Your {dl.description or dl.deadline_type} is due "
                f"{dl.due_date:%d %b %Y}. Tap to review."
            )
            ok, _ = _send_fcm_push(user.fcm_token, "Compliance Reminder", body, "deadline")
            if ok:
                dl.status = "reminded"
                dl.reminder_sent_at = datetime.utcnow()
                sent_7 += 1

        # 3. Three-day urgent
        three_day_dls = (
            ComplianceDeadline.query
            .filter(
                ComplianceDeadline.due_date == three_day,
                ComplianceDeadline.status.in_(["pending", "reminded"]),
            )
            .all()
        )

        sent_3 = 0
        for dl in three_day_dls:
            biz = Business.query.get(dl.client_id)
            if not biz or not biz.owner_user_id:
                continue
            user = User.query.get(biz.owner_user_id)
            if not user or not user.fcm_token:
                continue

            body = (
                f"URGENT: {dl.description or dl.deadline_type} due in 3 days "
                f"({dl.due_date:%d %b %Y})."
            )
            ok, _ = _send_fcm_push(user.fcm_token, "Urgent: Action Required", body, "urgent")
            if ok:
                dl.reminder_sent_at = datetime.utcnow()
                if dl.status == "pending":
                    dl.status = "reminded"
                sent_3 += 1

        db.session.commit()
        logger.info(
            "Daily reminder job done: missed=%d, 7-day=%d, 3-day=%d",
            missed_count, sent_7, sent_3,
        )
