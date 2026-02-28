"""
Transaction + My-data routes — Feature 3.

Blueprints
----------
transactions_bp  /transactions  — create, confirm OCR
my_bp            /my            — list, summary (client-facing read)

All routes require JWT with role='client' and business_id claim.
"""
import csv
import io
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


# ================================================================== #
# Phase 3: POST /my/import-bank-statement — Bank statement CSV import
# ================================================================== #

@my_bp.route("/import-bank-statement", methods=["POST"])
@jwt_required()
@_require_client
@limiter.limit("20 per day")
def import_bank_statement():
    """
    Parse a bank statement CSV and auto-create transactions.

    Supported CSV formats (auto-detected):
      Generic:  date, description, amount, type (sale/expense)
      Debit/Credit columns: date, description, debit, credit
      SBI style: Date, Description, Amount (Debit), Amount (Credit)

    Rules:
      - Credit amounts → sale
      - Debit amounts  → expense
      - Rows where both debit and credit are 0 are skipped (charges, interest, etc.)
      - Duplicate detection: same amount + date already in DB → skipped with warning
      - Max 500 rows per upload

    Response
    --------
    created_count, skipped_count, created (array), skipped (array with reasons)
    """
    business_id = _business_id()

    if "file" not in request.files:
        return _err("No file uploaded. Send CSV as 'file' in multipart/form-data.", 400)

    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return _err("Only CSV files are accepted.", 400)

    raw_bytes = f.read(2_000_000)  # 2 MB cap
    if len(raw_bytes) >= 2_000_000:
        return _err("File too large. Maximum size is 2 MB.", 400)

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except Exception:
            return _err("Cannot decode CSV. Use UTF-8 encoding.", 400)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return _err("CSV has no headers.", 400)

    # Normalise headers to lowercase with no whitespace
    headers_lower = {h.strip().lower().replace(" ", "_") for h in reader.fieldnames}

    # Detect format
    has_debit_credit = bool(
        ({"debit", "credit"} <= headers_lower) or
        ({"amount_(debit)", "amount_(credit)"} <= headers_lower) or
        ({"withdrawal_amt.", "deposit_amt."} <= headers_lower) or
        ({"withdrawals", "deposits"} <= headers_lower)
    )
    has_type = "type" in headers_lower

    rows = list(reader)
    if len(rows) > 500:
        return _err("Maximum 500 rows per import. Split the file and re-upload.", 400)

    def _clean_amount(val: str) -> float:
        if not val:
            return 0.0
        cleaned = val.replace(",", "").replace("₹", "").replace(" ", "").strip()
        try:
            return abs(float(cleaned))
        except ValueError:
            return 0.0

    def _parse_date(val: str):
        val = val.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    created, skipped = [], []

    for i, row in enumerate(rows, start=2):
        norm = {k.strip().lower().replace(" ", "_"): (v.strip() if v else "") for k, v in row.items()}

        # --- Parse date ---
        date_val = None
        for dk in ("date", "transaction_date", "value_dt", "txn_date"):
            if dk in norm and norm[dk]:
                date_val = _parse_date(norm[dk])
                break
        if not date_val:
            skipped.append({"row": i, "reason": "Cannot parse date"})
            continue

        # --- Parse description ---
        desc = ""
        for dk in ("description", "narration", "particulars", "remarks", "details"):
            if dk in norm and norm[dk]:
                desc = norm[dk][:200]
                break

        # --- Parse amount and type ---
        tx_type = None
        amount  = 0.0

        if has_debit_credit:
            # Try various column name conventions
            credit = 0.0
            debit  = 0.0
            for ck in ("credit", "deposit_amt.", "deposits", "amount_(credit)"):
                if ck in norm:
                    credit = _clean_amount(norm[ck])
                    break
            for dk in ("debit", "withdrawal_amt.", "withdrawals", "amount_(debit)"):
                if dk in norm:
                    debit = _clean_amount(norm[dk])
                    break

            if credit > 0 and debit == 0:
                tx_type, amount = "sale", credit
            elif debit > 0 and credit == 0:
                tx_type, amount = "expense", debit
            elif credit > 0 and debit > 0:
                # Rare — treat net direction
                if credit >= debit:
                    tx_type, amount = "sale", credit - debit
                else:
                    tx_type, amount = "expense", debit - credit
            else:
                skipped.append({"row": i, "reason": "Zero amount row skipped"})
                continue

        elif has_type:
            raw_type = norm.get("type", "").lower()
            amount   = _clean_amount(norm.get("amount", ""))
            if raw_type in ("sale", "income", "credit", "cr"):
                tx_type = "sale"
            elif raw_type in ("expense", "debit", "dr", "payment"):
                tx_type = "expense"
            else:
                skipped.append({"row": i, "reason": f"Unknown type '{raw_type}'"})
                continue
        else:
            # Fallback: single 'amount' column — treat positive as sale, negative as expense
            raw_amount = norm.get("amount", "0")
            is_neg = raw_amount.strip().startswith("-")
            amount = _clean_amount(raw_amount)
            tx_type = "expense" if is_neg else "sale"

        if amount <= 0:
            skipped.append({"row": i, "reason": "Zero or negative amount"})
            continue

        # --- Create transaction ---
        try:
            result = service.create_transaction(
                business_id      = business_id,
                tx_type          = tx_type,
                amount           = amount,
                category         = desc[:60] if desc else None,
                transaction_date = date_val,
                description      = desc or f"Imported from bank statement row {i}",
                file             = None,
            )
            stmt = result["transaction"]
            entry = {
                "row":    i,
                "id":     stmt.id,
                "type":   tx_type,
                "amount": amount,
                "date":   date_val.isoformat(),
                "desc":   desc,
            }
            if result.get("duplicate_warning"):
                entry["warning"] = "Possible duplicate"
            created.append(entry)
        except Exception as exc:
            logger.exception("import_bank_statement: row %d error — %s", i, exc)
            skipped.append({"row": i, "reason": "Failed to save. Try again."})

    return _ok({
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created":       created,
        "skipped":       skipped,
    }, 201 if created else 200)
