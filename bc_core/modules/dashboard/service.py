"""
Dashboard service — Feature 5.

Provides all business logic for:
  - GET /dashboard          org-level overview
  - GET /clients/:id/detail full client detail
  - GET /clients/:id/filing-summary   monthly aggregation
  - filing-summary Excel export

No SQL in routes; all queries here.
"""
import io
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, extract

from core.extensions import db
from modules.auth.models import User
from modules.businesses.models import Business
from modules.compliance.models import ComplianceAlert, ComplianceProfile
from modules.evidence.models import BusinessEvidence
from modules.organizations.models import Organization
from modules.statements.models import BusinessStatement

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Shared helpers
# ------------------------------------------------------------------ #

def _days_since(dt) -> Optional[int]:
    """Return days between dt and today.  None if dt is None."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        dt = dt.date()
    elif not isinstance(dt, date):
        return None
    return max(0, (date.today() - dt).days)


def _compliance_color(days_since: Optional[int]) -> str:
    """
    Red   — no entry in 5+ days (or never)
    Yellow — no entry in 3-4 days
    Green  — entry in last 2 days
    """
    if days_since is None or days_since >= 5:
        return "red"
    if days_since >= 3:
        return "yellow"
    return "green"


def _alert_dict(a: ComplianceAlert) -> dict:
    return {
        "id":         a.id,
        "alert_type": a.alert_type.value if hasattr(a.alert_type, "value") else str(a.alert_type),
        "severity":   a.severity.value   if hasattr(a.severity,   "value") else str(a.severity),
        "title":      a.reason[:100],
        "created_at": a.created_at.isoformat(),
    }


def _ev_for_stmts(stmt_ids: list) -> dict:
    """Returns {statement_id: BusinessEvidence} for given stmt ids."""
    if not stmt_ids:
        return {}
    evs = BusinessEvidence.query.filter(
        BusinessEvidence.statement_id.in_(stmt_ids)
    ).all()
    return {ev.statement_id: ev for ev in evs}


# ------------------------------------------------------------------ #
# 1. Dashboard (org-level overview)
# ------------------------------------------------------------------ #

def get_dashboard(org_id: int) -> dict:
    """
    Returns:
      org_name, stats (totals + colors), client list sorted by urgency,
      recent alerts.
    """
    org = Organization.query.get(org_id)
    if not org:
        raise ValueError("Organization not found.")

    # All active clients
    businesses = (
        Business.query
        .filter_by(org_id=org_id, is_active=True)
        .order_by(Business.created_at.desc())
        .all()
    )
    biz_ids = [b.id for b in businesses]

    # Last transaction date per business — one query
    last_tx_map: dict = {}
    if biz_ids:
        rows = (
            db.session.query(
                BusinessStatement.business_id,
                func.max(BusinessStatement.transaction_date).label("last_tx"),
            )
            .filter(BusinessStatement.business_id.in_(biz_ids))
            .group_by(BusinessStatement.business_id)
            .all()
        )
        for r in rows:
            last_tx_map[r.business_id] = r.last_tx

    # Compliance scores — one query
    score_map: dict = {}
    if biz_ids:
        for p in ComplianceProfile.query.filter(
            ComplianceProfile.business_id.in_(biz_ids)
        ).all():
            score_map[p.business_id] = p.discipline_score

    # Recent transaction count (current month) per business
    today = date.today()
    month_start = datetime(today.year, today.month, 1)
    tx_count_map: dict = {}
    if biz_ids:
        rows2 = (
            db.session.query(
                BusinessStatement.business_id,
                func.count(BusinessStatement.id).label("cnt"),
            )
            .filter(
                BusinessStatement.business_id.in_(biz_ids),
                BusinessStatement.transaction_date >= month_start,
            )
            .group_by(BusinessStatement.business_id)
            .all()
        )
        for r in rows2:
            tx_count_map[r.business_id] = r.cnt

    # Build client list
    client_list = []
    for biz in businesses:
        last_tx  = last_tx_map.get(biz.id)
        days     = _days_since(last_tx)
        color    = _compliance_color(days)
        client_list.append({
            "id":                   biz.id,
            "name":                 biz.name,
            "business_type":        biz.business_type,
            "phone":                biz.phone,
            "invite_status":        biz.invite_status,
            "compliance_color":     color,
            "compliance_score":     score_map.get(biz.id),
            "days_since_last_entry": days,
            "last_transaction_at":  last_tx.isoformat() if last_tx else None,
            "transactions_this_month": tx_count_map.get(biz.id, 0),
        })

    # Sort: red → yellow → green; within same color, most-urgent first
    _order = {"red": 0, "yellow": 1, "green": 2}
    client_list.sort(key=lambda c: (
        _order.get(c["compliance_color"], 3),
        c["days_since_last_entry"] if c["days_since_last_entry"] is not None else 9999
    ))

    # Counts
    total    = len(client_list)
    active   = sum(1 for b in businesses if b.invite_status == "active")
    invited  = sum(1 for b in businesses if b.invite_status in ("pending", "invited"))
    red      = sum(1 for c in client_list if c["compliance_color"] == "red")
    yellow   = sum(1 for c in client_list if c["compliance_color"] == "yellow")
    green    = sum(1 for c in client_list if c["compliance_color"] == "green")

    # Recent open alerts (last 10)
    alerts = []
    if biz_ids:
        alert_rows = (
            ComplianceAlert.query
            .filter(
                ComplianceAlert.business_id.in_(biz_ids),
                ComplianceAlert.status == ComplianceAlert.AlertStatus.OPEN,
            )
            .order_by(ComplianceAlert.created_at.desc())
            .limit(10)
            .all()
        )
        alerts = [_alert_dict(a) for a in alert_rows]

    unread = len(alerts)

    return {
        "org_name": org.name,
        "stats": {
            "total_clients":        total,
            "active_clients":       active,
            "invited_not_joined":   invited,
            "red_clients":          red,
            "yellow_clients":       yellow,
            "green_clients":        green,
            "unread_alerts":        unread,
        },
        "clients":       client_list,
        "recent_alerts": alerts,
    }


# ------------------------------------------------------------------ #
# 2. Client detail
# ------------------------------------------------------------------ #

def get_client_detail(org_id: int, business_id: int) -> dict:
    """
    Full client profile + current-month stats + last 10 transactions
    with evidence info.
    """
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        raise ValueError("Client not found.")

    today       = date.today()
    month_start = datetime(today.year, today.month, 1)

    # ── Current-month statements ──────────────────────────────── #
    month_stmts = (
        BusinessStatement.query
        .filter(
            BusinessStatement.business_id == business_id,
            BusinessStatement.transaction_date >= month_start,
        )
        .all()
    )

    total_sales    = sum(s.amount or 0 for s in month_stmts if s.statement_type == "sale")
    total_expenses = sum(s.amount or 0 for s in month_stmts if s.statement_type == "expense")
    tx_count       = len(month_stmts)

    # Evidence for this month's statements
    month_stmt_ids = [s.id for s in month_stmts]
    ev_map_month   = _ev_for_stmts(month_stmt_ids)
    with_ev        = len(ev_map_month)

    # Overall evidence breakdown
    all_evs = BusinessEvidence.query.filter_by(business_id=business_id).all()
    ev_breakdown = {
        "strong": sum(1 for e in all_evs if e.evidence_strength == "strong"),
        "medium": sum(1 for e in all_evs if e.evidence_strength == "medium"),
        "weak":   sum(1 for e in all_evs if e.evidence_strength == "weak"),
    }

    # ── Last 10 transactions (all time) ──────────────────────── #
    last_10 = (
        BusinessStatement.query
        .filter_by(business_id=business_id)
        .order_by(
            BusinessStatement.transaction_date.desc(),
            BusinessStatement.created_at.desc(),
        )
        .limit(10)
        .all()
    )
    ev_map_10 = _ev_for_stmts([s.id for s in last_10])

    recent_txs = []
    for s in last_10:
        ev = ev_map_10.get(s.id)
        recent_txs.append({
            "id":               s.id,
            "type":             s.statement_type,
            "amount":           s.amount,
            "category":         s.raw_text,
            "description":      s.description,
            "confidence":       s.confidence_level,
            "transaction_date": s.transaction_date.date().isoformat() if s.transaction_date else None,
            "created_at":       s.created_at.isoformat(),
            "evidence": {
                "id":            ev.id,
                "strength":      ev.evidence_strength,
                "ocr_status":    ev.ocr_status,
                "thumbnail_url": ev.thumbnail_url,
                "ocr_amount":    ev.detected_amount,
            } if ev else None,
        })

    # ── Compliance color ──────────────────────────────────────── #
    last_tx   = last_10[0].transaction_date if last_10 else None
    days      = _days_since(last_tx)
    color     = _compliance_color(days)
    profile   = ComplianceProfile.query.filter_by(business_id=business_id).first()
    comp_score = profile.discipline_score if profile else None

    # ── Owner info ───────────────────────────────────────────── #
    owner = biz.owner

    return {
        "client": {
            "id":                biz.id,
            "name":              biz.name,
            "business_type":     biz.business_type,
            "state":             biz.state,
            "gstin":             biz.gstin,
            "pan":               biz.pan,
            "phone":             biz.phone,
            "expected_turnover": biz.expected_turnover,
            "invite_status":     biz.invite_status,
            "invite_code":       biz.invite_code,
            "is_active":         biz.is_active,
            "created_at":        biz.created_at.isoformat(),
            "owner_name":        owner.name  if owner else None,
            "owner_phone":       owner.phone if owner else None,
        },
        "stats": {
            "total_sales_this_month":    round(total_sales, 2),
            "total_expenses_this_month": round(total_expenses, 2),
            "net_income_this_month":     round(total_sales - total_expenses, 2),
            "transaction_count":         tx_count,
            "with_evidence":             with_ev,
            "without_evidence":          tx_count - with_ev,
            "evidence_breakdown":        ev_breakdown,
        },
        "compliance_color":       color,
        "compliance_score":       comp_score,
        "days_since_last_entry":  days,
        "recent_transactions":    recent_txs,
    }


# ------------------------------------------------------------------ #
# 3. Filing summary
# ------------------------------------------------------------------ #

def get_filing_summary(org_id: int, business_id: int,
                       year: int, month: int) -> dict:
    """
    Aggregate all transactions for a client in a calendar month.
    Returns totals, confidence breakdown, and transaction list.
    """
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        raise ValueError("Client not found.")

    # Period bounds
    month_start = datetime(year, month, 1)
    next_month  = month + 1 if month < 12 else 1
    next_year   = year if month < 12 else year + 1
    month_end   = datetime(next_year, next_month, 1)

    stmts = (
        BusinessStatement.query
        .filter(
            BusinessStatement.business_id == business_id,
            BusinessStatement.transaction_date >= month_start,
            BusinessStatement.transaction_date <  month_end,
        )
        .order_by(BusinessStatement.transaction_date.asc())
        .all()
    )

    ev_map = _ev_for_stmts([s.id for s in stmts])

    total_sales    = 0.0
    total_expenses = 0.0
    high_cnt = medium_cnt = low_cnt = 0
    with_ev_cnt    = 0
    transactions   = []
    low_conf_txs   = []

    for s in stmts:
        amount = s.amount or 0.0
        if s.statement_type == "sale":
            total_sales    += amount
        elif s.statement_type == "expense":
            total_expenses += amount

        cl = s.confidence_level or "low"
        if cl == "high":
            high_cnt += 1
        elif cl == "medium":
            medium_cnt += 1
        else:
            low_cnt += 1

        ev = ev_map.get(s.id)
        if ev:
            with_ev_cnt += 1

        tx_dict = {
            "id":               s.id,
            "type":             s.statement_type,
            "category":         s.raw_text,
            "amount":           round(amount, 2),
            "transaction_date": s.transaction_date.date().isoformat() if s.transaction_date else None,
            "confidence":       cl,
            "confidence_reason": s.confidence_reason,
            "description":      s.description,
            "verified":         bool(s.verified),
            "evidence": {
                "id":            ev.id,
                "strength":      ev.evidence_strength,
                "ocr_status":    ev.ocr_status,
                "ocr_amount":    ev.detected_amount,
                "thumbnail_url": ev.thumbnail_url,
            } if ev else None,
        }
        transactions.append(tx_dict)
        if cl != "high":
            low_conf_txs.append(tx_dict)

    # Tax estimate (simplified for MVP)
    estimated_tax = 0.0
    if biz.gstin:
        # Rough 18% GST on net sales for registered businesses
        estimated_tax = round(total_sales * 0.18, 2)

    return {
        "client": {
            "id":            biz.id,
            "name":          biz.name,
            "gstin":         biz.gstin,
            "business_type": biz.business_type,
        },
        "period": f"{year:04d}-{month:02d}",
        "totals": {
            "sales":          round(total_sales, 2),
            "expenses":       round(total_expenses, 2),
            "net":            round(total_sales - total_expenses, 2),
            "estimated_tax":  estimated_tax,
        },
        "confidence_breakdown": {
            "high":          high_cnt,
            "medium":        medium_cnt,
            "low":           low_cnt,
            "total":         len(stmts),
            "with_evidence": with_ev_cnt,
        },
        "transactions":               transactions,
        "low_confidence_transactions": low_conf_txs,
    }


# ------------------------------------------------------------------ #
# 4. Excel export
# ------------------------------------------------------------------ #

def export_filing_excel(org_id: int, business_id: int,
                        year: int, month: int) -> bytes:
    """
    Generate an Excel workbook from the filing summary.

    Sheet 1: Summary
    Sheet 2: All Transactions
    Sheet 3: Low Confidence — Review

    Returns raw bytes.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("openpyxl is not installed. Run: pip install openpyxl")

    summary = get_filing_summary(org_id, business_id, year, month)
    period  = summary["period"]
    client  = summary["client"]

    # ── Helpers ──────────────────────────────────────────────── #
    def _bold(ws, row, col, value):
        c = ws.cell(row=row, column=col, value=value)
        c.font = Font(bold=True)
        return c

    def _header_row(ws, row, headers):
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=col, value=h)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill(fill_type="solid", fgColor="1F4E79")
            c.alignment = Alignment(horizontal="center")

    def _set_col_widths(ws, widths):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # ── Workbook ─────────────────────────────────────────────── #
    wb = openpyxl.Workbook()

    # ── Sheet 1: Summary ─────────────────────────────────────── #
    ws1 = wb.active
    ws1.title = "Summary"

    title = f"{client['name']} — Filing Summary — {period}"
    c = ws1.cell(row=1, column=1, value=title)
    c.font = Font(bold=True, size=14)
    ws1.merge_cells("A1:C1")

    if client.get("gstin"):
        ws1.cell(row=2, column=1, value=f"GSTIN: {client['gstin']}")

    _header_row(ws1, 4, ["Metric", "Value"])

    rows_data = [
        ("Total Sales (₹)",            summary["totals"]["sales"]),
        ("Total Expenses (₹)",         summary["totals"]["expenses"]),
        ("Net Income (₹)",             summary["totals"]["net"]),
        ("Estimated Tax Liability (₹)",summary["totals"]["estimated_tax"]),
        ("", ""),
        ("Total Transactions",         summary["confidence_breakdown"]["total"]),
        ("With Evidence",              summary["confidence_breakdown"]["with_evidence"]),
        ("High Confidence",            summary["confidence_breakdown"]["high"]),
        ("Medium Confidence",          summary["confidence_breakdown"]["medium"]),
        ("Low Confidence (Review!)",   summary["confidence_breakdown"]["low"]),
    ]
    for i, (metric, value) in enumerate(rows_data, 5):
        ws1.cell(row=i, column=1, value=metric)
        ws1.cell(row=i, column=2, value=value)
        if "Low Confidence" in metric:
            ws1.cell(row=i, column=1).font = Font(bold=True, color="C00000")
            ws1.cell(row=i, column=2).font = Font(bold=True, color="C00000")

    note_row = 5 + len(rows_data) + 1
    ws1.cell(row=note_row, column=1,
             value="Note: Tax estimate is indicative (18% GST on sales). "
                   "Final liability depends on HSN codes and applicable scheme.")
    ws1.cell(row=note_row, column=1).font = Font(italic=True, color="808080")
    ws1.merge_cells(f"A{note_row}:C{note_row}")

    _set_col_widths(ws1, [35, 20, 20])

    # ── Sheet 2: All Transactions ─────────────────────────────── #
    ws2 = wb.create_sheet("All Transactions")
    hdrs2 = ["Date", "Type", "Category", "Amount (₹)",
             "Confidence", "Verified", "Has Evidence", "Evidence Strength", "Description"]
    _header_row(ws2, 1, hdrs2)

    for i, tx in enumerate(summary["transactions"], 2):
        ev = tx.get("evidence") or {}
        ws2.cell(row=i, column=1, value=tx["transaction_date"])
        ws2.cell(row=i, column=2, value=tx["type"])
        ws2.cell(row=i, column=3, value=tx.get("category") or "")
        ws2.cell(row=i, column=4, value=tx["amount"])
        ws2.cell(row=i, column=5, value=tx["confidence"])
        ws2.cell(row=i, column=6, value="Yes" if tx["verified"] else "No")
        ws2.cell(row=i, column=7, value="Yes" if ev else "No")
        ws2.cell(row=i, column=8, value=ev.get("strength", "") if ev else "")
        ws2.cell(row=i, column=9, value=tx.get("description") or "")

        # Colour-code confidence
        cl = tx["confidence"]
        if cl == "high":
            ws2.cell(row=i, column=5).font = Font(color="375623")
        elif cl == "medium":
            ws2.cell(row=i, column=5).font = Font(color="7B6000")
        else:
            ws2.cell(row=i, column=5).font = Font(color="C00000", bold=True)

    _set_col_widths(ws2, [12, 10, 15, 14, 12, 10, 14, 16, 30])

    # ── Sheet 3: Low Confidence — Review ─────────────────────── #
    ws3 = wb.create_sheet("Low Confidence — Review")
    c3 = ws3.cell(row=1, column=1,
                  value="⚠  These transactions need CA review before filing")
    c3.font = Font(bold=True, color="C00000", size=12)
    ws3.merge_cells("A1:I1")

    if summary["low_confidence_transactions"]:
        hdrs3 = ["Date", "Type", "Category", "Amount (₹)",
                 "Confidence", "Reason", "Has Evidence", "Description"]
        _header_row(ws3, 2, hdrs3)

        for i, tx in enumerate(summary["low_confidence_transactions"], 3):
            ws3.cell(row=i, column=1, value=tx["transaction_date"])
            ws3.cell(row=i, column=2, value=tx["type"])
            ws3.cell(row=i, column=3, value=tx.get("category") or "")
            ws3.cell(row=i, column=4, value=tx["amount"])
            ws3.cell(row=i, column=5, value=tx["confidence"])
            ws3.cell(row=i, column=6, value=tx.get("confidence_reason") or "Manual entry — no photo")
            ws3.cell(row=i, column=7, value="Yes" if tx.get("evidence") else "No")
            ws3.cell(row=i, column=8, value=tx.get("description") or "")

        _set_col_widths(ws3, [12, 10, 15, 14, 12, 35, 14, 30])
    else:
        ws3.cell(row=3, column=1,
                 value="✓  All transactions have high confidence. No review needed.")
        ws3.cell(row=3, column=1).font = Font(color="375623", bold=True)
        ws3.merge_cells("A3:H3")

    # ── Serialize ─────────────────────────────────────────────── #
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
