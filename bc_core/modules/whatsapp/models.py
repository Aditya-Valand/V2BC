from core.extensions import db
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    """WhatsApp message types"""
    TEXT = 'text'
    IMAGE = 'image'
    DOCUMENT = 'document'
    AUDIO = 'audio'
    VIDEO = 'video'

class MessageStatus(Enum):
    """WhatsApp message processing status"""
    RECEIVED = 'received'          # Just received from WhatsApp
    PARSED = 'parsed'              # Parsed for content
    STATEMENT_CREATED = 'statement_created'  # Statement record created
    EVIDENCE_PROCESSING = 'evidence_processing'  # Media being processed
    EVIDENCE_COMPLETED = 'evidence_completed'    # Media processing done
    ERROR = 'error'                # Error processing
    SKIPPED = 'skipped'            # No actionable content

class WhatsAppMessage(db.Model):
    """WhatsApp message model with full lifecycle tracking"""
    __tablename__ = 'whats_app_message'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Message identification
    whatsapp_message_id = db.Column(db.String(100), unique=True, nullable=False)  # WhatsApp's message ID
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    sender_phone = db.Column(db.String(50), nullable=False)  # Full phone number with country code
    
    # Message content
    message_type = db.Column(db.String(20), default='text')  # text, image, document, etc
    raw_text = db.Column(db.Text)  # Original text content
    parsed_text = db.Column(db.Text)  # Cleaned/normalized text
    
    # Media handling
    media_url = db.Column(db.String(500))  # WhatsApp media URL
    media_local_path = db.Column(db.String(500))  # Local download path if saved
    media_mime_type = db.Column(db.String(100))  # image/jpeg, application/pdf, etc
    
    # Parsing results
    extracted_amount = db.Column(db.Float)  # Extracted financial amount
    extracted_date = db.Column(db.DateTime)  # Extracted transaction date
    extracted_type = db.Column(db.String(50))  # Transaction type (sale, expense, etc)
    confidence_score = db.Column(db.Float, default=0.0)  # Parsing confidence (0-1)
    
    # Processing status
    status = db.Column(db.String(30), default='received')  # received, parsed, statement_created, etc
    processing_error = db.Column(db.Text)  # Error message if processing failed
    
    # Links to created records
    statement_id = db.Column(db.Integer, db.ForeignKey('business_statement.id'))  # Link to created statement
    evidence_id = db.Column(db.Integer, db.ForeignKey('business_evidence.id'))  # Link to created evidence
    
    # Webhook data
    webhook_data = db.Column(db.JSON)  # Raw webhook message data
    processed_at = db.Column(db.DateTime)  # When processing completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<WhatsAppMessage {self.whatsapp_message_id} from {self.sender_phone}>"
    
    def mark_processed(self, status, statement_id=None, evidence_id=None, error=None):
        """Mark message as processed"""
        self.status = status
        self.statement_id = statement_id
        self.evidence_id = evidence_id
        self.processing_error = error
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
