"""
Dashboard routes — Feature 5.

Blueprint: dashboard_bp  /dashboard

GET /dashboard   — org overview: stats + client health + recent alerts
"""
import logging

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, jwt_required

from modules.dashboard import service

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


def _ok(data, status=200):
    return jsonify({"success": True, "data": data, "error": None}), status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status

def _require_ca_org():
    """Return org_id from JWT, or None if not a CA."""
    claims = get_jwt()
    if claims.get("role") == "client":
        return None
    return claims.get("org_id")


# ------------------------------------------------------------------ #
# GET /dashboard
# ------------------------------------------------------------------ #

@dashboard_bp.route("", methods=["GET"])
@jwt_required()
def get_dashboard():
    """
    Org-level summary for the CA dashboard landing page.

    Response:
      org_name
      stats: total_clients, active_clients, invited_not_joined,
             red_clients, yellow_clients, green_clients, unread_alerts
      clients: list sorted by urgency (red first), each with:
               id, name, business_type, compliance_color, compliance_score,
               days_since_last_entry, last_transaction_at, transactions_this_month
      recent_alerts: last 10 open alerts

    Edge cases:
      - No clients → all zeros, empty lists
      - No transactions ever → all clients are red
      - Not a CA → 403
    """
    org_id = _require_ca_org()
    if not org_id:
        return _err("CA access only.", 403)

    try:
        result = service.get_dashboard(org_id)
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("get_dashboard: %s", exc)
        return _err("Failed to load dashboard.", 500)

    return _ok(result)
