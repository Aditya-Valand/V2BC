from core.extensions import db
from datetime import datetime


class BusinessEvidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id  = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False)
    statement_id = db.Column(db.Integer, db.ForeignKey("business_statement.id"), nullable=True)
    uploaded_by  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # ── File ─────────────────────────────────────────────────── #
    file_name    = db.Column(db.String(255))
    file_path    = db.Column(db.String(500))       # local path (needed for OCR)
    file_url     = db.Column(db.Text)              # Cloudinary CDN URL (or same as file_path in dev)
    thumbnail_url= db.Column(db.Text)              # Cloudinary thumbnail URL
    cloudinary_public_id = db.Column(db.String(255))
    file_type    = db.Column(db.String(50))        # image/jpeg, image/png, application/pdf
    file_size_bytes = db.Column(db.Integer)

    evidence_type = db.Column(db.String(50))
    # invoice, receipt, bill, handwritten, upi_screenshot, unknown

    source = db.Column(db.String(30))              # whatsapp, web, client_app

    # ── Quality ──────────────────────────────────────────────── #
    quality_score  = db.Column(db.Float)           # 0–∞ Laplacian score
    quality_status = db.Column(db.String(20))      # usable, low_quality, rejected
    status         = db.Column(db.String(30), default="uploaded")
    # uploaded, usable, needs_review, error

    # ── Evidence strength ────────────────────────────────────── #
    evidence_strength = db.Column(db.String(20), default="weak")
    # weak, medium, strong

    # ── OCR ──────────────────────────────────────────────────── #
    ocr_status    = db.Column(db.String(20), default="pending")
    # pending, processing, success, failed, skipped, rejected

    ocr_text      = db.Column(db.Text)             # raw OCR response
    detected_amount = db.Column(db.Float)
    detected_date   = db.Column(db.DateTime)
    detected_gstin  = db.Column(db.String(20))
    ocr_vendor_name = db.Column(db.String(150))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
