"""
Validation routes — Feature 7.

Blueprint: validation_bp  /validation

Endpoints:
  GET  /validation/clients/<id>/anomalies  — anomaly summary for a client
  POST /validation/check                   — dry-run validation (no transaction created)
"""
import logging
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from modules.validation import service

logger = logging.getLogger(__name__)

validation_bp = Blueprint("validation", __name__)


def _ok(data, status=200):
    return jsonify({"success": True, "data": data, "error": None}), status


def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status


# ------------------------------------------------------------------ #
# GET /validation/clients/<business_id>/anomalies
# ------------------------------------------------------------------ #

@validation_bp.route("/clients/<int:business_id>/anomalies", methods=["GET"])
@jwt_required()
def client_anomalies(business_id):
    """
    Anomaly summary for a client: gap days, outliers, duplicates.

    Access: CA only (same org)
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id.", 401)

    # Verify business belongs to org
    from modules.businesses.models import Business
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        return _err("Client not found in your organization.", 404)

    result = service.get_anomaly_summary(business_id)
    result["client_name"] = biz.name
    return _ok(result)


# ------------------------------------------------------------------ #
# POST /validation/check
# ------------------------------------------------------------------ #

@validation_bp.route("/check", methods=["POST"])
@jwt_required()
def check_transaction():
    """
    Dry-run validation — returns warnings without creating a transaction.

    Body:
      amount           — float (required)
      type             — 'sale' | 'expense' (required)
      transaction_date — YYYY-MM-DD (optional, defaults to today)

    Access: Client (own business) or CA

    Response:
      warnings: [{rule, message, severity, details?}]
      valid: true if no high-severity warnings
    """
    claims = get_jwt()
    role = claims.get("role")

    if role == "client":
        business_id = claims.get("business_id")
        if not business_id:
            return _err("Token missing business_id.", 401)
    else:
        body = request.get_json(silent=True) or {}
        business_id = body.get("business_id")
        if not business_id:
            return _err("business_id is required for CA users.", 400)

    body = request.get_json(silent=True) or {}
    amount = body.get("amount")
    tx_type = body.get("type")
    tx_date_str = body.get("transaction_date")

    if amount is None:
        return _err("amount is required.", 400)
    if tx_type not in ("sale", "expense"):
        return _err("type must be 'sale' or 'expense'.", 400)

    try:
        amount = float(str(amount).replace(",", ""))
    except (ValueError, TypeError):
        return _err("amount must be a number.", 400)

    tx_date = None
    if tx_date_str:
        try:
            tx_date = date.fromisoformat(tx_date_str)
        except ValueError:
            return _err("Invalid date format. Use YYYY-MM-DD.", 400)

    warnings = service.validate_transaction(business_id, amount, tx_type, tx_date)

    has_high = any(w["severity"] == "high" for w in warnings)

    return _ok({
        "warnings": warnings,
        "warning_count": len(warnings),
        "valid": not has_high,
    })
