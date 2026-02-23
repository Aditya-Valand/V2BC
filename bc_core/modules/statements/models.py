from core.extensions import db
from datetime import datetime

class BusinessStatement(db.Model):
    __tablename__ = 'business_statement'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False)
    whatsapp_message_id = db.Column(db.Integer, db.ForeignKey("whats_app_message.id"), nullable=True)

    statement_type = db.Column(db.String(50))  
    # daily_sales, expense, purchase, unknown

    raw_text = db.Column(db.Text)
    amount = db.Column(db.Float)
    currency = db.Column(db.String(10), default="INR")
    transaction_date = db.Column(db.DateTime)  # When the transaction occurred

    source = db.Column(db.String(30))  # whatsapp, web, api, etc
    confidence_level = db.Column(db.String(20), default="low")  # low, medium, high
    confidence_reason = db.Column(db.Text)  # Why this confidence level
    description = db.Column(db.Text)  # Human-readable description
    
    # Metadata
    verified = db.Column(db.Boolean, default=False)  # CA verified this statement
    verified_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # Which user verified
    verified_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BusinessStatement {self.id} - {self.amount} {self.currency}>"
