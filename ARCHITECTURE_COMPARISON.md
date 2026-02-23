# BharatCompliance: Architecture - What You Have vs What You Need

---

## Current Architecture (What Exists)

```
┌─────────────────────────────────────────────────────────┐
│                    BharatCompliance                     │
│                    (Current State)                      │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐
│   Flask App      │
│  (app.py)        │
└────────┬─────────┘
         │
    ┌────┼──────────────────────────┐
    │    │                          │
    ▼    ▼                          ▼
┌─────────────────┐  ┌────────────────────┐  ┌──────────────────┐
│  Auth Routes    │  │  Org Routes        │  │  Business Routes │
│ ✅ Working      │  │ ✅ Working         │  │ ✅ Working       │
└────────┬────────┘  └────────┬───────────┘  └────────┬─────────┘
         │                    │                       │
         ▼                    ▼                       ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
    │ Auth Service │  │ Org Service  │  │ Business Service │
    │ ✅ Working   │  │ ✅ Working   │  │ ✅ Working       │
    └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
           │                 │                   │
           ▼                 ▼                   ▼
      ┌─────────────────────────────────────────────┐
      │         SQLAlchemy ORM                      │
      │  ✅ Database Properly Configured            │
      └─────────────────────────────────────────────┘
                         │
                         ▼
      ┌─────────────────────────────────────────────┐
      │  Database                                   │
      │  Tables:                                    │
      │    ✅ User                                  │
      │    ✅ Organization                          │
      │    ✅ Business                              │
      │    ❌ UserOrganizationPermission (missing)  │
      │    ❌ WhatsAppMessage (exists but empty)    │
      │    ❌ BusinessStatement (exists but empty)  │
      │    ❌ BusinessEvidence (exists but empty)   │
      └─────────────────────────────────────────────┘
```

---

## Missing Phase-1 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    WhatsApp Integration                          │
│                    ❌ COMPLETELY MISSING                         │
└──────────────────────────────────────────────────────────────────┘
         │
         │ (Should flow to →)
         ▼
┌──────────────────────────────────────────────────────────────────┐
│             WhatsApp Webhook Receiver                            │
│  modules/whatsapp/routes.py                                      │
│  ❌ EMPTY - Needs:                                               │
│     • GET /whatsapp/webhook - verification                       │
│     • POST /whatsapp/webhook - message receiver                  │
│     • Signature verification                                     │
│     • Phone number extraction                                    │
│     • Message routing logic                                      │
└──────────────────────────────────────────────────────────────────┘
         │
         │ lookup phone →
         ▼
┌──────────────────────────────────────────────────────────────────┐
│             Phone-to-Business Mapper                             │
│  ❌ MISSING Logic                                                │
│  Business.whatsapp_phone field ❌ MISSING                        │
│     Need to:                                                     │
│     1. Find business by phone number                             │
│     2. Handle unknown senders                                    │
│     3. Link message to correct business                          │
└──────────────────────────────────────────────────────────────────┘
         │
         ├─→ if text ─────────────────────┐
         │                                │
         ├─→ if image/media ────┐         │
         │                      │         │
         │                      ▼         ▼
         │              ┌────────────┐  ┌───────────────┐
         │              │  Download  │  │ Parse Text    │
         │              │ Media from │  │ Extract info  │
         │              │ WhatsApp   │  │ Create        │
         │              └────────┬───┘  │ Statement     │
         │                       │      └───────┬───────┘
         │                       │              │
         │                       ▼              ▼
         │              ┌──────────────────────────────┐
         │              │ Statement/Evidence Created   │
         │              │ ✅ Models exist             │
         │              │ ❌ APIs don't exist         │
         │              └──────────────────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────────────────┐
         │              │ OCR Processing               │
         │              │ ✅ Google Vision working     │
         │              │ ⚠️ Confidence not updating   │
         │              └──────────────────────────────┘
         │
         └──────────────────────────────────────────────────────┐
                                                                │
                                                                ▼
                                    ┌────────────────────────────────────┐
                                    │  CA Visibility APIs                │
                                    │  ❌ COMPLETELY MISSING             │
                                    │  Needs:                            │
                                    │  • GET /businesses/<id>/statements │
                                    │  • GET /businesses/<id>/evidence   │
                                    │  • GET /orgs/<id>/dashboard        │
                                    │  • Filtering, sorting, aggregation │
                                    └────────────────────────────────────┘
```

---

## Required Permission System (Missing)

```
┌──────────────────────────────────────────────────────────────┐
│                Permission System                             │
│                ❌ COMPLETELY MISSING                         │
└──────────────────────────────────────────────────────────────┘

Current State (BROKEN):
  Request to GET /businesses/org_1
     │
     └──► No permission check
     │
     └──► Any user can see any business
     │
     └──► DATA LEAK!

Required State (SECURE):
  Request to GET /businesses/org_1
     │
     ├──► Extract user_id from JWT
     │
     ├──► Query: Does user have access to org_1?
     │    SELECT * FROM UserOrganizationPermission
     │    WHERE user_id = X AND organization_id = org_1
     │
     ├──► If permission exists:
     │    └──► Return user's organizations' businesses
     │
     └──► If NO permission:
          └──► Return 403 Forbidden
```

---

## Required Permission Model (Missing)

```sql
-- NEW TABLE: UserOrganizationPermission
CREATE TABLE user_organization_permission (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL (FK: User),
    organization_id INTEGER NOT NULL (FK: Organization),
    role VARCHAR(50),  -- owner, manager, staff
    created_at TIMESTAMP,
    
    UNIQUE(user_id, organization_id)  -- One role per user per org
);

-- Business needs new fields:
ALTER TABLE business ADD COLUMN owner_user_id INTEGER (FK: User);
ALTER TABLE business ADD COLUMN whatsapp_phone VARCHAR(20) UNIQUE;

-- This enables:
-- 1. Phone → Business lookup (for webhook routing)
-- 2. User → Org access (for permission checking)
-- 3. Org → Business → Statements/Evidence flow
```

---

## Complete End-to-End Flow (What Should Happen)

```
┌─────────────────────────────────────────────────────────────┐
│  COMPLETE BHARATCOMPLIANCE FLOW (What Should Work)         │
└─────────────────────────────────────────────────────────────┘

1. SETUP PHASE
   ─────────
   CA signs up
   ↓
   CA creates organization
   ↓
   CA creates business for client "Tea Shop"
   ↓
   CA adds client WhatsApp: +919876543210
   ↓
   CA shares link/instructions with client


2. DATA INGESTION PHASE
   ───────────────────
   Client: Sends WhatsApp message "Today sale 8200 rupees"
   ↓
   WhatsApp Cloud API: Sends to POST /whatsapp/webhook
   ↓
   Webhook receiver: Verifies signature
   ↓
   Webhook handler: Extracts phone number +919876543210
   ↓
   Lookup: Find Business where whatsapp_phone = "919876543210"
   ↓ (Found: Business #42, Tea Shop)
   ↓
   Create WhatsAppMessage (raw storage)
   ↓
   Parse text: "Today sale 8200" → amount=8200, type=daily_sales
   ↓
   Create BusinessStatement:
      • business_id = 42
      • amount = 8200
      • confidence = low
      • source = whatsapp


3. EVIDENCE PROCESSING PHASE
   ────────────────────────
   If client sends image later:
   ↓
   WhatsApp: Sends image to POST /whatsapp/webhook
   ↓
   Download image from WhatsApp
   ↓
   Create BusinessEvidence:
      • business_id = 42
      • file_path = storage/uploads/xxxxx.jpg
      • source = whatsapp
      • status = uploaded
   ↓
   Quality check (Laplacian blur)
   ↓
   Run OCR with Google Vision
   ↓
   Extract: amount=8200, date=2024-01-09, gstin=FOUND
   ↓
   Update BusinessEvidence:
      • ocr_text = full extracted text
      • detected_amount = 8200
      • detected_gstin = XXXXXXXXXXXXX
      • status = usable
      • evidence_strength = strong
   ↓
   Update BusinessStatement:
      • confidence = high  ← NOW UPDATES!
      • confidence_reason = "OCR found amount + GSTIN"


4. CA VISIBILITY PHASE
   ───────────────────
   CA logs in
   ↓
   CA requests: GET /orgs/1/dashboard
   ↓
   Permission check: Is user member of org 1? ✓ YES
   ↓
   API returns:
   {
      "businesses": [
         {
            "id": 42,
            "name": "Tea Shop",
            "phone": "919876543210",
            "statements": 25,
            "strong_evidence": 8,
            "weak_evidence": 2,
            "monthly_turnover": 185000
         }
      ],
      "summary": {
         "total_businesses": 1,
         "strong_evidence_count": 8,
         "weak_evidence_count": 2,
         "total_turnover": 185000
      }
   }
   ↓
   CA requests: GET /businesses/42/statements
   ↓
   Permission check: Can user access business 42's org? ✓ YES
   ↓
   API returns all statements with confidence levels
   ↓
   CA requests: GET /businesses/42/evidence
   ↓
   API returns all evidence with OCR results and confidence
   ↓
   CA sees:
      • "Jan 9: ₹8200 sales (HIGH confidence - image has GSTIN)"
      • "Jan 8: ₹5500 expense (LOW confidence - handwritten)"
      • "Jan 7: ₹12000 sales (MEDIUM confidence - amount OCR'd)"
   ↓
   CA knows: This client is compliant and data is strong.
```

---

## Module Organization (What Should Exist)

### Current Structure
```
bc_core/modules/
├── auth/              ✅ COMPLETE
├── organizations/     ✅ COMPLETE
├── businesses/        ✅ MOSTLY COMPLETE (missing phone field)
├── whatsapp/          ❌ MOSTLY EMPTY
│   ├── models.py      ✅
│   ├── routes.py      ❌ EMPTY
│   ├── service.py     ⚠️ INCOMPLETE
│   └── webhook.py     ❌ EMPTY
├── statements/        ⚠️ INCOMPLETE
│   ├── models.py      ✅
│   ├── routes.py      ⚠️ MINIMAL (no POST/CREATE)
│   ├── parser.py      ⚠️ TOO SIMPLE
│   └── service.py     ✅ EXISTS
├── evidence/          ⚠️ INCOMPLETE
│   ├── models.py      ✅
│   ├── routes.py      ⚠️ ONLY UPLOAD
│   ├── quality.py     ✅
│   └── service.py     ✅
├── ocr/               ✅ MOSTLY COMPLETE
│   ├── client.py      ✅
│   ├── extractor.py   ✅
│   └── service.py     ⚠️ DOESN'T UPDATE CONFIDENCE
├── documents/         ❌ DELETE THIS (empty, wrong)
├── compliance/        ❌ DELETE THIS (Phase-2)
└── alerts/            ❌ DELETE THIS (Phase-2+)
```

### Required: New Compliance Module (for CA APIs)
```
bc_core/modules/compliance/  ← NEW (Phase-1)
├── __init__.py
├── routes.py           ← CA visibility APIs
│   ├── GET /orgs/<id>/dashboard
│   ├── GET /businesses/<id>/statements
│   ├── GET /businesses/<id>/evidence
│   └── GET /orgs/<id>/weak-evidence
├── service.py          ← Query logic
│   ├── get_org_dashboard()
│   ├── get_business_statements()
│   ├── get_business_evidence()
│   └── get_weak_evidence_alerts()
└── schemas.py          ← Response formatting
```

---

## Database Schema Comparison

### Current (What Exists)
```
User
├── id
├── name
├── email
├── password
├── role (CA, staff, client)  ← Too simple
└── created_at

Organization
├── id
├── name
├── owner_id (FK: User)
└── created_at

Business
├── id
├── org_id (FK: Organization)
├── name
├── business_type
├── state
├── gstin
├── pan
├── expected_turnover
└── created_at

WhatsAppMessage
├── id
├── business_id (FK: Business)
├── sender
├── message_type
├── raw_text
├── media_path
├── processed
└── created_at

BusinessStatement
├── id
├── business_id (FK: Business)
├── statement_type
├── raw_text
├── amount
├── currency
├── source
├── confidence_level (always "low")  ← Doesn't update!
└── created_at

BusinessEvidence
├── id
├── business_id (FK: Business)
├── statement_id (FK: BusinessStatement, optional)
├── file_name
├── file_path
├── evidence_type
├── source
├── quality_score
├── status
├── created_at
├── ocr_text
├── detected_amount
├── detected_date
└── detected_gstin
```

### Required (What's Missing)
```
ADD TO USER TABLE:
├── verified_at (optional - for email verification)
└── last_login

ADD: UserOrganizationPermission
├── id
├── user_id (FK: User)
├── organization_id (FK: Organization)
├── role (owner, manager, staff)
├── created_at
└── UNIQUE(user_id, organization_id)

ADD TO BUSINESS TABLE:
├── owner_user_id (FK: User, optional)  ← WHO OWNS THIS BUSINESS?
├── whatsapp_phone (unique)              ← CRITICAL FOR WEBHOOK!
├── verified_at
├── status (active, inactive, pending)
└── last_message_at

UPDATE BusinessStatement:
├── statement_date (separate from created_at)
├── confidence_reason (why is confidence what it is?)
├── marked_as_estimated (boolean)
├── manual_confidence_override (by CA review?)
└── evidence_links (array of evidence IDs)

UPDATE BusinessEvidence:
├── evidence_strength (strong, medium, weak)  ← CRITICAL!
├── confidence_reason (string explanation)
├── classified_type (auto-classified)
├── created_at
├── updated_at (for confidence updates)
└── ocr_status (pending, success, failed)
```

---

## Route Map

### Routes That Exist ✅
```
POST   /auth/register
POST   /auth/login
GET    /auth/me

POST   /orgs
GET    /orgs

POST   /businesses
GET    /businesses/<org_id>
```

### Routes That Should Exist But Don't ❌
```
# WhatsApp
GET    /whatsapp/webhook              ← Webhook verification
POST   /whatsapp/webhook              ← Receive messages

# Statements (partially)
POST   /statements                    ← Create via API
GET    /statements/business/<id>      ← Exists but not registered
GET    /statements/<id>               ← Get single
PUT    /statements/<id>               ← Update confidence (manual)

# Evidence (partially)
POST   /evidence/upload               ← Registered but missing webhook trigger
GET    /evidence/business/<id>        ← List business evidence
GET    /evidence/<id>                 ← Get single with OCR results
GET    /evidence/strength/<level>     ← Filter by strength

# Compliance - CA Dashboards (COMPLETELY MISSING)
GET    /compliance/orgs/<id>/dashboard
GET    /compliance/businesses/<id>/statements
GET    /compliance/businesses/<id>/evidence
GET    /compliance/orgs/<id>/weak-evidence
GET    /compliance/businesses/<id>/monthly-summary

# Permissions (COMPLETELY MISSING)
POST   /orgs/<id>/invite-user
DELETE /orgs/<id>/users/<user_id>
```

---

## The Path Forward

```
TODAY (Not Functional)
│
├─ Week 1: Unblock Phase-1
│  ├─ Implement WhatsApp webhook
│  ├─ Add phone-to-business mapping
│  ├─ Add permission system
│  └─ Register missing routes
│
├─ Week 2: Complete Phase-1
│  ├─ Build CA dashboards
│  ├─ Update confidence on OCR
│  ├─ Classify evidence strength
│  └─ Fix statement parser
│
└─ Week 3+: Polish & Launch
   ├─ Error handling
   ├─ Testing
   ├─ Security review
   └─ Beta launch
            │
            ▼
      FUNCTIONAL PRODUCT ✅
```

---

**That's the architecture overview. Ready to build?**
