"""
Evidence routes — Feature 4.

Blueprints
----------
evidence_bp  /evidence

POST   /evidence/upload           — client or CA uploads file → 202
GET    /evidence/:id              — poll OCR result (client own, or CA same org)
GET    /clients/:id/evidence      — CA views all evidence for a client

Auth
----
All routes require JWT.
Client role  → can upload/read their own evidence (business_id from JWT).
CA role      → can upload for any client in their org; can read/list.
"""
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from core.extensions import limiter
from modules.evidence import service

logger = logging.getLogger(__name__)

evidence_bp = Blueprint("evidence", __name__)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _ok(data, status=200):
    return jsonify({"success": True,  "data": data,  "error": None}), status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None,  "error": msg}),  status

def _claims():
    claims = get_jwt()
    return {
        "user_id":     int(get_jwt_identity()),
        "role":        claims.get("role"),
        "org_id":      claims.get("org_id"),
        "business_id": claims.get("business_id"),
    }


# ------------------------------------------------------------------ #
# POST /evidence/upload
# ------------------------------------------------------------------ #

@evidence_bp.route("/upload", methods=["POST"])
@jwt_required()
@limiter.limit("100 per day; 20 per hour")
def upload_evidence():
    """
    Upload a bill/receipt photo.

    Content-Type: multipart/form-data
    Fields:
      file          — required, image/jpeg|png|pdf|webp, max 10MB
      statement_id  — optional int, links evidence to a transaction

    For CA users:
      business_id   — required int, which client this evidence belongs to

    Returns 202 (OCR running in background).
    Response:
      evidence_id, file_url, thumbnail_url, quality_score,
      quality_status, ocr_status, message
    """
    c = _claims()
    file = request.files.get("file")

    # Determine business_id
    if c["role"] == "client":
        business_id = c["business_id"]
        if not business_id:
            return _err("Token missing business_id. Please log in again.", 401)
    else:
        # CA — must supply business_id in form
        raw_bid = request.form.get("business_id")
        if not raw_bid:
            return _err("business_id is required.", 400)
        try:
            business_id = int(raw_bid)
        except (TypeError, ValueError):
            return _err("business_id must be an integer.", 400)

    # statement_id (optional)
    statement_id = None
    raw_sid = request.form.get("statement_id")
    if raw_sid:
        try:
            statement_id = int(raw_sid)
        except (TypeError, ValueError):
            return _err("statement_id must be an integer.", 400)

    try:
        service.validate_file(file)
    except ValueError as exc:
        return _err(str(exc), 400)

    try:
        ev = service.upload_evidence(
            file              = file,
            business_id       = business_id,
            uploaded_by_user_id = c["user_id"],
            statement_id      = statement_id,
            source            = "client_app" if c["role"] == "client" else "ca_web",
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:
        logger.exception("upload_evidence route: %s", exc)
        return _err("Failed to upload file.", 500)

    quality_warn = None
    if ev.quality_status == "rejected":
        quality_warn = "Photo is too blurry to process. Please retake with better lighting."
    elif ev.quality_status == "low_quality":
        quality_warn = "Photo quality is low. Results may be less accurate."

    return _ok({
        "evidence_id":    ev.id,
        "file_url":       ev.file_url,
        "thumbnail_url":  ev.thumbnail_url,
        "quality_score":  round(ev.quality_score or 0, 1),
        "quality_status": ev.quality_status,
        "ocr_status":     ev.ocr_status,
        "quality_warning": quality_warn,
        "message": (
            "Photo saved. Scanning for details..."
            if ev.ocr_status == "pending"
            else "Photo saved. Image quality too poor for scanning."
        ),
    }, 202)


# ------------------------------------------------------------------ #
# GET /evidence/:id  — poll for OCR result
# ------------------------------------------------------------------ #

@evidence_bp.route("/<int:evidence_id>", methods=["GET"])
@jwt_required()
def get_evidence(evidence_id: int):
    """
    Retrieve evidence record with OCR results.
    Client polls this after upload to learn when OCR completes.

    Access: client (own evidence) or CA (same org's client).
    """
    c = _claims()

    try:
        ev = service.get_evidence(
            evidence_id     = evidence_id,
            user_id         = c["user_id"],
            user_role       = c["role"],
            user_business_id= c["business_id"],
            user_org_id     = c["org_id"],
        )
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("get_evidence: %s", exc)
        return _err("Failed to fetch evidence.", 500)

    return _ok(service._ev_dict(ev))


# ------------------------------------------------------------------ #
# GET /clients/:id/evidence  — CA lists client's evidence
# ------------------------------------------------------------------ #

@evidence_bp.route("/clients/<int:business_id>", methods=["GET"])
@jwt_required()
def list_client_evidence(business_id: int):
    """
    List all evidence for a client (CA-only).

    Query params:
      strength    — weak | medium | strong
      ocr_status  — pending | processing | success | failed
      page        — int (default 1)
      per_page    — int (default 20, max 50)
    """
    c = _claims()
    if c["role"] not in ("ca_owner", "ca_staff", "owner", "member"):
        # any non-client role is fine; tighter check below via org_id
        if c["role"] == "client":
            return _err("CA access only.", 403)

    if not c["org_id"]:
        return _err("Token missing org_id. Please log in again.", 401)

    strength   = request.args.get("strength")
    ocr_status = request.args.get("ocr_status")
    page       = max(1, int(request.args.get("page", 1) or 1))
    per_page   = min(50, max(1, int(request.args.get("per_page", 20) or 20)))

    if strength and strength not in ("weak", "medium", "strong"):
        return _err("strength must be weak, medium, or strong.", 400)

    try:
        result = service.list_client_evidence(
            business_id = business_id,
            org_id      = c["org_id"],
            strength    = strength,
            ocr_status  = ocr_status,
            page        = page,
            per_page    = per_page,
        )
    except ValueError as exc:
        return _err(str(exc), 404)
    except Exception as exc:
        logger.exception("list_client_evidence: %s", exc)
        return _err("Failed to fetch evidence.", 500)

    return _ok(result)
