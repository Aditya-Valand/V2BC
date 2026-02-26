"""
Evidence service — Feature 4.

Storage:
  Primary   — Cloudinary (CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME + keys in env)
  Fallback  — local instance/uploads/<business_id>/

OCR:
  Primary   — Gemini Vision (GOOGLE_API_KEY in env)
  Fallback  — mock data (dev mode when key absent)

All OCR runs in a daemon background thread after the HTTP response is returned.
"""
import logging
import os
import threading
import uuid
from typing import Optional

from flask import current_app
from werkzeug.utils import secure_filename

from core.extensions import db
from modules.businesses.models import Business
from modules.evidence.models import BusinessEvidence
from modules.evidence.quality import image_quality_score, quality_status

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf", "webp"}
MAX_FILE_BYTES      = 10 * 1024 * 1024   # 10 MB


# ------------------------------------------------------------------ #
# File validation
# ------------------------------------------------------------------ #

def validate_file(file) -> None:
    """Raise ValueError with user-facing message on any problem."""
    if not file or not file.filename:
        raise ValueError("No file provided.")

    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only JPG, PNG, PDF, WebP files are allowed.")

    # Check size by seeking to end
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_BYTES:
        raise ValueError("File too large. Maximum size is 10 MB.")


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


# ------------------------------------------------------------------ #
# Storage
# ------------------------------------------------------------------ #

def _cloudinary_upload(file_path: str, business_id: int) -> Optional[dict]:
    """
    Upload file to Cloudinary.  Returns dict with url, public_id, thumbnail_url.
    Returns None if Cloudinary not configured or upload fails.
    """
    try:
        import cloudinary
        import cloudinary.uploader

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key    = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        # Also support CLOUDINARY_URL which encodes all three
        cloudinary_url = os.getenv("CLOUDINARY_URL")
        if not cloudinary_url and not (cloud_name and api_key and api_secret):
            return None

        if cloudinary_url:
            cloudinary.config(cloudinary_url=cloudinary_url)
        else:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
            )

        folder  = f"bharatcompliance/{business_id}"
        pub_id  = f"{folder}/{uuid.uuid4().hex}"

        result = cloudinary.uploader.upload(
            file_path,
            public_id=pub_id,
            folder=None,        # already in public_id
            resource_type="auto",
            quality="auto:good",
            fetch_format="auto",
        )

        # Build thumbnail URL using Cloudinary transformation
        secure_url    = result.get("secure_url", "")
        thumbnail_url = _cloudinary_thumb(secure_url)

        return {
            "url":          secure_url,
            "thumbnail_url": thumbnail_url,
            "public_id":   result.get("public_id"),
        }

    except ImportError:
        logger.info("cloudinary package not installed — using local storage")
        return None
    except Exception as exc:
        logger.warning("Cloudinary upload failed: %s — using local storage", exc)
        return None


def _cloudinary_thumb(url: str) -> str:
    """Insert Cloudinary transformation for a 300×300 thumbnail."""
    if not url:
        return url
    # Insert /w_300,h_300,c_fill/ before the version or upload segment
    parts = url.split("/upload/", 1)
    if len(parts) == 2:
        return f"{parts[0]}/upload/w_300,h_300,c_fill/{parts[1]}"
    return url


def _local_save(file, business_id: int) -> tuple[str, str]:
    """Save file locally. Returns (file_path, original_name)."""
    base = os.path.join(current_app.instance_path, "uploads", str(business_id))
    os.makedirs(base, exist_ok=True)
    original  = secure_filename(file.filename or "upload.jpg")
    unique    = f"{uuid.uuid4().hex}_{original}"
    dest      = os.path.join(base, unique)
    file.save(dest)
    return dest, original


# ------------------------------------------------------------------ #
# Core upload function
# ------------------------------------------------------------------ #

def upload_evidence(
    file,
    business_id: int,
    uploaded_by_user_id: int,
    statement_id: Optional[int] = None,
    source: str = "web",
) -> BusinessEvidence:
    """
    1. Validate file
    2. Save locally (always — needed for OCR)
    3. Try Cloudinary upload
    4. Quality-check
    5. Create BusinessEvidence record (ocr_status='pending')
    6. Spawn background OCR thread
    Returns the committed BusinessEvidence.
    """
    validate_file(file)

    # 1. Local save first (OCR reads local file)
    file_path, original_name = _local_save(file, business_id)

    # 2. Quality check
    q_score  = image_quality_score(file_path)
    q_status = quality_status(q_score)

    # 3. Cloudinary upload attempt
    cdn_result    = _cloudinary_upload(file_path, business_id)
    file_url      = cdn_result["url"]          if cdn_result else file_path
    thumbnail_url = cdn_result["thumbnail_url"] if cdn_result else None
    cdn_public_id = cdn_result["public_id"]    if cdn_result else None

    # 4. Determine file type
    ext = _ext(original_name)
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png",  "pdf": "application/pdf",
                "webp": "image/webp"}
    file_type = mime_map.get(ext, "application/octet-stream")

    # 5. File size
    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        file_size = None

    ev = BusinessEvidence(
        business_id      = business_id,
        statement_id     = statement_id,
        file_name        = original_name,
        file_path        = file_path,
        file_url         = file_url,
        thumbnail_url    = thumbnail_url,
        cloudinary_public_id = cdn_public_id,
        file_type        = file_type,
        file_size_bytes  = file_size,
        source           = source,
        quality_score    = q_score,
        quality_status   = q_status,
        ocr_status       = "rejected" if q_status == "rejected" else "pending",
        status           = "uploaded",
        evidence_strength= "weak",    # will be updated by OCR
        evidence_type    = "unknown",
        uploaded_by      = uploaded_by_user_id,
    )
    db.session.add(ev)
    db.session.commit()

    # 6. Spawn OCR thread (unless quality too poor)
    if ev.ocr_status == "pending":
        _spawn_ocr(ev.id, current_app._get_current_object())

    logger.info(
        "Evidence uploaded: id=%d business_id=%d quality=%.1f status=%s cloudinary=%s",
        ev.id, business_id, q_score, q_status, bool(cdn_result)
    )
    return ev


def _spawn_ocr(evidence_id: int, app):
    """Run OCR in a background daemon thread."""
    def _run():
        with app.app_context():
            try:
                from modules.ocr.service import run_ocr
                ev = BusinessEvidence.query.get(evidence_id)
                if not ev:
                    return
                ev.ocr_status = "processing"
                db.session.commit()
                run_ocr(ev)
                ev.ocr_status = "success" if ev.status != "error" else "failed"
                db.session.commit()
            except Exception as exc:
                logger.exception("Background OCR failed (evidence_id=%d): %s", evidence_id, exc)
                try:
                    ev = BusinessEvidence.query.get(evidence_id)
                    if ev:
                        ev.ocr_status = "failed"
                        db.session.commit()
                except Exception:
                    db.session.rollback()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ------------------------------------------------------------------ #
# Read helpers
# ------------------------------------------------------------------ #

def get_evidence(evidence_id: int, user_id: int, user_role: str,
                 user_business_id: Optional[int] = None,
                 user_org_id: Optional[int] = None) -> BusinessEvidence:
    """
    Fetch evidence with access control.
    Raises ValueError on not found or permission denied.
    """
    ev = BusinessEvidence.query.get(evidence_id)
    if not ev:
        raise ValueError("Evidence not found.")

    if user_role == "client":
        if ev.business_id != user_business_id:
            raise ValueError("Access denied.")
    else:
        # CA — verify same org
        biz = Business.query.get(ev.business_id)
        if not biz or biz.org_id != user_org_id:
            raise ValueError("Access denied.")

    return ev


def list_client_evidence(
    business_id: int,
    org_id: int,
    strength: Optional[str] = None,
    ocr_status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """
    Return paginated evidence for a client (CA-only endpoint).
    Verifies client belongs to org_id.
    """
    biz = Business.query.filter_by(id=business_id, org_id=org_id).first()
    if not biz:
        raise ValueError("Client not found or access denied.")

    q = BusinessEvidence.query.filter_by(business_id=business_id)
    if strength:
        q = q.filter_by(evidence_strength=strength)
    if ocr_status:
        q = q.filter_by(ocr_status=ocr_status)

    q = q.order_by(BusinessEvidence.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "evidence": [_ev_dict(ev) for ev in items],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
    }


def _ev_dict(ev: BusinessEvidence) -> dict:
    return {
        "id":               ev.id,
        "business_id":      ev.business_id,
        "statement_id":     ev.statement_id,
        "file_url":         ev.file_url,
        "thumbnail_url":    ev.thumbnail_url,
        "file_type":        ev.file_type,
        "file_size_bytes":  ev.file_size_bytes,
        "quality_score":    ev.quality_score,
        "quality_status":   ev.quality_status,
        "ocr_status":       ev.ocr_status,
        "ocr_amount":       ev.detected_amount,
        "ocr_date":         ev.detected_date.date().isoformat() if ev.detected_date else None,
        "ocr_gstin":        ev.detected_gstin,
        "ocr_vendor_name":  ev.ocr_vendor_name,
        "ocr_document_type": ev.evidence_type,
        "strength":         ev.evidence_strength,
        "source":           ev.source,
        "created_at":       ev.created_at.isoformat(),
    }
