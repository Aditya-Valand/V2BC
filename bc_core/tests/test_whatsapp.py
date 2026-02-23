#!/usr/bin/env python
"""
WhatsApp Integration Test Suite

Tests:
1. Model validations
2. Webhook payload parsing
3. Message processing pipeline
4. Database operations
5. API endpoints
6. Statistical queries
"""

import pytest
import json
from datetime import datetime, timedelta
from app import create_app, db
from modules.whatsapp.models import WhatsAppMessage, MessageStatus
from modules.whatsapp.service import (
    process_webhook_message,
    find_business_by_phone,
    extract_amount_from_text,
    get_business_messages,
    get_message_stats
)
from modules.whatsapp.webhook import (
    validate_webhook_payload,
    extract_messages_from_webhook,
    format_text_message
)
from modules.businesses.models import Business
from modules.organizations.models import Organization
from modules.statements.models import BusinessStatement


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_business(app):
    """Create test business"""
    with app.app_context():
        org = Organization(name='Test Org')
        db.session.add(org)
        db.session.flush()
        
        business = Business(
            org_id=org.id,
            name='Test Business',
            whatsapp_phone='+919876543210',
            gstin='12ABCDE1234F1Z5',
            pan='ABCDE1234F',
            expected_turnover=10_000_000,
            business_type='retail',
            state='MH'
        )
        db.session.add(business)
        db.session.commit()
        
        return business


class TestWhatsAppModels:
    """Test WhatsApp message models"""
    
    def test_whatsapp_message_creation(self, app, test_business):
        with app.app_context():
            msg = WhatsAppMessage(
                whatsapp_message_id='wamid.test123',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='text',
                raw_text='Sales: 50000',
                extracted_amount=50000.0,
                confidence_score=0.95,
                status='statement_created'
            )
            db.session.add(msg)
            db.session.commit()
            
            assert msg.id is not None
            assert msg.whatsapp_message_id == 'wamid.test123'
            assert msg.extracted_amount == 50000.0
    
    def test_mark_processed(self, app, test_business):
        with app.app_context():
            msg = WhatsAppMessage(
                whatsapp_message_id='wamid.test123',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='text',
                raw_text='Sales: 50000',
                status='received'
            )
            db.session.add(msg)
            db.session.flush()
            
            msg.mark_processed('statement_created', statement_id=123)
            db.session.commit()
            
            assert msg.status == 'statement_created'
            assert msg.statement_id == 123
            assert msg.processed_at is not None


class TestWebhookParsing:
    """Test webhook payload parsing"""
    
    def test_validate_webhook_payload(self):
        payload = {
            'entry': [
                {
                    'changes': [
                        {
                            'field': 'messages',
                            'value': {
                                'messages': [
                                    {
                                        'id': 'wamid.123',
                                        'from': '+919876543210',
                                        'type': 'text',
                                        'text': {'body': 'Hello'}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        assert validate_webhook_payload(payload) == True
    
    def test_validate_invalid_payload(self):
        assert validate_webhook_payload({}) == False
        assert validate_webhook_payload(None) == False
        assert validate_webhook_payload({'entry': 'invalid'}) == False
    
    def test_extract_messages_from_webhook(self):
        payload = {
            'entry': [
                {
                    'changes': [
                        {
                            'field': 'messages',
                            'value': {
                                'messages': [
                                    {'id': 'msg1', 'from': '+919876543210', 'type': 'text'},
                                    {'id': 'msg2', 'from': '+919876543210', 'type': 'image'}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        messages = extract_messages_from_webhook(payload)
        assert len(messages) == 2
        assert messages[0]['id'] == 'msg1'


class TestAmountExtraction:
    """Test financial amount extraction"""
    
    def test_extract_simple_amount(self):
        amount, confidence = extract_amount_from_text("Sales: 50000")
        assert amount == 50000.0
        assert confidence > 0.5
    
    def test_extract_formatted_amount(self):
        amount, confidence = extract_amount_from_text("Sales: 50,000")
        assert amount == 50000.0
    
    def test_extract_with_currency(self):
        amount, confidence = extract_amount_from_text("₹50000")
        assert amount == 50000.0
    
    def test_extract_decimal_amount(self):
        amount, confidence = extract_amount_from_text("₹50000.50")
        assert amount == 50000.50
    
    def test_extract_no_amount(self):
        amount, confidence = extract_amount_from_text("Hello there")
        assert amount is None


class TestBusinessRouting:
    """Test finding business by phone"""
    
    def test_find_business_exact_match(self, app, test_business):
        with app.app_context():
            found = find_business_by_phone('+919876543210')
            assert found is not None
            assert found.id == test_business.id
    
    def test_find_business_without_country_code(self, app, test_business):
        with app.app_context():
            # Should also match without +91
            found = find_business_by_phone('9876543210')
            assert found is not None
            assert found.id == test_business.id
    
    def test_find_nonexistent_business(self, app):
        with app.app_context():
            found = find_business_by_phone('+911234567890')
            assert found is None


class TestMessageProcessing:
    """Test message processing pipeline"""
    
    def test_process_text_message(self, app, test_business):
        with app.app_context():
            message = {
                'id': 'wamid.test123',
                'from': '+919876543210',
                'type': 'text',
                'timestamp': str(int(datetime.utcnow().timestamp())),
                'text': {'body': 'Sales today: 50000'}
            }
            
            result = process_webhook_message(message, {})
            
            assert result['success'] == True
            assert result['extracted_amount'] == 50000.0
            assert result['statement_id'] is not None
    
    def test_process_message_no_business(self, app):
        with app.app_context():
            message = {
                'id': 'wamid.test123',
                'from': '+991234567890',  # Non-existent business
                'type': 'text',
                'timestamp': str(int(datetime.utcnow().timestamp())),
                'text': {'body': 'Sales: 50000'}
            }
            
            result = process_webhook_message(message, {})
            
            assert result['success'] == False
            assert 'No business found' in result['error']
    
    def test_process_message_no_amount(self, app, test_business):
        with app.app_context():
            message = {
                'id': 'wamid.test123',
                'from': '+919876543210',
                'type': 'text',
                'timestamp': str(int(datetime.utcnow().timestamp())),
                'text': {'body': 'Hello there'}
            }
            
            result = process_webhook_message(message, {})
            
            assert result['success'] == True
            # Message should be saved but status should be 'parsed' not 'statement_created'
            msg = WhatsAppMessage.query.filter_by(whatsapp_message_id='wamid.test123').first()
            assert msg.status in ['parsed', 'skipped']


class TestDatabaseQueries:
    """Test database query functions"""
    
    def test_get_business_messages(self, app, test_business):
        with app.app_context():
            # Create some messages
            for i in range(5):
                msg = WhatsAppMessage(
                    whatsapp_message_id=f'wamid.{i}',
                    business_id=test_business.id,
                    sender_phone='+919876543210',
                    message_type='text',
                    raw_text=f'Sales: {10000 * (i+1)}',
                    status='statement_created'
                )
                db.session.add(msg)
            db.session.commit()
            
            messages = get_business_messages(test_business.id, limit=10)
            assert len(messages) == 5
    
    def test_get_business_messages_filtered_by_status(self, app, test_business):
        with app.app_context():
            # Create messages with different statuses
            msg1 = WhatsAppMessage(
                whatsapp_message_id='wamid.1',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='text',
                status='received'
            )
            msg2 = WhatsAppMessage(
                whatsapp_message_id='wamid.2',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='text',
                status='statement_created'
            )
            db.session.add_all([msg1, msg2])
            db.session.commit()
            
            messages = get_business_messages(test_business.id, status='statement_created')
            assert len(messages) == 1
            assert messages[0].status == 'statement_created'
    
    def test_get_message_stats(self, app, test_business):
        with app.app_context():
            # Create messages with various types
            msg1 = WhatsAppMessage(
                whatsapp_message_id='wamid.1',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='text',
                raw_text='Sales: 50000',
                extracted_amount=50000.0,
                status='statement_created'
            )
            msg2 = WhatsAppMessage(
                whatsapp_message_id='wamid.2',
                business_id=test_business.id,
                sender_phone='+919876543210',
                message_type='image',
                status='evidence_processing'
            )
            db.session.add_all([msg1, msg2])
            db.session.commit()
            
            stats = get_message_stats(business_id=test_business.id)
            
            assert stats['total_messages'] == 2
            assert stats['by_status']['statement_created'] == 1
            assert stats['by_status']['evidence_processing'] == 1
            assert stats['by_type']['text'] == 1
            assert stats['by_type']['image'] == 1
            assert stats['total_amount_extracted'] == 50000.0


class TestWebhookEndpoints:
    """Test webhook API endpoints"""
    
    def test_webhook_verification(self, client):
        response = client.get(
            '/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=bharatcompliance_webhook&hub.challenge=test_challenge'
        )
        assert response.status_code == 200
        assert response.data == b'test_challenge'
    
    def test_webhook_verification_invalid_token(self, client):
        response = client.get(
            '/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=invalid&hub.challenge=test'
        )
        assert response.status_code == 403
    
    def test_receive_message_webhook(self, client, app, test_business):
        with app.app_context():
            payload = {
                'entry': [
                    {
                        'changes': [
                            {
                                'field': 'messages',
                                'value': {
                                    'messages': [
                                        {
                                            'id': 'wamid.webhook1',
                                            'from': '+919876543210',
                                            'type': 'text',
                                            'timestamp': str(int(datetime.utcnow().timestamp())),
                                            'text': {'body': 'Sales: 50000'}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
            
            response = client.post(
                '/whatsapp/webhook',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'received'
            assert data['processed'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
