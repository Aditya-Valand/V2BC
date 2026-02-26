"""
Reminders routes — Features 5 & 6.

Blueprint: reminders_bp  /reminders

POST /reminders/send       — CA sends push notification to one or all active clients
POST /reminders/send-bulk  — CA triggers deadline-aware bulk reminders (Feature 6)
"""
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from core.extensions import limiter
from modules.reminders import service

logger = logging.getLogger(__name__)

reminders_bp = Blueprint("reminders", __name__)


def _ok(data, status=200):
    return jsonify({"success": True, "data": data, "error": None}), status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status


# ------------------------------------------------------------------ #
# POST /reminders/send
# ------------------------------------------------------------------ #

@reminders_bp.route("/send", methods=["POST"])
@jwt_required()
@limiter.limit("30 per hour; 200 per day")
def send_reminders():
    """
    Send push notification to selected clients.

    Request body (JSON):
      client_ids  — list of int business IDs, or the string "all"
      message     — notification body (required, max 500 chars)
      type        — one of: deadline, general, missing, urgent  (default: general)

    Response 200:
      sent, failed, skipped, total, details

    Edge cases:
      - client_ids empty list → 400
      - message empty         → 400
      - client_ids > 500      → 400
      - Not a CA              → 403
      - Client has no FCM token → listed as "no_token" in details (not 4xx)
      - Client hasn't joined yet → listed as "skipped"
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id. Please log in again.", 401)

    body = request.get_json(silent=True) or {}

    client_ids    = body.get("client_ids")
    message       = body.get("message", "").strip()
    reminder_type = body.get("type", "general")

    # Validate
    if not message:
        return _err("message is required.", 400)
    if len(message) > 500:
        return _err("message must be 500 characters or fewer.", 400)
    if client_ids is None:
        return _err("client_ids is required (list of IDs or 'all').", 400)
    if isinstance(client_ids, str) and client_ids != "all":
        return _err("client_ids must be a list of integers or the string 'all'.", 400)
    if isinstance(client_ids, list):
        if len(client_ids) == 0:
            return _err("client_ids cannot be empty.", 400)
        if not all(isinstance(x, int) for x in client_ids):
            return _err("All client_ids must be integers.", 400)

    try:
        result = service.send_reminders(
            org_id        = org_id,
            client_ids    = client_ids,
            message       = message,
            reminder_type = reminder_type,
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:
        logger.exception("send_reminders: %s", exc)
        return _err("Failed to send reminders.", 500)

    return _ok(result)


# ------------------------------------------------------------------ #
# POST /reminders/send-bulk   (Feature 6)
# ------------------------------------------------------------------ #

@reminders_bp.route("/send-bulk", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour; 100 per day")
def send_bulk_reminders():
    """
    CA triggers deadline-aware bulk push reminders.

    Request body (JSON):
      client_ids     — list of int business IDs, or "all"
      message        — notification body (required, max 500 chars)
      deadline_type  — optional: gstr1_monthly, gstr3b, etc. to target specific filing

    Response 200:
      sent, failed, skipped, total, details

    Edge cases:
      - Same validation as /send
      - If deadline_type given, includes deadline info in push body
      - Marks targeted deadlines as "reminded"
    """
    claims = get_jwt()
    if claims.get("role") == "client":
        return _err("CA access only.", 403)

    org_id = claims.get("org_id")
    if not org_id:
        return _err("Token missing org_id. Please log in again.", 401)

    body = request.get_json(silent=True) or {}

    client_ids    = body.get("client_ids")
    message       = body.get("message", "").strip()
    deadline_type = body.get("deadline_type")

    # Validate
    if not message:
        return _err("message is required.", 400)
    if len(message) > 500:
        return _err("message must be 500 characters or fewer.", 400)
    if client_ids is None:
        return _err("client_ids is required (list of IDs or 'all').", 400)
    if isinstance(client_ids, str) and client_ids != "all":
        return _err("client_ids must be a list of integers or the string 'all'.", 400)
    if isinstance(client_ids, list):
        if len(client_ids) == 0:
            return _err("client_ids cannot be empty.", 400)
        if not all(isinstance(x, int) for x in client_ids):
            return _err("All client_ids must be integers.", 400)

    from modules.deadlines.service import send_bulk_reminders as _bulk

    try:
        result = _bulk(
            org_id=org_id,
            client_ids=client_ids,
            message=message,
            deadline_type=deadline_type,
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:
        logger.exception("send_bulk_reminders: %s", exc)
        return _err("Failed to send bulk reminders.", 500)

    return _ok(result)
