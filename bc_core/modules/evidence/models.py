from core.extensions import db
from datetime import datetime

class BusinessEvidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(db.Integer, db.ForeignKey("business.id"))
    statement_id = db.Column(db.Integer, db.ForeignKey("business_statement.id"), nullable=True)

    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))

    evidence_type = db.Column(db.String(50))  
    # bill, handwritten, upi, bank, notice, unknown

    source = db.Column(db.String(30))  # whatsapp, web

    quality_score = db.Column(db.Float)
    status = db.Column(db.String(30), default="uploaded")
    # uploaded, weak, needs_review, usable

    evidence_strength = db.Column(db.String(20), default="weak")
    # weak: blurry/illegible, medium: some OCR data, strong: clear with GSTIN/amount

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ocr_text = db.Column(db.Text)
    detected_amount = db.Column(db.Float)
    detected_date = db.Column(db.DateTime)
    detected_gstin = db.Column(db.String(20))
