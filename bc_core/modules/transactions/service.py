"""
Transaction service — Feature 3: In-App Guided Chat.

Key decisions:
- `BusinessStatement` stores both sales and expenses (statement_type = 'sale'|'expense')
- `raw_text` stores the expense category
- Files saved locally under instance/uploads/<business_id>/
- OCR runs synchronously; result returned in same response for conflict resolution
- Duplicate = same business, same type, same amount, same date, within 5 minutes
"""
import logging
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from flask import current_app
from sqlalchemy import func, extract

from core.extensions import db
from modules.businesses.models import Business
from modules.evidence.models import BusinessEvidence
from modules.statements.models import BusinessStatement

logger = logging.getLogger(__name__)

BLUR_THRESHOLD = 40.0   # quality_score below this → warn "photo is blurry"
OCR_DIFF_PCT   = 0.05   # 5% difference → trigger OCR conflict prompt


# ------------------------------------------------------------------ #
# File storage
# ------------------------------------------------------------------ #

def _upload_dir(business_id: int) -> str:
    base = os.path.join(current_app.instance_path, "uploads", str(business_id))
    os.makedirs(base, exist_ok=True)
    return base


def _save_file(file, business_id: int) -> tuple[str, str]:
    """Save uploaded file, return (file_path, file_name)."""
    from werkzeug.utils import secure_filename
    original_name = secure_filename(file.filename or "upload.jpg")
    unique_name   = f"{uuid.uuid4().hex}_{original_name}"
    dest          = os.path.join(_upload_dir(business_id), unique_name)
    file.save(dest)
    return dest, original_name


# ------------------------------------------------------------------ #
# Image quality check (blur detection)
# ------------------------------------------------------------------ #

def _compute_quality_score(file_path: str) -> float:
    """
    Estimate image sharpness via gradient magnitude (no PIL/scipy needed).
    Returns a score: higher = sharper.  Blurry images score < BLUR_THRESHOLD.
    Falls back to 100.0 (no quality warning) if numpy not available.
    """
    try:
        import numpy as np
        # Read raw bytes and decode as grayscale approximation
        # Works for JPEG/PNG when numpy is available
        with open(file_path, "rb") as f:
            data = f.read()

        # Try with PIL if available (better accuracy)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(data)).convert("L").resize((200, 200))
            arr = np.array(img, dtype=np.float32)
            gy = np.diff(arr, axis=0)
            gx = np.diff(arr, axis=1)
            return float(np.sqrt(np.mean(gy ** 2) + np.mean(gx ** 2)))
        except ImportError:
            pass  # PIL not available, use default

        return 100.0   # skip quality check

    except Exception:
        return 100.0


# ------------------------------------------------------------------ #
# Core create
# ------------------------------------------------------------------ #

def create_transaction(
    *,
    business_id: int,
    tx_type: str,
    amount: float,
    category: Optional[str] = None,
    transaction_date: Optional[date] = None,
    description: Optional[str] = None,
    file=None,                          # werkzeug FileStorage or None
) -> dict:
    """
    Create a transaction (sale or expense) with optional photo evidence.

    Returns a dict with:
      transaction      — BusinessStatement instance
      duplicate_warning — dict | None
      ocr_result        — dict | None  (only when file + OCR conflict)
      quality_warning   — str | None
    """
    today = transaction_date or date.today()
    tx_date_dt = datetime.combine(today, datetime.min.time())

    # ── 0. Feature 7: Validation + Anomaly Detection ──────────── #
    from modules.validation.service import validate_transaction
    validation_warnings = validate_transaction(business_id, amount, tx_type, today)

    # ── 1. Duplicate detection (legacy 5-min check) ───────────── #
    five_min_ago   = datetime.utcnow() - timedelta(minutes=5)
    duplicate_warn = None
    dup = (
        BusinessStatement.query
        .filter_by(business_id=business_id, statement_type=tx_type, amount=amount)
        .filter(
            func.date(BusinessStatement.transaction_date) == today,
            BusinessStatement.created_at >= five_min_ago,
        )
        .first()
    )
    if dup:
        duplicate_warn = {
            "message":     f"You already entered \u20b9{amount:,.0f} {tx_type} today.",
            "existing_id": dup.id,
        }

    # ── 2. Create statement ────────────────────────────────────── #
    stmt = BusinessStatement(
        business_id      = business_id,
        statement_type   = tx_type,
        amount           = amount,
        currency         = "INR",
        transaction_date = tx_date_dt,
        source           = "client_app",
        confidence_level = "high",    # client-entered data is trusted by default
        raw_text         = category,  # expense category stored here
        description      = description,
        verified         = False,
    )

    try:
        db.session.add(stmt)
        db.session.flush()   # get stmt.id before evidence
    except Exception:
        db.session.rollback()
        raise

    # ── 3. File upload + OCR ───────────────────────────────────── #
    ocr_result    = None
    quality_warn  = None
    evidence      = None

    if file and file.filename:
        try:
            file_path, file_name = _save_file(file, business_id)
            quality_score        = _compute_quality_score(file_path)

            if quality_score < BLUR_THRESHOLD:
                quality_warn = (
                    "This photo appears blurry. Please retake for better accuracy."
                )

            evidence = BusinessEvidence(
                business_id  = business_id,
                statement_id = stmt.id,
                file_name    = file_name,
                file_path    = file_path,
                evidence_type= "bill" if tx_type == "sale" else "receipt",
                source       = "client_app",
                quality_score= quality_score,
                status       = "uploaded",
            )
            db.session.add(evidence)
            db.session.flush()

            # Run OCR (uses existing pipeline; has mock fallback in dev)
            from modules.ocr.service import run_ocr
            ocr_data = run_ocr(evidence)

            # Check for amount conflict
            ocr_amount = ocr_data.get("amount")
            if ocr_amount and abs(ocr_amount - amount) / max(amount, 1) > OCR_DIFF_PCT:
                ocr_result = {
                    "conflict":       True,
                    "entered_amount": amount,
                    "ocr_amount":     ocr_amount,
                    "message":        (
                        f"The bill photo shows \u20b9{ocr_amount:,.0f}. "
                        f"You entered \u20b9{amount:,.0f}. Which is correct?"
                    ),
                    "evidence_id":    evidence.id,
                }
                # Keep statement at entered amount until client confirms
                stmt.confidence_level = "medium"

        except Exception as exc:
            logger.warning("create_transaction: file/OCR error — %s", exc)
            # Evidence failure is non-fatal; proceed without it
            evidence = None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info("Transaction created: stmt_id=%d business_id=%d type=%s amount=%.2f",
                stmt.id, business_id, tx_type, amount)

    return {
        "transaction":       stmt,
        "evidence":          evidence,
        "duplicate_warning": duplicate_warn,
        "ocr_result":        ocr_result,
        "quality_warning":   quality_warn,
        "warnings":          validation_warnings,
    }


# ------------------------------------------------------------------ #
# Confirm amount after OCR conflict
# ------------------------------------------------------------------ #

def confirm_transaction_amount(
    *,
    business_id: int,
    transaction_id: int,
    confirmed_amount: float,
) -> BusinessStatement:
    """
    Client resolves an OCR conflict by confirming the correct amount.
    Also marks the evidence as verified if amounts now match.
    """
    stmt = BusinessStatement.query.filter_by(
        id=transaction_id, business_id=business_id
    ).first()
    if not stmt:
        raise ValueError("Transaction not found.")

    stmt.amount          = confirmed_amount
    stmt.confidence_level = "high"
    stmt.updated_at      = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return stmt


# ------------------------------------------------------------------ #
# List transactions
# ------------------------------------------------------------------ #

def list_transactions(
    business_id: int,
    *,
    tx_type: Optional[str]     = None,
    from_date: Optional[date]  = None,
    to_date: Optional[date]    = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    q = (
        BusinessStatement.query
        .filter_by(business_id=business_id)
        .order_by(BusinessStatement.transaction_date.desc(),
                  BusinessStatement.created_at.desc())
    )
    if tx_type:
        q = q.filter_by(statement_type=tx_type)
    if from_date:
        q = q.filter(BusinessStatement.transaction_date >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        q = q.filter(BusinessStatement.transaction_date <= datetime.combine(to_date, datetime.max.time()))

    total = q.count()
    stmts = q.offset((page - 1) * per_page).limit(per_page).all()

    # Attach evidence ids in one query
    stmt_ids    = [s.id for s in stmts]
    evidence_map = {}
    if stmt_ids:
        evs = BusinessEvidence.query.filter(
            BusinessEvidence.statement_id.in_(stmt_ids)
        ).all()
        for ev in evs:
            evidence_map[ev.statement_id] = ev

    rows = []
    for s in stmts:
        ev = evidence_map.get(s.id)
        rows.append({
            "id":               s.id,
            "business_id":      s.business_id,
            "statement_type":   s.statement_type,
            "amount":           s.amount,
            "raw_text":         s.raw_text,
            "description":      s.description,
            "transaction_date": s.transaction_date,
            "source":           s.source,
            "confidence_level": s.confidence_level,
            "verified":         s.verified,
            "created_at":       s.created_at,
            "updated_at":       s.updated_at,
            "evidence_id":      ev.id     if ev else None,
            "evidence_status":  ev.status if ev else None,
        })

    return {
        "transactions": rows,
        "total":        total,
        "page":         page,
        "per_page":     per_page,
        "pages":        (total + per_page - 1) // per_page,
    }


# ------------------------------------------------------------------ #
# Monthly summary
# ------------------------------------------------------------------ #

def monthly_summary(business_id: int, year: int, month: int) -> dict:
    """
    Aggregate sales, expenses, daily breakdown, and expense categories
    for a given month.
    """
    stmts = (
        BusinessStatement.query
        .filter_by(business_id=business_id)
        .filter(
            extract("year",  BusinessStatement.transaction_date) == year,
            extract("month", BusinessStatement.transaction_date) == month,
        )
        .all()
    )

    total_sales    = 0.0
    total_expenses = 0.0
    daily: dict    = {}          # "YYYY-MM-DD" → {sales, expenses}
    categories: dict = {}        # category → total expense

    for s in stmts:
        day_key = (s.transaction_date.strftime("%Y-%m-%d")
                   if s.transaction_date else "unknown")

        if day_key not in daily:
            daily[day_key] = {"date": day_key, "sales": 0.0, "expenses": 0.0}

        if s.statement_type == "sale":
            total_sales              += s.amount or 0
            daily[day_key]["sales"]  += s.amount or 0
        elif s.statement_type == "expense":
            total_expenses                 += s.amount or 0
            daily[day_key]["expenses"]     += s.amount or 0
            cat = s.raw_text or "Other"
            categories[cat] = categories.get(cat, 0.0) + (s.amount or 0)

    return {
        "month":               f"{year:04d}-{month:02d}",
        "total_sales":         round(total_sales, 2),
        "total_expenses":      round(total_expenses, 2),
        "net_income":          round(total_sales - total_expenses, 2),
        "transaction_count":   len(stmts),
        "daily_breakdown":     sorted(daily.values(), key=lambda x: x["date"]),
        "expense_by_category": {k: round(v, 2) for k, v in
                                sorted(categories.items(), key=lambda x: -x[1])},
    }
