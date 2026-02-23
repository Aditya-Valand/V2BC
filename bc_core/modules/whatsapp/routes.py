"""
WhatsApp integration routes for webhook and messaging.

Endpoints:
- GET /webhook - Webhook verification
- POST /webhook - Incoming message receiver
- GET /businesses/<id>/messages - Get business messages
- GET /statistics - Get integration statistics
"""
from flask import Blueprint, request, jsonify
from modules.whatsapp.service import (
    process_webhook_message,
    get_business_messages,
    get_message_stats
)
from modules.whatsapp.models import WhatsAppMessage
from core.extensions import db
import os
import logging

logger = logging.getLogger(__name__)
whatsapp_bp = Blueprint('whatsapp', __name__)

# WhatsApp webhook verification token (from environment)
WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "bharatcompliance_webhook")


@whatsapp_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    WhatsApp webhook verification endpoint.
    Used by WhatsApp to verify that our server owns this webhook URL.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Verify the token
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        return challenge, 200
    else:
        return 'Forbidden', 403


@whatsapp_bp.route('/webhook', methods=['POST'])
def receive_webhook():
    """
    WhatsApp webhook message receiver.
    
    Handles incoming WhatsApp Cloud API webhooks and processes messages:
    1. Validates webhook payload structure
    2. Extracts messages from webhook
    3. Routes to appropriate business
    4. Creates statements/evidence as needed
    
    Always returns 200 to WhatsApp to prevent retry storms.
    Processing happens asynchronously.
    """
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Empty webhook payload")
            return jsonify({'status': 'received'}), 200
        
        # WhatsApp sends webhooks with this structure:
        # { "entry": [{ "changes": [{ "field": "messages", "value": { "messages": [...], "contacts": [...] } }] }] }
        
        webhook_context = {}
        processed_count = 0
        error_count = 0
        
        if data.get('entry'):
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # Store webhook context (contacts, metadata)
                        webhook_context = value
                        
                        # Process each message
                        messages = value.get('messages', [])
                        for message in messages:
                            result = process_webhook_message(message, webhook_context)
                            if result.get('success'):
                                processed_count += 1
                                logger.info(f"Processed message {result.get('message_id')}")
                            else:
                                error_count += 1
                                logger.warning(f"Failed to process message: {result.get('error')}")
        
        logger.info(f"Webhook processed: {processed_count} success, {error_count} errors")
        
        # Always return 200 to WhatsApp
        return jsonify({
            'status': 'received',
            'processed': processed_count,
            'errors': error_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        # Still return 200 to avoid retry storms
        return jsonify({'status': 'received', 'error': str(e)}), 200


@whatsapp_bp.route('/webhook/status', methods=['POST'])
def webhook_status():
    """
    WhatsApp webhook status updates (delivery, read receipts, etc.)
    
    Handles:
    - Message delivery confirmations
    - Message read receipts
    - Message failed statuses
    """
    try:
        data = request.get_json()
        # WhatsApp sends status updates in similar format
        if data.get('entry'):
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        statuses = change.get('value', {}).get('statuses', [])
                        for status in statuses:
                            # Could track message delivery status here
                            logger.debug(f"Message status update: {status}")
        
        return jsonify({'status': 'acknowledged'}), 200
    except Exception as e:
        logger.error(f"Error processing status webhook: {str(e)}")
        return jsonify({'status': 'acknowledged'}), 200


@whatsapp_bp.route('/businesses/<int:business_id>/messages', methods=['GET'])
def get_messages(business_id):
    """
    Get WhatsApp messages for a business.
    
    Query parameters:
    - status: Filter by status (received, parsed, statement_created, etc)
    - limit: Max messages to return (default: 50)
    
    Returns:
        List of messages with extraction results and processing status
    """
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', default=50, type=int)
        
        messages = get_business_messages(business_id, limit=limit, status=status)
        
        return jsonify({
            'success': True,
            'count': len(messages),
            'messages': [
                {
                    'id': msg.id,
                    'whatsapp_id': msg.whatsapp_message_id,
                    'type': msg.message_type,
                    'status': msg.status,
                    'raw_text': msg.raw_text,
                    'extracted_amount': msg.extracted_amount,
                    'confidence': msg.confidence_score,
                    'statement_id': msg.statement_id,
                    'evidence_id': msg.evidence_id,
                    'created_at': msg.created_at.isoformat(),
                    'processed_at': msg.processed_at.isoformat() if msg.processed_at else None,
                    'error': msg.processing_error
                }
                for msg in messages
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@whatsapp_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get WhatsApp integration statistics.
    
    Query parameters:
    - business_id: Filter by business (optional)
    
    Returns:
        Statistics about message processing, amounts extracted, etc
    """
    try:
        business_id = request.args.get('business_id', type=int)
        
        stats = get_message_stats(business_id=business_id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@whatsapp_bp.route('/messages/<int:message_id>', methods=['GET'])
def get_message_detail(message_id):
    """
    Get detailed information about a WhatsApp message.
    """
    try:
        msg = WhatsAppMessage.query.get(message_id)
        if not msg:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        return jsonify({
            'success': True,
            'message': {
                'id': msg.id,
                'whatsapp_id': msg.whatsapp_message_id,
                'business_id': msg.business_id,
                'sender': msg.sender_phone,
                'type': msg.message_type,
                'status': msg.status,
                'raw_text': msg.raw_text,
                'parsed_text': msg.parsed_text,
                'extracted_amount': msg.extracted_amount,
                'extracted_date': msg.extracted_date.isoformat() if msg.extracted_date else None,
                'extracted_type': msg.extracted_type,
                'confidence': msg.confidence_score,
                'media_url': msg.media_url,
                'media_type': msg.media_mime_type,
                'statement_id': msg.statement_id,
                'evidence_id': msg.evidence_id,
                'processing_error': msg.processing_error,
                'created_at': msg.created_at.isoformat(),
                'processed_at': msg.processed_at.isoformat() if msg.processed_at else None,
                'updated_at': msg.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting message detail: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
