"""
Client management + Invite routes — Feature 2.

Blueprints
----------
clients_bp  — /clients  (JWT required; CA-facing)
invite_bp   — /invite   (public; client-facing)

CA endpoints
------------
POST  /clients           — create client
GET   /clients           — list all clients for the CA's org
GET   /clients/:id       — single client detail
PUT   /clients/:id       — update client
POST  /clients/:id/regenerate-invite — new invite code (if expired/lost)

Invite (public) endpoints
-------------------------
GET   /invite/:code      — landing page data (CA name, client name)
POST  /invite/accept     — client submits name + phone + pin
POST  /invite/verify-otp — client verifies phone OTP → tokens issued
"""
import csv
import io
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from core.extensions import limiter
from modules.auth.service import create_tokens
from modules.businesses import service
from modules.businesses.schemas import (
    ClientCreateSchema,
    ClientDetailSchema,
    ClientSummarySchema,
    ClientUpdateSchema,
    InviteAcceptSchema,
    InviteLandingSchema,
    InviteVerifyOTPSchema,
)
from modules.businesses.sms_service import send_otp_sms

logger = logging.getLogger(__name__)

clients_bp = Blueprint("clients", __name__)
invite_bp  = Blueprint("invite",  __name__)


# ------------------------------------------------------------------ #
# Shared helpers
# ------------------------------------------------------------------ #

def _ok(data, status=200):
    return jsonify({"success": True,  "data": data,  "error": None}),  status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status

def _org_id_from_token() -> int:
    """Pull org_id from JWT claims.  Returns None if missing."""
    return get_jwt().get("org_id")


# ================================================================== #
# CA-facing: /clients
# ================================================================== #

@clients_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("60 per hour")
def create_client():
    """
    CA creates a new client record.

    Returns the client + invite_url + QR SVG.

    Edge cases
    ----------
    - Missing name              → 400
    - Duplicate GSTIN/PAN in org → 409
    - Duplicate whatsapp_phone  → 409
    - Invalid GSTIN/PAN format  → 400
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    try:
        data = ClientCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        result = service.create_client(org_id=org_id, **data)
    except ValueError as exc:
        return _err(str(exc), 409)
    except Exception as exc:
        logger.exception("create_client: unexpected error — %s", exc)
        return _err("Failed to create client.", 500)

    b = result["business"]
    return _ok({
        "client":     ClientDetailSchema().dump({
            "id": b.id, "org_id": b.org_id, "owner_user_id": b.owner_user_id,
            "name": b.name, "business_type": b.business_type, "state": b.state,
            "gstin": b.gstin, "pan": b.pan, "expected_turnover": b.expected_turnover,
            "phone": b.phone, "whatsapp_phone": b.whatsapp_phone,
            "invite_code": b.invite_code, "invite_status": b.invite_status,
            "invite_expires_at": b.invite_expires_at, "is_active": b.is_active,
            "created_at": b.created_at, "updated_at": b.updated_at,
            "owner_name": None, "owner_phone": None,
        }),
        "invite_url": result["invite_url"],
        "qr_svg":     result["qr_svg"],
    }, 201)


@clients_bp.route("", methods=["GET"])
@jwt_required()
def list_clients():
    """
    CA lists all clients for their org.

    Includes statement_count, last_activity, compliance_score per client.

    Edge cases
    ----------
    - No org_id in token  → 401
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    try:
        clients = service.list_clients(org_id)
    except Exception as exc:
        logger.exception("list_clients: unexpected error — %s", exc)
        return _err("Failed to fetch clients.", 500)

    return _ok({
        "clients": ClientSummarySchema(many=True).dump(clients),
        "total":   len(clients),
    })


@clients_bp.route("/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id: int):
    """
    CA views a single client.

    Edge cases
    ----------
    - client_id not in org → 404
    - No org_id in token   → 401
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    try:
        detail = service.get_client(org_id, client_id)
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("get_client: unexpected error — %s", exc)
        return _err("Failed to fetch client.", 500)

    return _ok({"client": ClientDetailSchema().dump(detail)})


@clients_bp.route("/<int:client_id>", methods=["PUT"])
@jwt_required()
@limiter.limit("120 per hour")
def update_client(client_id: int):
    """
    CA updates a client's details.

    Edge cases
    ----------
    - No fields provided    → 400
    - Client not in org     → 404
    - Duplicate GSTIN/PAN   → 409
    - Duplicate WA phone    → 409
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    payload = request.get_json(silent=True) or {}
    if not payload:
        return _err("No fields provided.", 400)

    try:
        data = ClientUpdateSchema().load(payload)
    except ValidationError as exc:
        return _err(exc.messages, 400)

    if not data:
        return _err("No valid fields to update.", 400)

    try:
        business = service.update_client(org_id, client_id, data)
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "not found" in msg.lower() else 409
        return _err(msg, status)
    except Exception as exc:
        logger.exception("update_client: unexpected error — %s", exc)
        return _err("Failed to update client.", 500)

    try:
        detail = service.get_client(org_id, client_id)
    except Exception:
        detail = {"id": business.id, "name": business.name}

    return _ok({"client": ClientDetailSchema().dump(detail)})


@clients_bp.route("/<int:client_id>/regenerate-invite", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def regenerate_invite(client_id: int):
    """
    CA requests a new invite code for a client who lost the link.

    Edge cases
    ----------
    - Client already active → 400
    - Client not in org     → 404
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    try:
        result = service.regenerate_invite(org_id, client_id)
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "not found" in msg.lower() else 400
        return _err(msg, status)
    except Exception as exc:
        logger.exception("regenerate_invite: unexpected error — %s", exc)
        return _err("Failed to regenerate invite.", 500)

    return _ok({
        "invite_url": result["invite_url"],
        "qr_svg":     result["qr_svg"],
        "invite_code": result["business"].invite_code,
    })


# ================================================================== #
# Feature 5: client detail, filing summary, Excel export
# ================================================================== #

@clients_bp.route("/<int:client_id>/detail", methods=["GET"])
@jwt_required()
def get_client_detail(client_id: int):
    """
    Full client profile for the CA dashboard detail screen.

    Returns:
      client        — identity + contact + compliance identifiers
      stats         — current-month sales/expenses/net, transaction_count,
                      with_evidence / without_evidence, evidence_breakdown
      compliance_color        — red | yellow | green
      compliance_score        — 0-100 from ComplianceProfile (nullable)
      days_since_last_entry   — int (null if no transactions yet)
      recent_transactions     — last 10 with evidence thumbnail + OCR data

    Edge cases:
      - Client not in this org → 404
      - No transactions yet    → all zeros, empty list, color='red'
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    from modules.dashboard.service import get_client_detail as _detail
    try:
        result = _detail(org_id, client_id)
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("get_client_detail: %s", exc)
        return _err("Failed to fetch client detail.", 500)

    return _ok(result)


@clients_bp.route("/<int:client_id>/filing-summary", methods=["GET"])
@jwt_required()
def get_filing_summary(client_id: int):
    """
    Monthly filing preparation summary for a client.

    Query params:
      month   — YYYY-MM  (default: current month)

    Returns:
      client, period, totals (sales/expenses/net/estimated_tax),
      confidence_breakdown, transactions (all), low_confidence_transactions

    Tax estimate: 18% on sales if GSTIN present, else 0.
    This is indicative only — CA must verify before filing.

    Edge cases:
      - Client not in org    → 404
      - Bad month format     → 400
      - No transactions      → all zeros, empty arrays
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    from datetime import datetime as _dt
    month_str = request.args.get("month") or _dt.utcnow().strftime("%Y-%m")
    try:
        year, month = [int(x) for x in month_str.split("-")]
        if not (1 <= month <= 12) or year < 2000:
            raise ValueError
    except (ValueError, AttributeError):
        return _err("Invalid month format. Use YYYY-MM.", 400)

    from modules.dashboard.service import get_filing_summary as _summary
    try:
        result = _summary(org_id, client_id, year, month)
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("get_filing_summary: %s", exc)
        return _err("Failed to generate filing summary.", 500)

    return _ok(result)


@clients_bp.route("/<int:client_id>/filing-summary/export", methods=["GET"])
@jwt_required()
@limiter.limit("20 per hour")
def export_filing_summary(client_id: int):
    """
    Download the filing summary as an Excel file.

    Query params:
      month   — YYYY-MM  (default: current month)

    Response:
      Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
      Content-Disposition: attachment; filename="<BusinessName>_<Period>_Filing.xlsx"

    Excel structure:
      Sheet 1: Summary     — totals, confidence breakdown, tax estimate
      Sheet 2: All Transactions
      Sheet 3: Low Confidence — Review   ← CA should check these before filing

    Edge cases:
      - Client not in org → 404
      - No transactions   → Excel with zero totals and empty transaction sheets
    """
    from flask import make_response
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    from datetime import datetime as _dt
    month_str = request.args.get("month") or _dt.utcnow().strftime("%Y-%m")
    try:
        year, month = [int(x) for x in month_str.split("-")]
        if not (1 <= month <= 12) or year < 2000:
            raise ValueError
    except (ValueError, AttributeError):
        return _err("Invalid month format. Use YYYY-MM.", 400)

    from modules.dashboard.service import (
        export_filing_excel as _export,
        get_filing_summary  as _summary,
    )
    try:
        # Get client name for the filename
        summary = _summary(org_id, client_id, year, month)
        excel_bytes = _export(org_id, client_id, year, month)
    except ValueError as exc:
        return _err(str(exc), 404)
    except RuntimeError as exc:
        return _err(str(exc), 500)
    except Exception as exc:
        logger.exception("export_filing_summary: %s", exc)
        return _err("Failed to generate Excel export.", 500)

    safe_name = summary["client"]["name"].replace(" ", "_").replace("/", "-")
    filename  = f"{safe_name}_{year:04d}-{month:02d}_Filing.xlsx"

    resp = make_response(excel_bytes)
    resp.headers["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ================================================================== #
# Public invite flow: /invite
# ================================================================== #

@invite_bp.route("/<string:invite_code>", methods=["GET"])
@limiter.limit("30 per minute")
def invite_landing(invite_code: str):
    """
    Public endpoint — returns CA name + client name for the landing page.

    The frontend uses this to show "Priya Nair (CA) has invited you to
    join BharatCompliance" before the client fills in their details.

    Edge cases
    ----------
    - Code not found    → 404
    - Already accepted  → 200 with invite_status='active'
    - Revoked           → 200 with invite_status='revoked'
    """
    try:
        info = service.get_invite_info(invite_code)
    except ValueError as exc:
        return _err(str(exc), 404)

    return _ok({"invite": InviteLandingSchema().dump(info)})


@invite_bp.route("/accept", methods=["POST"])
@limiter.limit("10 per minute")
def invite_accept():
    """
    Client accepts the invite: submits name, phone, PIN.

    On success, an OTP is sent to the client's phone.
    Returns user_id so the client can call /invite/verify-otp.

    Edge cases
    ----------
    - Invalid invite code      → 404
    - Invite already accepted  → 409
    - Invite revoked           → 409
    - Invite expired           → 410
    - Phone already registered → 409
    - Invalid PIN format       → 400
    """
    try:
        data = InviteAcceptSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, business, otp = service.accept_invite(
            invite_code=data["invite_code"],
            name=data["name"],
            phone=data["phone"],
            pin=data["pin"],
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower() or "invalid invite" in msg.lower():
            return _err(msg, 404)
        if "expired" in msg.lower():
            return _err(msg, 410)
        return _err(msg, 409)
    except Exception as exc:
        logger.exception("invite_accept: unexpected error — %s", exc)
        return _err("Failed to process invite.", 500)

    # Send OTP via SMS (non-fatal if it fails)
    sms_sent = send_otp_sms(to_phone=user.phone, otp=otp, name=user.name)
    if not sms_sent:
        logger.warning("invite_accept: OTP SMS failed for user_id=%d", user.id)

    from flask import current_app
    response = {
        "user_id": user.id,
        "message": (
            f"Invite accepted! We've sent a 6-digit code to {user.phone}."
            if sms_sent else
            "Invite accepted! SMS delivery failed — use otp_dev_only below."
        ),
    }
    if current_app.config.get("APP_ENV", "development") != "production":
        response["otp_dev_only"] = otp

    return _ok(response, 201)


@invite_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("10 per minute")
def invite_verify_otp():
    """
    Client verifies phone OTP.

    On success: marks account as verified, sets Business.invite_status='active',
    and returns JWT access + refresh tokens for the client PWA.

    Edge cases
    ----------
    - user_id not found     → 404
    - Already verified      → 400
    - Wrong OTP             → 400 (remaining attempts shown)
    - OTP expired           → 400
    - Too many attempts     → 400
    """
    try:
        data = InviteVerifyOTPSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, business = service.verify_client_otp(
            user_id=data["user_id"],
            otp=data["otp"],
        )
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "not found" in msg.lower() else 400
        return _err(msg, status)
    except Exception as exc:
        logger.exception("invite_verify_otp: unexpected error — %s", exc)
        return _err("Verification failed.", 500)

    # Issue tokens — client tokens have role='client', no org_id
    additional_claims = {
        "role":        user.role,
        "business_id": business.id if business else None,
        "org_id":      business.org_id if business else None,
    }
    access_token  = create_access_token(identity=str(user.id),  additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

    return _ok({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "Bearer",
        "user": {
            "id":          user.id,
            "name":        user.name,
            "phone":       user.phone,
            "role":        user.role,
            "is_verified": user.is_verified,
        },
        "business": {
            "id":            business.id,
            "name":          business.name,
            "invite_status": business.invite_status,
        } if business else None,
    })


# ================================================================== #
# Phase 3: POST /clients/import — Bulk CSV client import
# ================================================================== #

@clients_bp.route("/import", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour")
def import_clients_csv():
    """
    Bulk-create clients from a CSV file.

    Expected CSV columns (header row required):
      name          — required
      business_type — optional (retail/food/services/manufacturing/other)
      state         — optional (Indian state name)
      phone         — optional
      gstin         — optional
      pan           — optional
      expected_turnover — optional (numeric)
      whatsapp_phone — optional

    Returns a summary with created count, skipped rows, and error details.

    Edge cases
    ----------
    - File too large (>500 KB)   → 400
    - Missing 'name' column      → 400
    - Row with duplicate GSTIN   → skipped (error noted)
    - Row with bad phone format  → skipped (error noted)
    - Max 200 rows per upload    → 400 if exceeded
    """
    org_id = _org_id_from_token()
    if not org_id:
        return _err("Token does not contain org_id. Please log in again.", 401)

    if "file" not in request.files:
        return _err("No file uploaded. Send a CSV as 'file' in multipart/form-data.", 400)

    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return _err("Only CSV files are accepted.", 400)

    raw_bytes = f.read(600_000)  # 600 KB hard cap
    if len(raw_bytes) >= 600_000:
        return _err("File too large. Maximum size is 500 KB.", 400)

    try:
        text = raw_bytes.decode("utf-8-sig")  # handle BOM from Excel
    except UnicodeDecodeError:
        return _err("CSV must be UTF-8 encoded.", 400)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return _err("CSV has no headers.", 400)

    headers_lower = [h.strip().lower() for h in reader.fieldnames]
    if "name" not in headers_lower:
        return _err("CSV must contain a 'name' column.", 400)

    rows = list(reader)
    if len(rows) > 200:
        return _err("Maximum 200 rows per import. Split the file and re-upload.", 400)

    created, skipped = [], []

    for i, row in enumerate(rows, start=2):  # row 1 = header
        # Normalise keys
        norm = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
        name = norm.get("name", "")
        if not name:
            skipped.append({"row": i, "reason": "Missing name"})
            continue

        kwargs = {
            "org_id":            org_id,
            "name":              name,
            "business_type":     norm.get("business_type") or None,
            "state":             norm.get("state") or None,
            "phone":             norm.get("phone") or None,
            "gstin":             norm.get("gstin") or None,
            "pan":               norm.get("pan") or None,
            "whatsapp_phone":    norm.get("whatsapp_phone") or None,
            "expected_turnover": None,
        }

        raw_turnover = norm.get("expected_turnover", "")
        if raw_turnover:
            try:
                kwargs["expected_turnover"] = float(raw_turnover.replace(",", ""))
            except ValueError:
                pass  # silently ignore bad turnover

        try:
            result = service.create_client(**kwargs)
            b = result["business"]
            created.append({
                "row":        i,
                "name":       b.name,
                "invite_url": result["invite_url"],
            })
        except ValueError as exc:
            skipped.append({"row": i, "name": name, "reason": str(exc)})
        except Exception as exc:
            logger.exception("import_clients_csv: row %d error — %s", i, exc)
            skipped.append({"row": i, "name": name, "reason": "Server error. Try again."})

    return _ok({
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created":       created,
        "skipped":       skipped,
    }, 201 if created else 200)
