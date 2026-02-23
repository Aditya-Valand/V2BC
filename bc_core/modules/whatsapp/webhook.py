"""
WhatsApp webhook utilities and message formatting helpers.

Provides:
- Message validation and extraction
- Webhook payload parsing
- Message formatting for replies
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validate_webhook_payload(data: Dict[str, Any]) -> bool:
    """
    Validate WhatsApp webhook payload structure.
    
    Args:
        data: Webhook payload
        
    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    if 'entry' not in data:
        return False
    
    entries = data.get('entry', [])
    if not isinstance(entries, list):
        return False
    
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        if 'changes' not in entry:
            return False
    
    return True


def extract_messages_from_webhook(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all messages from a webhook payload.
    
    Args:
        data: Webhook payload from WhatsApp
        
    Returns:
        List of message dicts
    """
    messages = []
    
    if not validate_webhook_payload(data):
        logger.warning("Invalid webhook payload structure")
        return messages
    
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'messages':
                value = change.get('value', {})
                messages.extend(value.get('messages', []))
    
    return messages


def extract_webhook_contacts(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract contact information from webhook payload.
    
    Args:
        data: Webhook payload
        
    Returns:
        Dict of phone -> contact info
    """
    contacts = {}
    
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'messages':
                value = change.get('value', {})
                for contact in value.get('contacts', []):
                    phone = contact.get('wa_id')
                    if phone:
                        contacts[phone] = {
                            'name': contact.get('profile', {}).get('name'),
                            'phone': phone
                        }
    
    return contacts


def format_text_message(text: str, phone: str) -> Dict[str, Any]:
    """
    Format a text message to send via WhatsApp.
    
    Args:
        text: Message text
        phone: Recipient phone number (with country code)
        
    Returns:
        WhatsApp API compatible message payload
    """
    return {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': phone,
        'type': 'text',
        'text': {
            'preview_url': False,
            'body': text
        }
    }


def format_template_message(template_name: str, language: str, phone: str, params: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Format a template message to send via WhatsApp.
    
    Args:
        template_name: Name of the template
        language: Language code (e.g., 'en', 'hi')
        phone: Recipient phone number
        params: Template parameters
        
    Returns:
        WhatsApp API compatible message payload
    """
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {
                'code': language
            }
        }
    }
    
    if params:
        payload['template']['components'] = [
            {
                'type': 'body',
                'parameters': [{'type': 'text', 'text': param} for param in params]
            }
        ]
    
    return payload


def format_button_message(text: str, buttons: List[Dict[str, str]], phone: str) -> Dict[str, Any]:
    """
    Format a message with quick reply buttons.
    
    Args:
        text: Message text
        buttons: List of {'id': str, 'title': str} dicts
        phone: Recipient phone number
        
    Returns:
        WhatsApp API compatible message payload
    """
    return {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'interactive',
        'interactive': {
            'type': 'button',
            'body': {
                'text': text
            },
            'action': {
                'buttons': [
                    {
                        'type': 'reply',
                        'reply': {
                            'id': btn['id'],
                            'title': btn['title']
                        }
                    }
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            }
        }
    }


def format_list_message(
    text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    phone: str
) -> Dict[str, Any]:
    """
    Format a message with a selection list.
    
    Args:
        text: Header text
        button_text: Button text
        sections: List of {'title': str, 'rows': [{'id': str, 'title': str, 'description': str}]}
        phone: Recipient phone number
        
    Returns:
        WhatsApp API compatible message payload
    """
    return {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'interactive',
        'interactive': {
            'type': 'list',
            'body': {
                'text': text
            },
            'action': {
                'button': button_text,
                'sections': sections
            }
        }
    }


def parse_quick_reply(message: Dict[str, Any]) -> Optional[str]:
    """
    Extract quick reply selection from message.
    
    Args:
        message: Message dict from webhook
        
    Returns:
        Selected button ID or None
    """
    if message.get('type') != 'interactive':
        return None
    
    interactive = message.get('interactive', {})
    button_reply = interactive.get('button_reply', {})
    return button_reply.get('id')


def parse_list_reply(message: Dict[str, Any]) -> Optional[str]:
    """
    Extract list selection from message.
    
    Args:
        message: Message dict from webhook
        
    Returns:
        Selected row ID or None
    """
    if message.get('type') != 'interactive':
        return None
    
    interactive = message.get('interactive', {})
    list_reply = interactive.get('list_reply', {})
    return list_reply.get('id')


def get_message_timestamp(message: Dict[str, Any]) -> datetime:
    """
    Get message timestamp from webhook message.
    
    Args:
        message: Message dict from webhook
        
    Returns:
        datetime object
    """
    timestamp = int(message.get('timestamp', 0))
    return datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()


def get_message_mime_type(message: Dict[str, Any]) -> Optional[str]:
    """
    Get MIME type from media message.
    
    Args:
        message: Message dict from webhook
        
    Returns:
        MIME type string or None
    """
    msg_type = message.get('type')
    
    if msg_type == 'image':
        return message.get('image', {}).get('mime_type', 'image/jpeg')
    elif msg_type == 'document':
        return message.get('document', {}).get('mime_type', 'application/octet-stream')
    elif msg_type == 'audio':
        return message.get('audio', {}).get('mime_type', 'audio/aac')
    elif msg_type == 'video':
        return message.get('video', {}).get('mime_type', 'video/mp4')
    
    return None
