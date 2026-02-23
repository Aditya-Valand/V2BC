# BharatCompliance: Implementation Quick-Start Guide

## Reading Order for Audit Documents

1. **CRITICAL_ISSUES.md** ← Start here (15 min read)
   - Top 12 issues in priority order
   - What needs to be fixed immediately

2. **STATUS_CHECKLIST.md** ← Read next (10 min read)
   - What works vs what doesn't
   - Verdict by phase
   - User journey impact

3. **ARCHITECTURE_AUDIT.md** ← Full deep dive (45 min read)
   - Complete analysis
   - Code examples
   - Detailed explanations

---

## How to Fix Each Critical Issue

### CRITICAL #1: Implement WhatsApp Webhook

**File:** `bc_core/modules/whatsapp/routes.py`

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import hmac
import hashlib
import os
from modules.whatsapp.service import save_message, process_message

whatsapp_bp = Blueprint("whatsapp", __name__)

def verify_whatsapp_signature(payload_raw, signature_header):
    """Verify webhook came from WhatsApp"""
    expected = hmac.new(
        os.getenv("WHATSAPP_WEBHOOK_SECRET", "").encode(),
        payload_raw,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)

@whatsapp_bp.route("/webhook", methods=["GET"])
def webhook_verify():
    """WhatsApp verification endpoint"""
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "your-token")
    
    if token == expected_token:
        return challenge, 200
    return "Invalid token", 403

@whatsapp_bp.route("/webhook", methods=["POST"])
def webhook_receiver():
    """Receive messages from WhatsApp"""
    
    # Get raw body for signature verification
    payload_raw = request.get_data(as_text=True)
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Verify signature (optional but recommended)
    # if not verify_whatsapp_signature(payload_raw, signature):
    #     return jsonify({"error": "Invalid signature"}), 403
    
    payload = request.json
    
    try:
        # WhatsApp sends entry array
        entries = payload.get("entry", [])
        
        for entry in entries:
            changes = entry.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    # Process each message
                    process_message(message)
        
        # WhatsApp requires 200 response within 30 seconds
        return jsonify({"status": "ok"}), 200
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500
```

**File:** `bc_core/modules/whatsapp/service.py` - Update existing

```python
from core.extensions import db
from modules.whatsapp.models import WhatsAppMessage
from modules.businesses.models import Business
from modules.statements.service import create_statement
from modules.evidence.service import save_evidence
from datetime import datetime
import requests
import os

def process_message(message_data):
    """Process incoming WhatsApp message"""
    
    # Extract message info
    phone_number = message_data.get("from")  # e.g., "919876543210"
    message_id = message_data.get("id")
    timestamp = message_data.get("timestamp")
    
    # Find business by phone
    business = Business.query.filter_by(whatsapp_phone=phone_number).first()
    
    if not business:
        # Log unknown sender
        log_unknown_sender(phone_number)
        return None
    
    message_type = message_data.get("type")  # text, image, document, etc.
    
    # Handle different message types
    if message_type == "text":
        text_content = message_data.get("text", {}).get("body", "")
        
        # Save raw message
        msg = WhatsAppMessage(
            business_id=business.id,
            sender=phone_number,
            message_type="text",
            raw_text=text_content,
            processed=False,
            created_at=datetime.fromtimestamp(int(timestamp))
        )
        db.session.add(msg)
        db.session.commit()
        
        # Parse as statement
        create_statement(business.id, text_content, source="whatsapp")
        
        # Mark as processed
        msg.processed = True
        db.session.commit()
    
    elif message_type in ["image", "document", "video"]:
        # Download media from WhatsApp
        media_data = message_data.get(message_type, {})
        media_id = media_data.get("id")
        
        # Save raw message
        msg = WhatsAppMessage(
            business_id=business.id,
            sender=phone_number,
            message_type=message_type,
            raw_text=message_data.get("text", {}).get("caption", ""),
            processed=False,
            created_at=datetime.fromtimestamp(int(timestamp))
        )
        db.session.add(msg)
        db.session.commit()
        
        # Download and save as evidence
        file_path = download_whatsapp_media(media_id)
        if file_path:
            from modules.evidence.service import save_evidence_from_path
            save_evidence_from_path(file_path, business.id, source="whatsapp")
        
        # Mark as processed
        msg.processed = True
        db.session.commit()
    
    return msg

def download_whatsapp_media(media_id):
    """Download media from WhatsApp Cloud API"""
    
    # Get media URL
    url = f"https://graph.instagram.com/v17.0/{media_id}/"
    
    params = {
        "access_token": os.getenv("WHATSAPP_BUSINESS_ACCOUNT_TOKEN")
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        return None
    
    media_data = response.json()
    media_url = media_data.get("media_product_type")  # Adjust based on actual response
    
    # Download the actual file
    file_response = requests.get(media_url, headers={
        "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_ACCOUNT_TOKEN')}"
    })
    
    # Save temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(file_response.content)
        return f.name

def log_unknown_sender(phone_number):
    """Log messages from unknown phone numbers"""
    # TODO: Store in database for admin review
    print(f"Message from unknown sender: {phone_number}")
```

**Required Environment Variables:**
```env
WHATSAPP_VERIFY_TOKEN=your-random-token-here
WHATSAPP_BUSINESS_ACCOUNT_TOKEN=your-business-account-token
WHATSAPP_WEBHOOK_SECRET=your-webhook-secret
```

---

### CRITICAL #2: Add WhatsApp Phone to Business

**File:** `bc_core/modules/businesses/models.py` - Update

```python
from core.extensions import db
from datetime import datetime

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    
    # NEW: Link to micro-business owner user
    owner_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    
    # NEW: WhatsApp phone number (primary identifier)
    whatsapp_phone = db.Column(db.String(20), unique=True, nullable=True)
    
    # Existing
    name = db.Column(db.String(150))
    business_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    expected_turnover = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Create Migration:**
```bash
cd bc_core
flask db migrate -m "add whatsapp_phone and owner_user_id to business"
flask db upgrade
```

---

### CRITICAL #3: Add Permission Model

**File:** `bc_core/modules/auth/models.py` - Update

```python
from core.extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20))  # CA, staff, client
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# NEW: Permission model
class UserOrganizationPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    role = db.Column(db.String(50), default="staff")  # owner, manager, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'organization_id', name='uq_user_org'),)
```

**Create Migration:**
```bash
flask db migrate -m "add UserOrganizationPermission model"
flask db upgrade
```

---

### CRITICAL #4: Register Missing Blueprints

**File:** `bc_core/app.py` - Update

```python
from flask import Flask
from core.config import Config
from core.extensions import db, migrate, jwt
from core.dependencies import register_error_handlers

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from modules.auth.routes import auth_bp
    from modules.organizations.routes import org_bp
    from modules.businesses.routes import business_bp
    from modules.evidence.routes import evidence_bp
    from modules.statements.routes import statements_bp
    from modules.whatsapp.routes import whatsapp_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(org_bp, url_prefix="/orgs")
    app.register_blueprint(business_bp, url_prefix="/businesses")
    app.register_blueprint(evidence_bp, url_prefix="/evidence")  # NEW
    app.register_blueprint(statements_bp, url_prefix="/statements")  # NEW
    app.register_blueprint(whatsapp_bp, url_prefix="/whatsapp")  # NEW
    
    register_error_handlers(app)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
```

---

### CRITICAL #5: Add Permission Checks

**File:** `bc_core/core/dependencies.py` - Update

```python
from flask import jsonify
from functools import wraps
from flask_jwt_extended import get_jwt_identity
from modules.auth.models import UserOrganizationPermission
from modules.businesses.models import Business

def require_org_access(f):
    """Decorator to check if user has access to organization"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        org_id = kwargs.get('org_id')
        
        if not org_id:
            return jsonify({"error": "org_id required"}), 400
        
        perm = UserOrganizationPermission.query.filter_by(
            user_id=user_id,
            organization_id=org_id
        ).first()
        
        if not perm:
            return jsonify({"error": "Unauthorized"}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def require_business_access(f):
    """Decorator to check if user can access business"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        business_id = kwargs.get('business_id')
        
        if not business_id:
            return jsonify({"error": "business_id required"}), 400
        
        business = Business.query.get(business_id)
        if not business:
            return jsonify({"error": "Business not found"}), 404
        
        # Check if user has access to this business's organization
        perm = UserOrganizationPermission.query.filter_by(
            user_id=user_id,
            organization_id=business.org_id
        ).first()
        
        if not perm:
            return jsonify({"error": "Unauthorized"}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def register_error_handlers(app):
    @app.errorhandler(422)
    def handle_validation_error(err):
        return jsonify({"error": err.description}), 422
```

**Update routes to use decorator:**
```python
from core.dependencies import require_org_access, require_business_access

@business_bp.route("/<int:org_id>")
@jwt_required()
@require_org_access
def list_all(org_id):
    bs = list_businesses(org_id)
    return jsonify(BusinessResponseSchema(many=True).dump(bs))
```

---

### CRITICAL #6: Update Confidence on OCR

**File:** `bc_core/modules/ocr/service.py` - Update

```python
from modules.ocr.client import extract_text
from modules.ocr.extractor import extract_amount, extract_date, extract_gstin
from core.extensions import db
from modules.evidence.models import BusinessEvidence
from modules.statements.models import BusinessStatement

def run_ocr(evidence: BusinessEvidence):
    try:
        full_text, blocks = extract_text(evidence.file_path)
        
        amount = extract_amount(full_text)
        gstin = extract_gstin(full_text)
        date = extract_date(full_text)
        
        evidence.ocr_text = full_text
        evidence.detected_amount = amount
        evidence.detected_gstin = gstin
        evidence.detected_date = date
        
        # Set status based on OCR results
        if amount or gstin:
            evidence.status = "usable"
        else:
            evidence.status = "needs_review"
        
        # NEW: Update associated statement's confidence
        if evidence.statement_id:
            stmt = BusinessStatement.query.get(evidence.statement_id)
            if stmt:
                # Calculate confidence based on OCR extraction
                if amount and gstin and date:
                    stmt.confidence_level = "high"
                    stmt.confidence_reason = "OCR found amount, GSTIN, and date"
                elif amount and gstin:
                    stmt.confidence_level = "high"
                    stmt.confidence_reason = "OCR found amount and GSTIN"
                elif amount:
                    stmt.confidence_level = "medium"
                    stmt.confidence_reason = "OCR found amount"
                elif gstin:
                    stmt.confidence_level = "medium"
                    stmt.confidence_reason = "OCR found GSTIN"
                else:
                    stmt.confidence_level = "low"
                    stmt.confidence_reason = "OCR extraction failed"
        
        db.session.commit()
        
        return {
            "amount": amount,
            "gstin": gstin,
            "date": str(date) if date else None,
            "status": evidence.status
        }
    
    except Exception as e:
        evidence.status = "needs_review"
        evidence.ocr_text = f"OCR Error: {str(e)}"
        db.session.commit()
        raise
```

---

## Testing Your Changes

### 1. After Adding WhatsApp Phone Field
```bash
# Test that business can have a phone
curl -X POST http://localhost:5000/businesses \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tea Shop",
    "org_id": 1,
    "whatsapp_phone": "919876543210",
    "business_type": "retail"
  }'
```

### 2. After Adding Permission Model
```bash
# Create a test organization
curl -X POST http://localhost:5000/orgs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My CA Firm"}'

# Try to access it (should work if you're the owner)
curl -X GET http://localhost:5000/orgs \
  -H "Authorization: Bearer TOKEN"
```

### 3. After Registering Blueprints
```bash
# These should now return 200 (or 401 if not authorized)
curl http://localhost:5000/statements/business/1 \
  -H "Authorization: Bearer TOKEN"

curl http://localhost:5000/evidence/upload \
  -X POST \
  -H "Authorization: Bearer TOKEN"
```

---

## Implementation Checklist

- [ ] Read all three audit documents
- [ ] Understand WhatsApp webhook flow
- [ ] Add whatsapp_phone to Business model
- [ ] Create migration for whatsapp_phone
- [ ] Create UserOrganizationPermission model
- [ ] Create migration for permissions
- [ ] Update app.py to register missing blueprints
- [ ] Implement WhatsApp webhook receiver
- [ ] Implement permission decorators
- [ ] Update OCR service to set confidence
- [ ] Add environment variables
- [ ] Test each endpoint
- [ ] Run migrations
- [ ] Delete documents, compliance, alerts modules

---

## Timeline Estimate

- WhatsApp webhook: 3-4 hours
- Phone mapping: 1 hour
- Permissions: 4-5 hours
- Route registration: 15 minutes
- Confidence updating: 1-2 hours
- Testing: 2-3 hours

**Total: ~12-16 hours of focused work**

This will make Phase-1 functional.
