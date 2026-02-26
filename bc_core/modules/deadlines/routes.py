"""
Deadlines routes — Feature 6.

Blueprint: deadlines_bp  /deadlines

Endpoints:
  GET  /deadlines/clients/<id>     — all deadlines for a client
  GET  /deadlines/upcoming         — CA view: next 30 days across all clients
  POST /deadlines/<id>/complete    — CA marks deadline as filed
  POST /deadlines/<id>/acknowledge — Client acknowledges a reminder
  POST /deadlines/generate/<id>    — Generate/refresh deadlines for a client
"""
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from core.extensions import limiter
from modules.deadlines import service

logger = logging.getLogger(__name__)

deadlines_bp = Blueprint("deadlines", __name__)


def _ok(data, status=200):
    return jsonify({"success": True, "data": data, "error": None}), status


def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status


# ------------------------------------------------------------------ #
# GET /deadlines/clients/<business_id>
# ------------------------------------------------------------------ #

@deadlines_bp.route("/clients/<int:business_id>", methods=["GET"])
@jwt_required()
def client_deadlines(business_id):
    """
    All deadlines for a client.

    Query params:
      status — filter by status (pending, reminded, acknowledged, completed, missed)

    Access: CA (same org) or Client (own business)
    """
    claims = get_jwt()
    role = claims.get("role")

    # Resolve org_id for access control
    if role == "client":
        biz_id = claims.get("business_id")
        if biz_id != business_id:
            return _err("You can only view your own deadlines.", 403)
        org_id = claims.get("org_id")
        if not org_id:
            # Client may not have org_id in claims — look it up
            from modules.businesses.models import Business
            biz = Business.query.get(business_id)
            org_id = biz.org_id if biz else None
    else:
        org_id = claims.get("org_id")
        if not org_id:
            return _err("Token missing org_id. Please log in again.", 401)

    status_filter = request.args.get("status")

    try:
        result = service.get_client_deadlines(org_id, business_id, status_filter)
    except ValueError as exc:
        return _err(str(exc), 404)

    return _ok(result)


# ------------------------------------------------------------------ #
# GET /deadlines/upcoming
# ------------------------------------------------------------------ #

@deadlines_bp.route("/upcoming", methods=["GET"])
@jwt_required()
def upcoming_deadlines():
    """
    CA view: all client deadlines in next N days.

    Query params:
      days — lookahead window (default 30, max 90)

    Access: CA only
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id. Please log in again.", 401)

    days = request.args.get("days", 30, type=int)
    if days < 1:
        days = 1
    if days > 90:
        days = 90

    result = service.get_upcoming_deadlines(org_id, days)
    return _ok(result)


# ------------------------------------------------------------------ #
# POST /deadlines/<id>/complete
# ------------------------------------------------------------------ #

@deadlines_bp.route("/<int:deadline_id>/complete", methods=["POST"])
@jwt_required()
def complete_deadline(deadline_id):
    """
    CA marks a deadline as completed (filed).

    Body (optional):
      notes — free text note about the filing

    Access: CA only (same org)
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id. Please log in again.", 401)

    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    notes = body.get("notes", "").strip() or None

    try:
        result = service.complete_deadline(deadline_id, user_id, org_id, notes)
    except ValueError as exc:
        return _err(str(exc), 400)
    except PermissionError as exc:
        return _err(str(exc), 403)

    return _ok(result)


# ------------------------------------------------------------------ #
# POST /deadlines/<id>/acknowledge
# ------------------------------------------------------------------ #

@deadlines_bp.route("/<int:deadline_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_deadline(deadline_id):
    """
    Client acknowledges a reminder ("Got it").

    Access: Client (own deadline) or CA (any in org)
    """
    claims = get_jwt()
    user_id = get_jwt_identity()

    business_id = None
    if claims.get("role") == "client":
        business_id = claims.get("business_id")

    try:
        result = service.acknowledge_deadline(deadline_id, user_id, business_id)
    except ValueError as exc:
        return _err(str(exc), 400)
    except PermissionError as exc:
        return _err(str(exc), 403)

    return _ok(result)


# ------------------------------------------------------------------ #
# POST /deadlines/generate/<business_id>
# ------------------------------------------------------------------ #

@deadlines_bp.route("/generate/<int:business_id>", methods=["POST"])
@jwt_required()
def generate_deadlines(business_id):
    """
    Generate (or refresh) next 12 months of deadlines for a client.

    Skips duplicates, safe to call multiple times.

    Access: CA only (same org)
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id. Please log in again.", 401)

    # Verify business belongs to org
    from modules.businesses.models import Business
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        return _err("Client not found in your organization.", 404)

    try:
        count = service.generate_deadlines(business_id, org_id)
    except ValueError as exc:
        return _err(str(exc), 400)

    return _ok({
        "client_id": business_id,
        "deadlines_created": count,
        "message": f"Generated {count} new deadline(s)." if count else "All deadlines already exist.",
    }, 201 if count else 200)
