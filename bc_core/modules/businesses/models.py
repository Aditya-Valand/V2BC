from core.extensions import db
from datetime import datetime

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    
    # NEW: Link to micro-business owner user
    owner_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    
    # NEW: WhatsApp phone number (PRIMARY identifier for webhook routing)
    whatsapp_phone = db.Column(db.String(20), unique=True, nullable=True)
    
    name = db.Column(db.String(150))
    business_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    expected_turnover = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
