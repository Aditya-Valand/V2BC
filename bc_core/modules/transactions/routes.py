"""
Transaction + My-data routes — Feature 3.

Blueprints
----------
transactions_bp  /transactions  — create, confirm OCR
my_bp            /my            — list, summary (client-facing read)

All routes require JWT with role='client' and business_id claim.
"""
import logging
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from core.extensions import limiter
from modules.transactions import service
from modules.transactions.schemas import (
    MonthlySummarySchema,
    TransactionConfirmSchema,
    TransactionCreateSchema,
    TransactionSchema,
)

logger = logging.getLogger(__name__)

transactions_bp = Blueprint("transactions", __name__)
my_bp           = Blueprint("my",           __name__)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _ok(data, status=200):
    return jsonify({"success": True,  "data": data,  "error": None}), status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None,  "error": msg}),  status

def _business_id() -> int | None:
    return get_jwt().get("business_id")

def _require_client(f):
    """Decorator: ensure JWT has role=client and business_id."""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "client":
            return _err("Client access only.", 403)
        if not claims.get("business_id"):
            return _err("Token missing business_id. Please log in again.", 401)
        return f(*args, **kwargs)
    return wrapper


# ================================================================== #
# POST /transactions — create a transaction
# ================================================================== #

@transactions_bp.route("", methods=["POST"])
@jwt_required()
@_require_client
@limiter.limit("200 per day; 30 per hour")
def create_transaction():
    """
    Create a sale or expense entry.

    Accepts either:
      - JSON body (no photo): Content-Type: application/json
      - Multipart form  (with photo): Content-Type: multipart/form-data
        form fields: type, amount, category, transaction_date, description
        file field:  evidence_file

    Response includes:
      transaction      — created record
      duplicate_warning — present if same amount+type already entered today (last 5 min)
      ocr_result        — present when photo OCR detects a different amount
      quality_warning   — present when photo is blurry (score < 40)

    Edge cases handled
    ------------------
    - amount == 0 or negative    → 400
    - amount with commas (8,200) → strip on client; also handled server-side
    - Duplicate entry (5-min window) → 200 with duplicate_warning (not blocked,
      just warned — client decides whether to add another)
    - Blurry photo               → 200 with quality_warning
    - OCR amount differs ≥5%     → 200 with ocr_result.conflict=true
    - No photo                   → 200, no evidence created
    """
    business_id = _business_id()

    # Support both JSON and multipart
    if request.content_type and "multipart" in request.content_type:
        raw = {k: v for k, v in request.form.items()}
        # Strip commas from amount (e.g. "8,200" → "8200")
        if "amount" in raw:
            raw["amount"] = raw["amount"].replace(",", "")
        file = request.files.get("evidence_file")
    else:
        raw  = request.get_json(silent=True) or {}
        if "amount" in raw and isinstance(raw["amount"], str):
            raw["amount"] = raw["amount"].replace(",", "")
        file = None

    try:
        data = TransactionCreateSchema().load(raw)
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        result = service.create_transaction(
            business_id      = business_id,
            tx_type          = data["type"],
            amount           = data["amount"],
            category         = data.get("category"),
            transaction_date = data.get("transaction_date"),
            description      = data.get("description"),
            file             = file,
        )
    except Exception as exc:
        logger.exception("create_transaction: %s", exc)
        return _err("Failed to create transaction.", 500)

    stmt = result["transaction"]
    ev   = result["evidence"]

    response = {
        "transaction": {
            "id":               stmt.id,
            "type":             stmt.statement_type,
            "amount":           stmt.amount,
            "category":         stmt.raw_text,
            "description":      stmt.description,
            "transaction_date": stmt.transaction_date.isoformat() if stmt.transaction_date else None,
            "confidence_level": stmt.confidence_level,
            "source":           stmt.source,
            "created_at":       stmt.created_at.isoformat(),
            "evidence_id":      ev.id if ev else None,
        },
        "duplicate_warning": result["duplicate_warning"],
        "ocr_result":        result["ocr_result"],
        "quality_warning":   result["quality_warning"],
        "warnings":          result.get("warnings", []),
    }
    return _ok(response, 201)


# ================================================================== #
# PATCH /transactions/:id — confirm amount after OCR conflict
# ================================================================== #

@transactions_bp.route("/<int:transaction_id>", methods=["PATCH"])
@jwt_required()
@_require_client
def confirm_transaction(transaction_id: int):
    """
    Resolve an OCR amount conflict by confirming the correct amount.

    Called when create_transaction returns ocr_result.conflict=true
    and the client chooses the correct value.

    Edge cases
    ----------
    - transaction_id not owned by this client  → 404
    - amount <= 0                              → 400
    """
    business_id = _business_id()

    try:
        data = TransactionConfirmSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        stmt = service.confirm_transaction_amount(
            business_id      = business_id,
            transaction_id   = transaction_id,
            confirmed_amount = data["amount"],
        )
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("confirm_transaction: %s", exc)
        return _err("Failed to update transaction.", 500)

    return _ok({
        "transaction": {
            "id":     stmt.id,
            "amount": stmt.amount,
            "confidence_level": stmt.confidence_level,
        }
    })


# ================================================================== #
# GET /my/transactions — client's own transaction history
# ================================================================== #

@my_bp.route("/transactions", methods=["GET"])
@jwt_required()
@_require_client
def list_transactions():
    """
    Paginated list of the client's transactions.

    Query params
    ------------
    type      — 'sale' | 'expense'
    from      — YYYY-MM-DD
    to        — YYYY-MM-DD
    page      — int (default 1)
    per_page  — int (default 20, max 100)

    Edge cases
    ----------
    - No transactions yet → empty list, 200
    - Invalid date format → 400
    """
    business_id = _business_id()

    tx_type  = request.args.get("type")
    page     = max(1, int(request.args.get("page", 1) or 1))
    per_page = min(100, max(1, int(request.args.get("per_page", 20) or 20)))

    from_date = to_date = None
    try:
        if request.args.get("from"):
            from_date = date.fromisoformat(request.args["from"])
        if request.args.get("to"):
            to_date = date.fromisoformat(request.args["to"])
    except ValueError:
        return _err("Invalid date format. Use YYYY-MM-DD.", 400)

    if tx_type and tx_type not in ("sale", "expense"):
        return _err("type must be 'sale' or 'expense'.", 400)

    try:
        result = service.list_transactions(
            business_id,
            tx_type   = tx_type,
            from_date = from_date,
            to_date   = to_date,
            page      = page,
            per_page  = per_page,
        )
    except Exception as exc:
        logger.exception("list_transactions: %s", exc)
        return _err("Failed to fetch transactions.", 500)

    # Rename statement_type → type in response
    for t in result["transactions"]:
        t["type"]     = t.pop("statement_type", None)
        t["category"] = t.pop("raw_text", None)

    return _ok(result)


# ================================================================== #
# GET /my/summary — monthly summary
# ================================================================== #

@my_bp.route("/summary", methods=["GET"])
@jwt_required()
@_require_client
def monthly_summary():
    """
    Aggregated sales/expense summary for a month.

    Query params
    ------------
    month — YYYY-MM  (default: current month)

    Response
    --------
    total_sales, total_expenses, net_income, transaction_count,
    daily_breakdown (array of {date, sales, expenses}),
    expense_by_category (dict of category → total)

    Edge cases
    ----------
    - No data for month → all zeros, empty arrays
    - Invalid month format → 400
    """
    business_id = _business_id()

    month_str = request.args.get("month") or datetime.utcnow().strftime("%Y-%m")
    try:
        year, month = [int(x) for x in month_str.split("-")]
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        return _err("Invalid month format. Use YYYY-MM.", 400)

    try:
        summary = service.monthly_summary(business_id, year, month)
    except Exception as exc:
        logger.exception("monthly_summary: %s", exc)
        return _err("Failed to compute summary.", 500)

    return _ok({"summary": summary})


# ================================================================== #
# GET /my/compliance-score — client's own compliance score
# ================================================================== #

@my_bp.route("/compliance-score", methods=["GET"])
@jwt_required()
@_require_client
def get_compliance_score():
    """
    Return the compliance score and grade for the authenticated client.

    Uses ComplianceProfile (computed by the rule engine).
    Falls back to sensible defaults if the profile hasn't been computed yet.

    Response
    --------
    score          — discipline_score 0-100
    grade          — A/B/C/D derived from score
    evidence_health — 0-100
    gst_risk_level  — low | medium | high
    business_name   — client's business name
    ca_name         — name of the CA who manages this client
    last_updated    — ISO datetime of last profile update (nullable)
    """
    business_id = _business_id()

    from modules.compliance.models import ComplianceProfile
    from modules.businesses.models import Business
    from modules.auth.models import User
    from modules.organizations.models import Organization

    profile  = ComplianceProfile.query.filter_by(business_id=business_id).first()
    business = Business.query.get(business_id)

    # Resolve CA name via org owner
    ca_name = None
    if business and business.org_id:
        org = Organization.query.get(business.org_id)
        if org:
            ca_user = User.query.get(org.owner_id)
            ca_name = ca_user.name if ca_user else None

    score          = profile.discipline_score if profile else 50
    evidence_health = profile.evidence_health  if profile else 50
    gst_risk        = profile.gst_risk_level.value if profile else "low"

    if   score >= 80: grade = "A"
    elif score >= 60: grade = "B"
    elif score >= 40: grade = "C"
    else:             grade = "D"

    return _ok({
        "score":           score,
        "grade":           grade,
        "evidence_health": evidence_health,
        "gst_risk_level":  gst_risk,
        "business_name":   business.name if business else "My Business",
        "ca_name":         ca_name,
        "last_updated":    profile.last_updated.isoformat() if profile and profile.last_updated else None,
    })


# ================================================================== #
# GET /my/annual-summary — 12-month annual summary
# ================================================================== #

@my_bp.route("/annual-summary", methods=["GET"])
@jwt_required()
@_require_client
def annual_summary():
    """
    Aggregated sales/expense/net summary for all 12 months of a year.

    Query params
    ------------
    year  — int (default: current year, min: 2020)

    Response
    --------
    year, months (array of 12), totals

    Edge cases
    ----------
    - Year with no data → all zeros for every month
    - Invalid year      → 400
    """
    business_id = _business_id()
    current_year = datetime.utcnow().year

    try:
        year = int(request.args.get("year", current_year))
        if not (2020 <= year <= current_year + 1):
            raise ValueError
    except (ValueError, TypeError):
        return _err(f"Invalid year. Must be between 2020 and {current_year + 1}.", 400)

    months_data = []
    total_sales = total_expenses = total_tx = 0

    for m in range(1, 13):
        try:
            summary = service.monthly_summary(business_id, year, m)
            s = summary.get("total_sales", 0) or 0
            e = summary.get("total_expenses", 0) or 0
            c = summary.get("transaction_count", 0) or 0
        except Exception:
            s = e = c = 0

        months_data.append({
            "month":             m,
            "month_label":       datetime(year, m, 1).strftime("%B"),
            "month_short":       datetime(year, m, 1).strftime("%b"),
            "sales":             s,
            "expenses":          e,
            "net":               s - e,
            "transaction_count": c,
        })
        total_sales    += s
        total_expenses += e
        total_tx       += c

    return _ok({
        "year":   year,
        "months": months_data,
        "totals": {
            "sales":             total_sales,
            "expenses":          total_expenses,
            "net":               total_sales - total_expenses,
            "transaction_count": total_tx,
        },
    })
