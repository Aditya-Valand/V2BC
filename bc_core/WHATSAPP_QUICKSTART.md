# WhatsApp Integration - Quick Start Guide

## What's Ready?

✅ **Complete WhatsApp Integration** with:
- Webhook endpoint for receiving messages
- Automatic message parsing and statement creation
- Message status tracking and error handling
- REST APIs for querying messages and statistics
- Database schema with full lifecycle tracking
- Comprehensive test suite
- Production-ready error handling and logging

## 5-Minute Setup

### 1. Start the Flask Server

```bash
python -c "from app import app; app.run(debug=True, port=5000)"
```

### 2. Verify Installation

```bash
# Check all systems working
python verify_system.py

# Should output:
# [SUCCESS] SYSTEM VERIFICATION COMPLETE
# Status: PRODUCTION READY
```

### 3. Configure WhatsApp Cloud API

```bash
# Get webhook token
export WHATSAPP_VERIFY_TOKEN="your-secure-token-here"

# Your webhook URL (must be HTTPS in production):
# https://your-domain.com/whatsapp/webhook
```

### 4. Test with Sample Data

```bash
# Create test business with WhatsApp phone
curl -X POST http://localhost:5000/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": 1,
    "name": "Test Business",
    "whatsapp_phone": "+919876543210",
    "gstin": "12ABCDE1234F1Z5",
    "state": "MH"
  }'

# Simulate incoming WhatsApp message
curl -X POST http://localhost:5000/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "field": "messages",
        "value": {
          "messages": [{
            "id": "wamid.test123",
            "from": "+919876543210",
            "type": "text",
            "timestamp": "1705000000",
            "text": {"body": "Sales today: 50000 rupees"}
          }]
        }
      }]
    }]
  }'

# Check if message was processed
curl http://localhost:5000/whatsapp/businesses/1/messages

# Get statistics
curl http://localhost:5000/whatsapp/statistics
```

## Key Features

### 1. Automatic Amount Extraction

Send messages like:
- "Sales: 50000"
- "50,000"
- "₹50000"
- "Rs 50000"
- "Today sales are 50000"

All will be parsed and statement records created automatically.

### 2. Message Status Tracking

Each message goes through states:
```
RECEIVED → PARSED → STATEMENT_CREATED → (EVIDENCE_COMPLETED or SKIPPED)
```

Track progress with:
```bash
curl http://localhost:5000/whatsapp/businesses/1/messages?status=statement_created
```

### 3. Confidence Scoring

Extraction confidence automatically scored (0.0-1.0):
- 0.95: "₹50000" (clear)
- 0.85: "Sales: 50000" (good)
- 0.70: "approx 50000" (ambiguous)
- 0.00: "Hello there" (no amount)

### 4. Statistics & Analytics

Get integration insights:
```bash
curl http://localhost:5000/whatsapp/statistics

# Returns:
{
  "total_messages": 250,
  "by_status": {
    "statement_created": 200,
    "evidence_completed": 30,
    "error": 10,
    "skipped": 10
  },
  "by_type": {
    "text": 200,
    "image": 30,
    "document": 15,
    "audio": 5
  },
  "total_amount_extracted": 5000000.0
}
```

## API Quick Reference

### Send Message to Business
```bash
POST /whatsapp/webhook
Body: WhatsApp webhook JSON
```

### Query Messages
```bash
# All messages for business
GET /whatsapp/businesses/{id}/messages

# Filter by status
GET /whatsapp/businesses/{id}/messages?status=statement_created

# Limit results
GET /whatsapp/businesses/{id}/messages?limit=20
```

### Message Details
```bash
GET /whatsapp/messages/{id}
```

### Statistics
```bash
GET /whatsapp/statistics
GET /whatsapp/statistics?business_id=1
```

## Database Schema

### WhatsAppMessage (22 columns)
- ID, WhatsApp ID, Business ID
- Sender Phone
- Message type (text/image/document)
- Raw & parsed text
- Media URL & MIME type
- Extracted amount & date
- Confidence score (0-1)
- Status (received/parsed/statement_created/error)
- Links to Statement & Evidence records
- Webhook data & timestamps

### BusinessStatement (17 columns)
Enhanced with:
- Confidence level & reason
- Verification tracking (verified by, verified at)
- Source (whatsapp/web/api)
- Full audit timestamps

## Workflow Examples

### Scenario 1: Daily Sales Report

```
User sends WhatsApp:
"Sales today: Rs 50000"
          ↓
Webhook received
          ↓
Message parsed → amount=50000
          ↓
Statement created
          ↓
CA dashboard shows new statement
          ↓
CA can verify/reject in app
```

### Scenario 2: Invoice Upload

```
User sends invoice image
          ↓
Webhook received
          ↓
Message marked: evidence_processing
          ↓
(Async) OCR processes image
          ↓
Evidence record created with extracted data
          ↓
CA reviews extracted invoice details
```

### Scenario 3: Query Message History

```
bash: GET /whatsapp/businesses/1/messages
          ↓
Returns: [
  {message_id, amount, confidence, status, created_at, ...},
  {message_id, amount, confidence, status, created_at, ...},
  ...
]
```

## Testing

### Run Unit Tests
```bash
pytest tests/test_whatsapp.py -v
```

### Run Manual Webhook Test
```bash
python -c "
from app import create_app, db
from modules.whatsapp.service import process_webhook_message

app = create_app()
with app.app_context():
    # Create test business first
    message = {
        'id': 'wamid.test',
        'from': '+919876543210',
        'type': 'text',
        'timestamp': '1705000000',
        'text': {'body': 'Sales: 50000'}
    }
    
    result = process_webhook_message(message, {})
    print(f'Result: {result}')
    print(f'Amount extracted: {result.get(\"extracted_amount\")}')
    print(f'Confidence: {result.get(\"confidence\")}')
"
```

## Troubleshooting

### Messages not being created

1. **Check Business Registration**
   ```bash
   curl http://localhost:5000/businesses
   # Verify business with matching whatsapp_phone
   ```

2. **Check Webhook Format**
   - Verify JSON structure matches WhatsApp Cloud API format
   - Check that 'from' field contains registered phone

3. **Check Logs**
   ```bash
   # Look for processing_error in WhatsAppMessage record
   curl http://localhost:5000/whatsapp/messages/1
   # See 'error' field if processing failed
   ```

### Low Confidence Scores

1. Message format unclear? Add more context:
   - "Sales: 50000" (better) vs "50000" (ambiguous)

2. Check number format:
   - "₹50000" or "50,000" work best
   - Multi-digit numbers in text might need currency prefix

3. Review parsing patterns in:
   - `modules/statements/parser.py` → `parse_statement_text()`

### Media Not Processing

1. Verify media URL is accessible from server
2. Check OCR service configuration (if enabled)
3. Review evidence processing logs

## Next Steps

1. **Configure WhatsApp Cloud API**
   - Get business account from Meta
   - Set up webhook with your URL
   - Get access token for outbound messages

2. **Add Outbound Messages**
   - Send confirmations: "Received: ₹50000"
   - Request clarifications: "Is this ₹50000 or ₹500000?"
   - Use templates for formatted replies

3. **Deploy to Production**
   - Set up HTTPS
   - Configure database (PostgreSQL recommended)
   - Set environment variables
   - Enable logging and monitoring

4. **Enhance Parsing**
   - Add support for more languages
   - ML-based amount extraction
   - Document classification

## Support Files

- **Documentation**: [WHATSAPP_INTEGRATION.md](WHATSAPP_INTEGRATION.md)
- **Models**: `modules/whatsapp/models.py`
- **Service**: `modules/whatsapp/service.py`
- **Routes**: `modules/whatsapp/routes.py`
- **Webhooks**: `modules/whatsapp/webhook.py`
- **Tests**: `tests/test_whatsapp.py`
