from core.extensions import db
from modules.whatsapp.models import WhatsAppMessage, MessageStatus
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.statements.parser import parse_statement_text
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def find_business_by_phone(sender_phone: str):
    """
    Find business by WhatsApp sender phone number.
    Handles phone number formatting variations.
    """
    if not sender_phone:
        return None
    
    # Try exact match
    business = Business.query.filter_by(whatsapp_phone=sender_phone).first()
    if business:
        return business
    
    # Try matching without country code
    if sender_phone.startswith('+91'):
        phone_without_cc = sender_phone[3:]  # Remove +91
        business = Business.query.filter_by(whatsapp_phone=phone_without_cc).first()
        if business:
            return business
    
    # Try matching with country code added
    business = Business.query.filter_by(whatsapp_phone=f'+91{sender_phone}').first()
    if business:
        return business
    
    return None


def extract_amount_from_text(text: str):
    """
    Extract financial amount from message text.
    Handles various formats: 1000, 1,000, ₹1000, Rs 1000, etc
    """
    if not text:
        return None, 0.0
    
    parsed = parse_statement_text(text)
    return parsed.get('amount'), parsed.get('confidence', 0.0) if parsed.get('amount') else 0.0


def save_message(payload):
    """Save a WhatsApp message to the database"""
    msg = WhatsAppMessage(
        business_id=payload.get("business_id"),
        sender_phone=payload.get("from"),
        message_type=payload.get("type"),
        raw_text=payload.get("text"),
        media_url=payload.get("media_url"),
        whatsapp_message_id=payload.get("message_id")
    )
    db.session.add(msg)
    db.session.commit()
    return msg


def process_webhook_message(message, webhook_context):
    """
    Process an incoming WhatsApp message from webhook.
    
    Complete pipeline:
    1. Validate and extract message info
    2. Find associated business
    3. Save message record
    4. Parse text for financial data
    5. Create statement if amount found
    6. Download and process media if present
    
    Args:
        message: Message object from WhatsApp webhook
        webhook_context: Context from webhook (contacts, statuses, etc)
        
    Returns:
        {'success': bool, 'message_id': int, 'business_id': int, 'statement_id': int or None, 'error': str}
    """
    try:
        # Step 1: Extract message info
        sender_phone = message.get('from')
        message_id = message.get('id')
        message_type = message.get('type', 'text')
        timestamp = int(message.get('timestamp', 0))
        
        if not sender_phone or not message_id:
            return {'success': False, 'error': 'Missing required message fields'}
        
        # Step 2: Find business by phone
        business = find_business_by_phone(sender_phone)
        if not business:
            logger.warning(f"No business found for phone {sender_phone}")
            return {'success': False, 'error': f'No business found for phone {sender_phone}'}
        
        # Step 3: Extract content based on message type
        text_content = None
        media_url = None
        media_mime = None
        confidence = 0.0
        
        if message_type == 'text':
            text_content = message.get('text', {}).get('body', '')
        elif message_type == 'document':
            doc_data = message.get('document', {})
            media_url = doc_data.get('link')
            media_mime = doc_data.get('mime_type', 'application/octet-stream')
        elif message_type == 'image':
            img_data = message.get('image', {})
            media_url = img_data.get('link')
            media_mime = img_data.get('mime_type', 'image/jpeg')
        
        # Step 4: Save the WhatsApp message record
        wa_msg = WhatsAppMessage(
            whatsapp_message_id=message_id,
            business_id=business.id,
            sender_phone=sender_phone,
            message_type=message_type,
            raw_text=text_content,
            media_url=media_url,
            media_mime_type=media_mime,
            webhook_data=message
        )
        db.session.add(wa_msg)
        db.session.flush()  # Get the ID without committing
        
        statement_id = None
        evidence_id = None
        
        # Step 5: Process text messages for financial data
        if message_type == 'text' and text_content:
            amount, confidence = extract_amount_from_text(text_content)
            wa_msg.extracted_amount = amount
            wa_msg.confidence_score = confidence
            wa_msg.parsed_text = text_content
            
            if amount:
                parsed_data = parse_statement_text(text_content)
                
                # Create statement record
                stmt = BusinessStatement(
                    business_id=business.id,
                    statement_type='daily_sales',
                    amount=amount,
                    currency='INR',
                    transaction_date=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow(),
                    source='whatsapp',
                    description=text_content,
                    confidence_level='medium' if confidence > 0.5 else 'low',
                    confidence_reason=f'Parsed from WhatsApp message (confidence: {confidence:.2f})'
                )
                db.session.add(stmt)
                db.session.flush()
                statement_id = stmt.id
                
                wa_msg.extracted_date = stmt.transaction_date
                wa_msg.extracted_type = parsed_data.get('type', 'unknown')
                wa_msg.mark_processed('statement_created', statement_id=statement_id)
                logger.info(f"Created statement {statement_id} from WhatsApp message for business {business.id}")
            else:
                wa_msg.mark_processed('parsed')
        
        # Step 6: Process media
        elif message_type in ['image', 'document'] and media_url:
            wa_msg.mark_processed('evidence_processing')
            logger.info(f"Media message received for business {business.id}: {message_type}")
            # Media processing happens asynchronously in background tasks
        
        else:
            wa_msg.mark_processed('skipped', error='No actionable content')
        
        db.session.commit()
        
        return {
            'success': True,
            'message_id': wa_msg.id,
            'business_id': business.id,
            'statement_id': statement_id,
            'extracted_amount': wa_msg.extracted_amount,
            'confidence': wa_msg.confidence_score
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing webhook message: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def get_business_messages(business_id: int, limit: int = 50, status: str = None):
    """
    Get WhatsApp messages for a business.
    
    Args:
        business_id: Business ID
        limit: Max messages to return
        status: Filter by status (received, parsed, statement_created, etc)
    """
    query = WhatsAppMessage.query.filter_by(business_id=business_id)
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(WhatsAppMessage.created_at.desc()).limit(limit).all()


def get_unprocessed_messages(limit: int = 100):
    """
    Get all messages that haven't been fully processed yet.
    """
    return WhatsAppMessage.query.filter(
        WhatsAppMessage.status.in_(['received', 'parsing', 'evidence_processing'])
    ).order_by(WhatsAppMessage.created_at.asc()).limit(limit).all()


def get_message_stats(business_id: int = None):
    """
    Get statistics about WhatsApp messages.
    """
    query = WhatsAppMessage.query
    
    if business_id:
        query = query.filter_by(business_id=business_id)
    
    total = query.count()
    by_status = {}
    by_type = {}
    
    for status in ['received', 'parsed', 'statement_created', 'evidence_completed', 'error', 'skipped']:
        by_status[status] = query.filter_by(status=status).count()
    
    for msg_type in ['text', 'image', 'document', 'audio', 'video']:
        by_type[msg_type] = query.filter_by(message_type=msg_type).count()
    
    return {
        'total_messages': total,
        'by_status': by_status,
        'by_type': by_type,
        'total_amount_extracted': db.session.query(
            db.func.sum(WhatsAppMessage.extracted_amount)
        ).filter(WhatsAppMessage.extracted_amount.isnot(None)).scalar() or 0.0
    }
