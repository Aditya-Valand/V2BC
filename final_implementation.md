# BharatCompliance – Final Implementation Plan

**Version:** 1.0
**Audience:** Core dev team (2–3 engineers)
**Assumption:** Bootstrap budget. No VC. Ship fast, stay lean.
**Starting point:** Existing `bc_core/` Flask codebase is the foundation. We extend it — not rewrite.

---

## 1. Product Goal (First 90 Days)

### What "Working MVP" Means

A CA firm can:
1. Register, create their firm profile, and invite clients in under 10 minutes
2. Share a link/QR code with each client that gets them into the client app immediately
3. Watch clients enter daily sales, expenses, and bill photos from a guided in-app chat
4. See all client data in a clean web dashboard — sorted by compliance health
5. Get auto-generated filing prep summaries with all transactions listed and evidence attached
6. Send one-click deadline reminders to all or selected clients

A micro-business client can:
1. Open the app from the CA's invite link (no Google Play required — PWA)
2. Enter "today's sales" in 3 taps — guided, no freeform typing
3. Upload a bill photo that auto-fills the amount after OCR
4. See their own compliance status and next deadline

### What MVP Is NOT

- Not a GST filing tool (no GSTN portal integration)
- Not a lending or credit scoring product
- Not multi-language yet (English + Hindi labels only)
- Not a CA-client video/voice communication tool
- Not a full accounting ledger

### Success Metrics at 90 Days

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Paying CA firms | 5 (pilot, ₹0 but committed) | Validates product-market fit |
| Active client apps | 40+ (8 clients per CA avg) | Validates client adoption |
| Transactions entered via app | 500+ | Validates daily usage habit |
| Evidence (photos) uploaded | 200+ | Validates OCR pipeline |
| CA daily active sessions | 3+ per CA per week | Validates CA dashboard stickiness |
| Data accuracy complaint rate | <5% | Validates trust |
| Client app D7 retention | >50% | Validates UX simplicity |

**The one hard gate:** At least 3 CA firms must complete a full monthly filing cycle using BharatCompliance data before Day 90. If that hasn't happened, the product has not been validated.

---

## 2. MVP Feature Breakdown (Build Order)

Features are listed in exact build order. Do not jump ahead. Each feature unlocks the next.

---

### Feature 1: CA Firm Registration + Auth

**Purpose:**
Every other feature requires a CA firm account. This is the foundation. Get it right once.

**User Flow:**
```
CA visits web app
→ Clicks "Register your CA Firm"
→ Enters: Name, Email, Phone, Firm Name, City, State
→ Gets OTP on email (or phone — email preferred, cheaper)
→ Verifies OTP → Account created
→ Redirected to CA dashboard (empty state)
```

**Backend Components (modify existing `bc_core/modules/auth/`):**
- Extend `User` model: add `phone`, `fcm_token`, `last_login`, `language` fields
- Extend `Organization` model: add `city`, `state`, `license_number` (optional), `plan` (`free`, `paid`), `plan_expires_at`
- Fix `UserOrganizationPermission`: already exists in the codebase — ensure it is created automatically when CA registers (owner role)

**Database Changes:**
```sql
ALTER TABLE user ADD COLUMN phone VARCHAR(15);
ALTER TABLE user ADD COLUMN fcm_token TEXT;
ALTER TABLE user ADD COLUMN last_login TIMESTAMP;
ALTER TABLE user ADD COLUMN language VARCHAR(5) DEFAULT 'en';
ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN otp_code VARCHAR(10);
ALTER TABLE user ADD COLUMN otp_expires_at TIMESTAMP;

ALTER TABLE organization ADD COLUMN city VARCHAR(100);
ALTER TABLE organization ADD COLUMN state VARCHAR(100);
ALTER TABLE organization ADD COLUMN license_number VARCHAR(50);
ALTER TABLE organization ADD COLUMN plan VARCHAR(20) DEFAULT 'free';
ALTER TABLE organization ADD COLUMN plan_expires_at TIMESTAMP;
ALTER TABLE organization ADD COLUMN client_count INTEGER DEFAULT 0;
```

**APIs Required:**
- `POST /api/auth/register` — create user + org + org_member(owner)
- `POST /api/auth/verify-otp` — verify email OTP
- `POST /api/auth/login` — returns JWT access + refresh tokens
- `POST /api/auth/refresh` — rotate access token
- `GET /api/auth/me` — return user + org details

**Edge Cases:**
- Email already registered → return clear error, not a 500
- OTP expires after 10 minutes → resend endpoint needed
- CA registers without a firm name → block it (firm name is required for onboarding clients)
- Rate limit OTP requests to 3 per hour per email to prevent abuse

---

### Feature 2: Client Invite + Client PWA Registration

**Purpose:**
This is the core distribution mechanism. A CA creates a client record, gets a unique invite link, shares it. Client opens the link, registers, and is automatically bound to that CA firm. Without this working perfectly, nothing else matters.

**User Flow (CA side):**
```
CA opens dashboard → "Add Client"
→ Fills form: Client Name, Business Name, Business Type, City, Phone
→ System creates Client record + generates unique 8-char invite_code
→ CA sees invite link: https://app.bharatcompliance.in/join/XK9P2M7Q
→ CA sees QR code (auto-generated from that URL)
→ CA shares link/QR via their own WhatsApp (ironic but effective)
```

**User Flow (Client side):**
```
Client opens invite link on phone
→ Sees: "Your CA [Name] has invited you to BharatCompliance"
→ "Get Started" button
→ PWA install prompt appears ("Add to Home Screen")
→ Client enters: Name, Phone, sets 4-digit PIN (no email required)
→ Account linked to invite_code → bound to CA firm
→ Redirected to in-app chat welcome screen
```

**Key Decision:** Client does NOT need email. Phone + 4-digit PIN only. Email is friction they don't have. Phone OTP for verification.

**Backend Components (new module: `bc_core/modules/clients/`):**
- New `Client` model (replaces/extends `Business` — see schema section)
- `generate_invite_code()` — 8 uppercase alphanumeric, unique, indexed
- `accept_invite(code, user_data)` — validates code, creates user with role `client`, links to client record

**Database: New `clients` table (replaces `business` for new schema):**
```sql
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_user_id INTEGER REFERENCES users(id),

    -- Business info
    business_name VARCHAR(150) NOT NULL,
    owner_name VARCHAR(120),
    business_type VARCHAR(50) NOT NULL,  -- food, retail, service, gig, contractor
    sector VARCHAR(50),                  -- fssai_food, textile, construction, etc.
    city VARCHAR(100),
    state VARCHAR(100),
    pin_code VARCHAR(10),
    phone VARCHAR(15),

    -- Compliance identifiers (all optional at signup)
    gstin VARCHAR(20),
    pan VARCHAR(20),
    udyam_number VARCHAR(30),
    fssai_number VARCHAR(20),
    fssai_expiry DATE,

    -- Financial profile
    expected_monthly_turnover NUMERIC(12,2),
    gst_scheme VARCHAR(20) DEFAULT 'unregistered',  -- unregistered, regular, composition

    -- Invite system
    invite_code VARCHAR(8) UNIQUE NOT NULL,
    invite_accepted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'invited',  -- invited, active, inactive

    -- Computed compliance fields (updated by background job)
    compliance_score INTEGER DEFAULT NULL,
    last_transaction_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clients_org_id ON clients(org_id);
CREATE INDEX idx_clients_invite_code ON clients(invite_code);
CREATE INDEX idx_clients_status ON clients(status);
```

**APIs Required:**
- `POST /api/clients` — CA creates a client (returns invite_code + invite_url + QR code SVG)
- `GET /api/clients` — CA lists all their clients (with summary stats)
- `GET /api/clients/:id` — CA views single client detail
- `PUT /api/clients/:id` — CA edits client details
- `POST /api/invite/accept` — Client accepts invite (payload: `{invite_code, name, phone, pin}`)
- `POST /api/invite/verify-otp` — Client verifies phone OTP after invite accept
- `GET /api/invite/:code` — Public endpoint — returns CA name + client name (for the landing page before registration)

**Edge Cases:**
- Invite code used twice → second attempt gets "already registered" with login prompt
- Client on very slow internet → invite_code lookup should respond in <500ms (index on invite_code)
- CA accidentally creates duplicate client → unique constraint on `(org_id, phone)` — return "client with this phone exists in your firm"
- Client enters wrong OTP 3 times → lock for 30 minutes

---

### Feature 3: In-App Guided Chat (Client Data Entry)

**Purpose:**
This is the product's core differentiator. The micro-business owner should be able to record a day's transactions in under 60 seconds. Guided prompts prevent garbage input. This replaces WhatsApp parsing entirely.

**Principle:** Never show a blank text box. Always ask a specific question with a numeric keypad or pre-set options as the input method.

**User Flow (Daily Sales Entry):**
```
Client opens PWA
→ Chat screen shows last message from "BharatCompliance Bot"
→ "Good morning Ramesh! Ready to record today's transactions?"
→ [Quick replies: "Add Sales" | "Add Expense" | "View Summary"]

Client taps "Add Sales"
→ Chat: "What were your total sales today?"
→ [Numeric input field — large font, ₹ prefix, no keyboard]
→ Client enters: 8200
→ Chat: "Got it! ₹8,200 in sales. Want to add a bill photo as proof?"
→ [Yes, add photo | No, skip]

Client taps "Yes, add photo"
→ Camera opens → Client takes photo of bill
→ Photo uploaded → OCR runs in background
→ Chat: "Photo saved! Your entry is complete."
→ Entry shown as a card in chat history

If OCR finds different amount:
→ Chat: "Hmm, the bill photo shows ₹8,500. Which is correct?"
→ [₹8,200 (I entered) | ₹8,500 (from photo) | Enter different amount]
```

**User Flow (Expense Entry):**
```
Client taps "Add Expense"
→ Chat: "What type of expense?"
→ [Raw Material | Rent | Electricity | Labour | Other]
→ Client selects category
→ Chat: "How much did you spend?"
→ [Numeric input]
→ Chat: "Add a receipt photo?"
→ [Yes | No]
```

**Backend Components:**
- This is a **frontend-driven flow** — the "chat" is a sequence of UI states, not an AI chatbot
- Backend only receives the final structured payload, not raw conversational text
- No NLP required. No text parsing required. This is the crucial architectural decision.

**Chat message model (client-side state machine, not stored as chat):**
```
Each "conversation flow" is a JSON config defining steps:
{
  "flow": "daily_sales",
  "steps": [
    {"type": "amount_input", "label": "Total sales today?", "field": "amount"},
    {"type": "yes_no", "label": "Add bill photo?", "field": "has_evidence"},
    {"type": "camera", "label": "Take photo", "field": "evidence_file", "conditional": "has_evidence == yes"}
  ]
}
```
The PWA renders these steps as a chat-like sequence. Data is collected step by step. At the end, one API call is made with the complete structured payload.

**APIs Required:**
- `POST /api/transactions` — Create transaction (see Section 5 for full payload)
- `GET /api/my/transactions` — Client views their own transaction history
- `GET /api/my/summary` — Client views their own monthly summary

**Edge Cases:**
- Client enters 0 as amount → reject with "Amount must be greater than ₹0"
- Client enters amount with commas (8,200) → strip commas client-side before sending
- Client submits duplicate entry (same amount, same day, same type within 5 minutes) → warn "You already entered ₹8,200 sales today. Add another?"
- Client is offline when they tap submit → queue locally in localStorage, retry when online
- Photo is blurry → quality check returns score <40 → show "This photo is blurry. Please retake." before accepting

---

### Feature 4: Evidence Upload + OCR Pipeline

**Purpose:**
Bill photos turn unverifiable numbers into auditable evidence. OCR eliminates manual extraction. Together, they are what separates BharatCompliance from a basic ledger.

**User Flow:**
```
Client takes photo in app
→ PWA uploads to backend → /api/evidence/upload
→ Backend saves to Cloudinary (CDN URL returned)
→ Background job triggered: quality_check → ocr_extract
→ OCR result returned to client in ~3 seconds
→ If OCR amount differs from entered amount → flag to client
→ CA sees evidence linked to transaction in dashboard
```

**OCR Pipeline (keep existing Gemini Vision integration):**

```
Image received
    │
    ▼
Quality Check (Laplacian blur score)
    │
    ├── Score < 30 → reject immediately ("photo too blurry")
    ├── Score 30-60 → accept but mark as "low_quality"
    └── Score > 60 → mark as "usable"
    │
    ▼
Gemini Vision API call
Prompt: "Extract from this Indian business document:
1. total_amount (number only, no currency symbol)
2. document_date (YYYY-MM-DD, null if not visible)
3. gstin (15-char alphanumeric, null if not visible)
4. vendor_name (string, null if not visible)
5. document_type (invoice/receipt/bill/handwritten/unknown)
Return JSON only. No explanation."
    │
    ▼
Parse JSON response
    │
    ├── amount extracted → confidence = "medium"
    ├── amount + gstin extracted → confidence = "high"
    ├── amount + gstin + date → confidence = "high", strength = "strong"
    └── nothing extracted → confidence = "low", strength = "weak"
    │
    ▼
Update evidence record
Update linked transaction confidence
```

**Backend Components (modify `bc_core/modules/evidence/`):**
- `quality.py` — existing Laplacian blur detection, keep as-is
- `ocr_service.py` — replace Google Vision call with Gemini Vision (already in requirements.txt as `google-genai`)
- Make OCR async: use a simple background thread (no Celery needed for MVP — Celery is overkill until 100+ CA firms)

**Simple async approach for MVP (no Celery required):**
```python
# In evidence/routes.py — after saving file, run OCR in background thread
import threading

def run_ocr_background(evidence_id, file_url):
    with app.app_context():
        run_ocr_and_update(evidence_id, file_url)

thread = threading.Thread(target=run_ocr_background, args=(evidence.id, file_url))
thread.daemon = True
thread.start()
```
This is good enough for 50 concurrent users. Replace with Celery when needed.

**File Storage Decision — Cloudinary (free tier):**
- 25GB storage free, 25GB bandwidth free per month
- Built-in CDN, image optimization
- Direct upload from browser using signed upload preset (bypass your server for the file bytes)
- Returns a `secure_url` you store in DB

**Database: `evidence` table:**
```sql
CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    transaction_id INTEGER REFERENCES transactions(id),
    uploaded_by INTEGER NOT NULL REFERENCES users(id),

    -- File
    cloudinary_public_id VARCHAR(255),
    file_url TEXT NOT NULL,
    file_type VARCHAR(50),        -- image/jpeg, image/png, application/pdf
    file_size_bytes INTEGER,

    -- Quality
    quality_score INTEGER,         -- 0-100 Laplacian score
    quality_status VARCHAR(20),    -- usable, low_quality, rejected

    -- OCR
    ocr_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, success, failed
    ocr_raw_text TEXT,
    ocr_amount NUMERIC(12,2),
    ocr_date DATE,
    ocr_gstin VARCHAR(20),
    ocr_vendor_name VARCHAR(150),
    ocr_document_type VARCHAR(50),
    ocr_confidence VARCHAR(20),    -- low, medium, high

    -- Computed strength
    strength VARCHAR(20),          -- strong, medium, weak
    strength_reason TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_evidence_client_id ON evidence(client_id);
CREATE INDEX idx_evidence_transaction_id ON evidence(transaction_id);
CREATE INDEX idx_evidence_ocr_status ON evidence(ocr_status);
```

**APIs Required:**
- `POST /api/evidence/upload` — receives file, saves to Cloudinary, kicks off async OCR
- `GET /api/evidence/:id` — returns evidence with OCR results (client polls this to show OCR outcome)
- `GET /api/clients/:id/evidence` — CA views all evidence for a client, filterable by strength

**Edge Cases:**
- Cloudinary upload fails → save locally as fallback, retry Cloudinary upload on next request
- OCR returns invalid JSON → catch parse error, mark ocr_status = 'failed', store raw response for debugging
- PDF uploaded instead of image → Gemini Vision can handle PDFs, but limit to 10MB
- Client uploads same photo twice → hash the file on client side, check against existing hashes before uploading

---

### Feature 5: CA Web Dashboard

**Purpose:**
This is what CA firms pay for. Every other feature feeds into this screen. The dashboard must answer "which client needs my attention right now?" in under 3 seconds of looking at it.

**Dashboard screens (3 only, in priority order):**

**Screen 1: Overview (default landing)**
```
┌─────────────────────────────────────────────────────────────┐
│  BharatCompliance    [Sharma & Associates CA Firm]   [Logout]│
├─────────────────────────────────────────────────────────────┤
│  OVERVIEW          CLIENTS          DEADLINES                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  12 Clients   |   8 Active   |   3 Attention Needed         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ CLIENT          STATUS    LAST ENTRY   DEADLINE       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🔴 Ramesh Tea Shop  Missing 5d   Jan 14   GSTR Jan 20 │   │
│  │ 🟡 Priya Tiffin     2d ago       Jan 18   7 days      │   │
│  │ 🟢 Ahmed Tailor     Today        Jan 20   18 days     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  [Send Reminders to All]        [Add New Client]             │
└─────────────────────────────────────────────────────────────┘
```

Color logic:
- 🔴 Red: No transaction in 5+ days AND deadline within 10 days
- 🟡 Yellow: No transaction in 3+ days OR deadline within 7 days
- 🟢 Green: Transaction in last 2 days, deadline >7 days away

**Screen 2: Client Detail View**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    Ramesh Tea Shop    🔴 Attention Needed            │
├─────────────────────────────────────────────────────────────┤
│  Monthly Sales: ₹1,24,500   Expenses: ₹38,200               │
│  Transactions: 18   With Evidence: 12   Without: 6          │
│  Evidence Quality: Strong 8 | Medium 3 | Weak 1             │
├─────────────────────────────────────────────────────────────┤
│  NEXT DEADLINE: GSTR-3B — January 20 (5 days)               │
│  [Prepare Filing Summary]  [Send Reminder]                  │
├─────────────────────────────────────────────────────────────┤
│  TRANSACTIONS                                               │
│  Jan 20  Sale  ₹6,200  🟢 High confidence (bill photo)      │
│  Jan 19  Sale  ₹4,800  🟡 Medium (manual entry)             │
│  Jan 18  Expense ₹1,200  🟡 Medium (photo, low quality)     │
│  Jan 15  Sale  ₹9,100  🟢 High confidence (bill + GSTIN)    │
└─────────────────────────────────────────────────────────────┘
```

**Screen 3: Filing Summary (most commercially important)**
```
┌─────────────────────────────────────────────────────────────┐
│  Filing Summary — Ramesh Tea Shop — January 2025            │
├─────────────────────────────────────────────────────────────┤
│  Total Sales:    ₹1,24,500  (18 entries, 12 with evidence)  │
│  Total Expenses: ₹38,200   (9 entries, 7 with evidence)     │
│  Net Turnover:   ₹86,300                                    │
│  Tax Liability:  ₹[calculated based on GST scheme]          │
├─────────────────────────────────────────────────────────────┤
│  DATA CONFIDENCE                                            │
│  Strong evidence (OCR+GSTIN): 8 transactions               │
│  Medium evidence (OCR only):  7 transactions               │
│  Weak (manual, no evidence):  3 transactions — REVIEW       │
├─────────────────────────────────────────────────────────────┤
│  [Download Excel]    [Download PDF]    [Mark as Filed]      │
└─────────────────────────────────────────────────────────────┘
```

**Backend APIs Required:**
- `GET /api/dashboard` — Returns org summary (total clients, counts by status color)
- `GET /api/clients/:id/detail` — Returns full client detail with transaction list and stats
- `GET /api/clients/:id/filing-summary?month=2025-01` — Generates filing summary data
- `GET /api/clients/:id/filing-summary/export?format=excel` — Returns Excel file
- `POST /api/reminders/send` — Sends push notification reminder to selected clients

**Frontend Stack (CA Dashboard):**
React.js + TailwindCSS, served as a static SPA from a CDN or Render.
Do NOT use Flask templates for the CA dashboard — the data updates need to feel responsive.

---

### Feature 6: Compliance Calendar + Deadline Management

**Purpose:**
This is the feature that makes CAs *stay* on the product. It removes the single biggest daily pain: tracking who is due for what filing and when.

**Hard-coded Indian Compliance Dates (Year 1 scope):**
```python
COMPLIANCE_DEADLINES = {
    "gstr1_monthly": {  # Regular scheme, monthly filer (>₹5 crore turnover)
        "day_of_month": 11,
        "applicable_to": ["regular"],
        "description": "GSTR-1 Monthly Filing"
    },
    "gstr1_quarterly": {  # QRMP scheme
        "quarter_end_months": [3, 6, 9, 12],
        "filing_by_month_offset": 1,
        "day_of_month": 13,
        "applicable_to": ["regular_quarterly"],
        "description": "GSTR-1 Quarterly (QRMP)"
    },
    "gstr3b": {  # All regular filers
        "day_of_month": 20,
        "applicable_to": ["regular", "regular_quarterly"],
        "description": "GSTR-3B Filing"
    },
    "cmp08": {  # Composition scheme — quarterly
        "quarter_end_months": [3, 6, 9, 12],
        "filing_by_month_offset": 1,
        "day_of_month": 18,
        "applicable_to": ["composition"],
        "description": "CMP-08 Composition Quarterly Return"
    },
    "advance_tax_q1": {"date": "June 15", "description": "Advance Tax Q1"},
    "advance_tax_q2": {"date": "September 15", "description": "Advance Tax Q2"},
    "advance_tax_q3": {"date": "December 15", "description": "Advance Tax Q3"},
    "advance_tax_q4": {"date": "March 15", "description": "Advance Tax Q4"},
    "fssai_renewal": {  # Based on fssai_expiry date per client
        "days_before": 30,
        "applicable_to_sector": "food",
        "description": "FSSAI License Renewal"
    }
}
```

**Deadline generation logic:**
When a client is created, a background job generates the next 12 months of applicable deadlines based on their `gst_scheme` and `sector` and inserts them into the `compliance_deadlines` table.

**Database: `compliance_deadlines` table:**
```sql
CREATE TABLE compliance_deadlines (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id),

    deadline_type VARCHAR(50) NOT NULL,  -- gstr1_monthly, gstr3b, cmp08, etc.
    description VARCHAR(150),
    due_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,

    status VARCHAR(20) DEFAULT 'pending',  -- pending, reminded, acknowledged, completed, missed
    reminder_sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,           -- client tapped "Got it" in app
    completed_at TIMESTAMP,
    completed_by INTEGER REFERENCES users(id),

    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deadlines_client_id ON compliance_deadlines(client_id);
CREATE INDEX idx_deadlines_due_date ON compliance_deadlines(due_date);
CREATE INDEX idx_deadlines_status ON compliance_deadlines(status);
```

**Reminder System:**

Automated reminders run via a daily scheduled job (APScheduler — already in Python, no external service needed):
```
Daily at 9:00 AM IST:
  → Find all deadlines where due_date is in 7 days AND status = 'pending'
  → Send push notification to each client: "Your GSTR-3B is due Jan 20. Tap to review."
  → Find all deadlines where due_date is in 3 days AND status != 'completed'
  → Send push notification: "URGENT: GSTR-3B due in 3 days."
  → Update reminder_sent_at
```

Push notification: Firebase Cloud Messaging (FCM) — completely free, works on Android PWA.

**APIs Required:**
- `GET /api/clients/:id/deadlines` — Returns all deadlines for a client
- `GET /api/deadlines/upcoming` — CA view: deadlines for all clients in next 30 days
- `POST /api/deadlines/:id/complete` — CA marks a deadline as completed
- `POST /api/deadlines/:id/acknowledge` — Client acknowledges a reminder
- `POST /api/reminders/send-bulk` — CA triggers immediate reminder to selected clients

---

### Feature 7: Data Validation + Anomaly Detection

**Purpose:**
CAs must trust the data before they use it for filing. Automated anomaly flags catch client errors before they become compliance problems. This is the feature that converts a skeptical CA into a confident daily user.

**Validation rules (server-side on transaction creation):**

```python
VALIDATION_RULES = [
    {
        "name": "amount_range",
        "check": lambda amount, client: amount > 0 and amount < 10_000_000,
        "warning": "Amount ₹{amount} seems unusually high. Please confirm."
    },
    {
        "name": "outlier_detection",
        "check": lambda amount, client: not is_outlier(amount, client.id),
        # is_outlier = True if amount > 5x rolling 30-day average for same type
        "warning": "This is much higher than your usual daily sales. Please confirm."
    },
    {
        "name": "duplicate_detection",
        "check": lambda amount, type, client, date: not has_duplicate(amount, type, client.id, date),
        # has_duplicate = True if same amount+type exists within same day
        "warning": "You already entered ₹{amount} {type} today. Add another?"
    },
    {
        "name": "future_date",
        "check": lambda date: date <= today(),
        "warning": "Transaction date cannot be in the future."
    },
    {
        "name": "gap_detection",
        # Not a per-transaction check — runs daily as a batch job
        # Alerts CA if client has >3 days gap in daily_sales entries
        "type": "batch"
    }
]
```

Validation returns a `warnings` array in the API response — not errors. The client can override warnings and submit anyway. This preserves flexibility while surfacing issues.

---

## 3. Technical Architecture

### Backend

**Framework:** Flask (keep existing `bc_core/`)
Why: Already built, team knows it, switching to FastAPI gains nothing at this scale.

**Database:** PostgreSQL via Supabase
Why: Supabase free tier gives 500MB storage, 2GB bandwidth, daily backups — sufficient for 6 months. Connection pooler built-in. If you outgrow it, $25/month tier handles 10,000+ CA firms.
Migration: Switch SQLite → PostgreSQL is one config line change. Do it on Day 1.

**Auth:** Flask-JWT-Extended (keep existing)
Access token: 1 hour expiry. Refresh token: 30 days.
Add: `jti` (JWT ID) to a blocklist table for logout invalidation.

**File Storage:** Cloudinary
Why: Free tier covers MVP entirely. Built-in image optimization helps OCR quality. CDN serves images fast on mobile.
Alternative if Cloudinary paid plan needed: Supabase Storage (already in your infra).

**OCR:** Gemini Vision API (keep existing `google-genai` library)
Why: Already integrated, better than Google Cloud Vision for unstructured Indian bill formats, handles Hindi text.
Cost: Gemini 1.5 Flash is $0.075 per 1M tokens. A bill photo OCR call is ~1,000 tokens. 1,000 photos/month = $0.075. Negligible.

**Async Tasks:** Python threading for MVP (no Celery)
Why: Celery requires Redis ($5-10/month extra). Python daemon threads are sufficient until you hit 50+ concurrent OCR requests. Add Celery at 100 CA firms.

**Scheduled Jobs:** APScheduler (add to requirements.txt)
Why: Pure Python, no extra infrastructure. Runs inside your Flask process. Handles the daily reminder job, gap detection, and deadline generation.

**Push Notifications:** Firebase Cloud Messaging (FCM) — free
Client PWA receives push via service worker.

**Email:** Resend (resend.com) — free tier: 3,000 emails/month
Use for: CA registration OTP, weekly summary emails to CAs.

**Deployment:** Railway.app
Why: $5/month for a Flask app. PostgreSQL add-on is $5/month. Total infrastructure cost: $10/month. Render is fine too but Railway has better DX for backend-only services.

---

### Frontend

**CA Dashboard:** React.js (Vite) + TailwindCSS
Why: CA dashboard needs reactive updates (live client status, data changes). Flask/Jinja2 templates will require full page reloads — unacceptable for a dashboard.
Deploy: Vercel free tier (static SPA).

**Client App:** Progressive Web App (PWA)
Why: No Google Play approval (which takes 2-7 days and requires policy compliance). Instant updates without app store review. Works on any Android Chrome browser. Users add to home screen.
Implementation: React (same codebase, different route). Add `manifest.json` + service worker.
The single biggest reason: your first 40 clients need to be onboarded in week 7-8 of development. A PWA is live the moment the URL is shared.

---

### Full Architecture Flow

```
┌────────────────────────────────────────────────────────────┐
│                    CLIENT PWA (React)                       │
│  Guided Chat UI → Form Data → REST API calls               │
│  Service Worker → FCM Push Notifications                   │
└─────────────────────────┬──────────────────────────────────┘
                          │ HTTPS REST
┌─────────────────────────▼──────────────────────────────────┐
│                    CA WEB DASHBOARD (React)                 │
│  Client List → Detail → Filing Summary → Export            │
└─────────────────────────┬──────────────────────────────────┘
                          │ HTTPS REST
┌─────────────────────────▼──────────────────────────────────┐
│                  FLASK BACKEND (bc_core/)                   │
│                                                            │
│  auth/  clients/  transactions/  evidence/  dashboard/     │
│  deadlines/  notifications/  filing/                       │
│                          │                                 │
│  ┌───────────────────────┼────────────────────────────┐    │
│  │                       │                            │    │
│  ▼                       ▼                            ▼    │
│ PostgreSQL          Cloudinary                   Gemini     │
│ (Supabase)         (File Storage)             Vision API   │
│                                                            │
│  APScheduler (daily reminders + gap detection)             │
│  FCM (push notifications)                                  │
│  Resend (email OTPs)                                        │
└────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema (Initial Version)

Migration strategy: Create fresh migrations for the new schema. The existing Alembic setup in `bc_core/migrations/` handles this. Tables `user` and `organization` are extended; `business` is replaced by `clients`.

---

### Full Schema

```sql
-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) UNIQUE,               -- CA users must have email
    phone VARCHAR(15) UNIQUE,                -- Client users phone-only
    password_hash VARCHAR(255) NOT NULL,
    pin_hash VARCHAR(255),                   -- 4-digit PIN for clients
    role VARCHAR(20) NOT NULL,               -- ca_owner, ca_staff, client

    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    otp_code VARCHAR(10),
    otp_expires_at TIMESTAMP,

    -- App state
    fcm_token TEXT,                          -- Firebase push token
    language VARCHAR(5) DEFAULT 'en',
    last_login TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX idx_users_phone ON users(phone) WHERE phone IS NOT NULL;

-- ============================================================
-- ORGANIZATIONS (CA Firms)
-- ============================================================
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),

    -- Firm details
    city VARCHAR(100),
    state VARCHAR(100),
    license_number VARCHAR(50),              -- ICAI membership number (optional)

    -- Plan
    plan VARCHAR(20) DEFAULT 'free',         -- free, paid
    plan_expires_at TIMESTAMP,
    client_count INTEGER DEFAULT 0,          -- denormalized, updated on insert

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- ORG MEMBERS (Permission table)
-- ============================================================
CREATE TABLE org_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,               -- owner, manager, staff
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, org_id)
);

CREATE INDEX idx_org_members_org_id ON org_members(org_id);
CREATE INDEX idx_org_members_user_id ON org_members(user_id);

-- ============================================================
-- CLIENTS (micro-businesses managed by CA firm)
-- ============================================================
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_user_id INTEGER REFERENCES users(id),  -- set when invite accepted

    -- Business identity
    business_name VARCHAR(150) NOT NULL,
    owner_name VARCHAR(120),
    business_type VARCHAR(50) NOT NULL,
    -- Allowed: food_vendor, retailer, service_provider, gig_worker,
    --          contractor, manufacturer, freelancer, other
    sector VARCHAR(50),
    -- Allowed: fssai_food, textile, construction, logistics, hospitality, other

    -- Location
    city VARCHAR(100),
    state VARCHAR(100),
    pin_code VARCHAR(10),
    phone VARCHAR(15),

    -- Compliance identifiers (all optional at signup)
    gstin VARCHAR(20),
    pan VARCHAR(20),
    udyam_number VARCHAR(30),
    fssai_number VARCHAR(20),
    fssai_expiry DATE,

    -- Financial profile
    expected_monthly_turnover NUMERIC(12,2),
    gst_scheme VARCHAR(30) DEFAULT 'unregistered',
    -- Allowed: unregistered, regular, regular_quarterly, composition

    -- Invite & onboarding
    invite_code VARCHAR(8) UNIQUE NOT NULL,
    invite_accepted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'invited',    -- invited, active, inactive

    -- Computed (updated by background job nightly)
    compliance_score INTEGER,               -- 0-100
    last_transaction_at TIMESTAMP,
    monthly_turnover_cache NUMERIC(12,2),   -- current month, refreshed daily

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clients_org_id ON clients(org_id);
CREATE UNIQUE INDEX idx_clients_invite_code ON clients(invite_code);
CREATE INDEX idx_clients_status ON clients(status);
CREATE UNIQUE INDEX idx_clients_org_phone ON clients(org_id, phone)
    WHERE phone IS NOT NULL;

-- ============================================================
-- TRANSACTIONS
-- ============================================================
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id),  -- denormalized for faster CA queries
    entered_by INTEGER NOT NULL REFERENCES users(id),

    -- Transaction data
    type VARCHAR(30) NOT NULL,
    -- Allowed: sale, expense, purchase, salary_paid, loan_received, other
    category VARCHAR(50),
    -- For expenses: raw_material, rent, electricity, labour, transport, other
    amount NUMERIC(12,2) NOT NULL,
    currency CHAR(3) DEFAULT 'INR',
    transaction_date DATE NOT NULL,
    description TEXT,

    -- Source & confidence
    source VARCHAR(30) DEFAULT 'app_chat',
    -- Allowed: app_chat, manual_ca, import
    confidence VARCHAR(20) DEFAULT 'low',    -- low, medium, high
    confidence_reason TEXT,
    is_estimated BOOLEAN DEFAULT FALSE,

    -- CA review
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    ca_note TEXT,

    -- Anomaly flags (set at creation, cleared when CA reviews)
    anomaly_flags JSONB DEFAULT '[]',
    -- Example: [{"type": "outlier", "message": "5x higher than 30-day avg"}]

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_client_id ON transactions(client_id);
CREATE INDEX idx_transactions_org_id ON transactions(org_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_type ON transactions(type);

-- ============================================================
-- EVIDENCE (bill photos, receipts)
-- ============================================================
CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    uploaded_by INTEGER NOT NULL REFERENCES users(id),

    -- File storage
    cloudinary_public_id VARCHAR(255),
    file_url TEXT NOT NULL,
    thumbnail_url TEXT,
    file_type VARCHAR(50),
    file_size_bytes INTEGER,

    -- Quality check
    quality_score INTEGER,                   -- 0-100
    quality_status VARCHAR(20),              -- usable, low_quality, rejected

    -- OCR results
    ocr_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, success, failed, skipped
    ocr_raw_text TEXT,
    ocr_amount NUMERIC(12,2),
    ocr_date DATE,
    ocr_gstin VARCHAR(20),
    ocr_vendor_name VARCHAR(150),
    ocr_document_type VARCHAR(50),
    ocr_confidence VARCHAR(20),
    ocr_processed_at TIMESTAMP,

    -- Evidence strength (computed from quality + OCR)
    strength VARCHAR(20),                    -- strong, medium, weak
    strength_reason TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_evidence_client_id ON evidence(client_id);
CREATE INDEX idx_evidence_transaction_id ON evidence(transaction_id);
CREATE INDEX idx_evidence_ocr_status ON evidence(ocr_status) WHERE ocr_status = 'pending';

-- ============================================================
-- COMPLIANCE DEADLINES
-- ============================================================
CREATE TABLE compliance_deadlines (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id),

    deadline_type VARCHAR(50) NOT NULL,
    description VARCHAR(150),
    due_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,

    status VARCHAR(20) DEFAULT 'pending',
    -- Allowed: pending, reminded, acknowledged, completed, missed

    reminder_sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    completed_at TIMESTAMP,
    completed_by INTEGER REFERENCES users(id),
    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deadlines_client_id ON compliance_deadlines(client_id);
CREATE INDEX idx_deadlines_due_date ON compliance_deadlines(due_date);
CREATE INDEX idx_deadlines_org_upcoming ON compliance_deadlines(org_id, due_date)
    WHERE status NOT IN ('completed', 'missed');

-- ============================================================
-- ALERTS (system-generated, shown in CA dashboard)
-- ============================================================
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    org_id INTEGER NOT NULL REFERENCES organizations(id),

    alert_type VARCHAR(50) NOT NULL,
    -- Allowed: missing_data, deadline_approaching, deadline_overdue,
    --          anomaly_detected, threshold_warning, fssai_expiry, ocr_mismatch

    severity VARCHAR(20) NOT NULL,           -- info, warning, critical
    title VARCHAR(150) NOT NULL,
    message TEXT,

    is_read BOOLEAN DEFAULT FALSE,
    read_by INTEGER REFERENCES users(id),
    read_at TIMESTAMP,
    auto_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,

    metadata JSONB DEFAULT '{}',
    -- Stores context: {"days_missing": 5, "amount": 8200, etc.}

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alerts_org_id ON alerts(org_id);
CREATE INDEX idx_alerts_unread ON alerts(org_id, is_read) WHERE is_read = FALSE;

-- ============================================================
-- FILING SUMMARIES (generated, not manually created)
-- ============================================================
CREATE TABLE filing_summaries (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    generated_by INTEGER NOT NULL REFERENCES users(id),

    period VARCHAR(10) NOT NULL,             -- '2025-01' for Jan 2025
    filing_type VARCHAR(30) NOT NULL,        -- gstr1, gstr3b, cmp08, advance_tax

    -- Computed totals
    total_sales NUMERIC(12,2) DEFAULT 0,
    total_expenses NUMERIC(12,2) DEFAULT 0,
    total_purchases NUMERIC(12,2) DEFAULT 0,
    estimated_tax_liability NUMERIC(12,2),

    -- Confidence breakdown
    high_confidence_count INTEGER DEFAULT 0,
    medium_confidence_count INTEGER DEFAULT 0,
    low_confidence_count INTEGER DEFAULT 0,
    total_transaction_count INTEGER DEFAULT 0,
    evidence_attached_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'draft',      -- draft, exported, filed
    exported_at TIMESTAMP,
    filed_at TIMESTAMP,
    filed_by INTEGER REFERENCES users(id),

    -- Snapshot of transactions at time of generation (JSONB)
    transactions_snapshot JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_filing_summaries_client_period ON filing_summaries(client_id, period);

-- ============================================================
-- AUDIT LOG (immutable record of all CA actions)
-- ============================================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    org_id INTEGER REFERENCES organizations(id),

    action VARCHAR(50) NOT NULL,
    -- Allowed: login, create_client, edit_transaction, delete_transaction,
    --          mark_filed, export_summary, send_reminder, etc.

    entity_type VARCHAR(50),                 -- client, transaction, evidence, deadline
    entity_id INTEGER,

    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (created_at);
-- Partition by month for performance. Create partitions quarterly.

CREATE INDEX idx_audit_org_id ON audit_logs(org_id, created_at DESC);

-- ============================================================
-- JWT BLOCKLIST (for logout)
-- ============================================================
CREATE TABLE jwt_blocklist (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(36) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jwt_blocklist_jti ON jwt_blocklist(jti);
-- Run cleanup job weekly: DELETE FROM jwt_blocklist WHERE expires_at < NOW()
```

### Permission Rules (enforced in middleware, not just DB)

```
RULE 1: A user can only access data within their org_id.
  Enforcement: Every API route that touches client/transaction/evidence
  data must verify: org_members WHERE user_id = jwt_identity AND org_id = requested_org_id

RULE 2: A 'client' role user can only read/write their own client record.
  Enforcement: transactions WHERE client_id = user.client_id only.

RULE 3: Only 'ca_owner' or 'ca_staff' can mark transactions as verified.
  Enforcement: role check on PUT /api/transactions/:id/verify

RULE 4: Only 'ca_owner' can invite new users to the org or delete clients.
  Enforcement: role check on POST /api/clients, DELETE /api/clients/:id

RULE 5: Audit log is append-only. No UPDATE or DELETE on audit_logs.
  Enforcement: No route exposes update/delete on audit_logs table.
```

---

## 5. API Design (Core Endpoints)

Base URL: `https://api.bharatcompliance.in/api/v1`
Auth: Bearer JWT in Authorization header for all protected routes.
All responses use: `{"success": true/false, "data": {...}, "error": null/"message"}`

---

### 5.1 Auth Endpoints

```
POST /auth/register
────────────────────────────────
Request:
{
  "name": "Rajesh Sharma",
  "email": "rajesh@sharmaandco.in",
  "phone": "9876543210",
  "password": "SecurePass123",
  "firm_name": "Sharma & Associates",
  "city": "Pune",
  "state": "Maharashtra"
}

Response 201:
{
  "success": true,
  "data": {
    "user_id": 1,
    "org_id": 1,
    "message": "OTP sent to rajesh@sharmaandco.in"
  }
}

Validation errors → 400:
  - email already exists: "An account with this email already exists"
  - firm_name missing: "Firm name is required"
```

```
POST /auth/verify-otp
────────────────────────────────
Request:
{
  "user_id": 1,
  "otp": "847291"
}

Response 200:
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": {"id": 1, "name": "Rajesh Sharma", "role": "ca_owner"},
    "org": {"id": 1, "name": "Sharma & Associates"}
  }
}
```

```
POST /auth/login
────────────────────────────────
Request: {"email": "rajesh@sharmaandco.in", "password": "SecurePass123"}

Response 200: (same structure as verify-otp response)

Error 401: "Invalid email or password"  ← never say which is wrong
```

```
POST /auth/client-login  (for PWA client app)
────────────────────────────────
Request: {"phone": "9988776655", "pin": "4821"}

Response 200: access_token with role=client, client_id in JWT payload
```

```
POST /auth/logout
────────────────────────────────
Auth: Required
Adds current JWT jti to blocklist.
Response 200: {"success": true}
```

---

### 5.2 Client Management Endpoints (CA-facing)

```
POST /clients
────────────────────────────────
Auth: ca_owner or ca_staff
Request:
{
  "business_name": "Ramesh Tea Shop",
  "owner_name": "Ramesh Kumar",
  "business_type": "food_vendor",
  "sector": "fssai_food",
  "city": "Pune",
  "state": "Maharashtra",
  "phone": "9988776655",
  "expected_monthly_turnover": 80000,
  "gst_scheme": "unregistered",
  "gstin": null,
  "fssai_number": "12345678901234",
  "fssai_expiry": "2025-08-31"
}

Response 201:
{
  "success": true,
  "data": {
    "client_id": 42,
    "invite_code": "XK9P2M7Q",
    "invite_url": "https://app.bharatcompliance.in/join/XK9P2M7Q",
    "invite_qr_svg": "<svg>...</svg>",
    "deadlines_generated": 8
  }
}
```

```
GET /clients
────────────────────────────────
Auth: ca_owner or ca_staff
Query params: ?status=active&sort=compliance_score&order=asc

Response 200:
{
  "success": true,
  "data": {
    "total": 12,
    "clients": [
      {
        "id": 42,
        "business_name": "Ramesh Tea Shop",
        "status": "active",
        "compliance_color": "red",     // red, yellow, green
        "compliance_score": 45,
        "last_transaction_at": "2025-01-14T18:30:00Z",
        "days_since_last_entry": 5,
        "next_deadline": {
          "type": "gstr3b",
          "due_date": "2025-01-20",
          "days_remaining": 6
        },
        "monthly_turnover": 62500,
        "transaction_count_this_month": 14
      }
    ]
  }
}
```

```
GET /clients/:id
────────────────────────────────
Auth: ca_owner or ca_staff (must belong to same org as client)
Response 200: Full client record + stats + recent transactions (last 10)
```

```
GET /clients/:id/transactions
────────────────────────────────
Auth: ca_owner or ca_staff
Query: ?month=2025-01&type=sale&confidence=low&page=1&per_page=50

Response 200:
{
  "data": {
    "period": "2025-01",
    "totals": {
      "sales": 124500,
      "expenses": 38200,
      "purchases": 0,
      "net": 86300
    },
    "transactions": [
      {
        "id": 201,
        "type": "sale",
        "amount": 6200,
        "transaction_date": "2025-01-20",
        "confidence": "high",
        "confidence_reason": "OCR confirmed amount + GSTIN found",
        "is_verified": false,
        "anomaly_flags": [],
        "evidence": {
          "id": 88,
          "thumbnail_url": "https://res.cloudinary.com/...",
          "strength": "strong",
          "ocr_amount": 6200
        }
      }
    ]
  }
}
```

---

### 5.3 Transaction Endpoints (Client PWA)

```
POST /transactions
────────────────────────────────
Auth: client role
Request:
{
  "type": "sale",
  "category": null,
  "amount": 8200,
  "transaction_date": "2025-01-20",
  "description": "Daily sales",
  "is_estimated": false,
  "evidence_id": 88        // optional — link pre-uploaded evidence
}

Response 201:
{
  "success": true,
  "data": {
    "transaction_id": 201,
    "confidence": "high",      // updated immediately if evidence_id was provided
    "warnings": [
      {
        "type": "outlier",
        "message": "This is 3x higher than your usual daily sales. Please confirm."
      }
    ]
  }
}

Note: If warnings array is non-empty, the transaction IS still saved.
Frontend shows warning as a toast — user already confirmed by submitting.
```

```
GET /my/transactions
────────────────────────────────
Auth: client role
Returns this client's own transactions for current month.
Same response structure as CA view but limited to own client_id.
```

```
PUT /transactions/:id
────────────────────────────────
Auth: client (own transactions only) or ca_staff/ca_owner
Request: {"amount": 8500, "description": "Corrected amount"}
Creates audit log entry on every update.
```

---

### 5.4 Evidence Upload

```
POST /evidence/upload
────────────────────────────────
Auth: client or ca_staff
Content-Type: multipart/form-data
Body: file (image/jpeg, image/png, application/pdf, max 10MB)
     client_id (integer)

Steps (server-side):
1. Validate file type and size
2. Run quality check (Laplacian blur)
3. Upload to Cloudinary
4. Insert evidence record (ocr_status = 'pending')
5. Spawn background thread for OCR
6. Return immediately

Response 202 (Accepted, OCR running):
{
  "success": true,
  "data": {
    "evidence_id": 88,
    "file_url": "https://res.cloudinary.com/...",
    "thumbnail_url": "https://res.cloudinary.com/.../t_thumb/...",
    "quality_score": 72,
    "quality_status": "usable",
    "ocr_status": "pending",
    "message": "Photo saved. Scanning for details..."
  }
}
```

```
GET /evidence/:id
────────────────────────────────
Auth: client (own) or ca_staff/ca_owner (same org)
Client polls this after upload to get OCR result.

Response when OCR complete:
{
  "data": {
    "evidence_id": 88,
    "ocr_status": "success",
    "ocr_amount": 8200,
    "ocr_date": "2025-01-20",
    "ocr_gstin": "27AAPFU0939F1ZV",
    "strength": "strong",
    "strength_reason": "Clear bill image, amount and GSTIN extracted by OCR"
  }
}
```

---

### 5.5 Dashboard (CA)

```
GET /dashboard
────────────────────────────────
Auth: ca_owner or ca_staff

Response 200:
{
  "data": {
    "org_name": "Sharma & Associates",
    "stats": {
      "total_clients": 12,
      "active_clients": 8,
      "invited_not_joined": 4,
      "red_clients": 2,
      "yellow_clients": 3,
      "green_clients": 7,
      "unread_alerts": 5
    },
    "upcoming_deadlines": [
      {
        "client_name": "Ramesh Tea Shop",
        "deadline_type": "gstr3b",
        "due_date": "2025-01-20",
        "days_remaining": 5,
        "status": "pending"
      }
    ],
    "recent_alerts": [
      {
        "id": 15,
        "alert_type": "missing_data",
        "severity": "warning",
        "title": "Ramesh Tea Shop — No entries for 5 days",
        "created_at": "2025-01-19T09:00:00Z"
      }
    ]
  }
}
```

---

### 5.6 Filing Summary

```
GET /clients/:id/filing-summary?period=2025-01&type=gstr3b
────────────────────────────────
Auth: ca_owner or ca_staff
Generates (or retrieves cached) filing summary.

Response 200:
{
  "data": {
    "client": {"id": 42, "business_name": "Ramesh Tea Shop"},
    "period": "2025-01",
    "filing_type": "gstr3b",
    "totals": {
      "sales": 124500,
      "expenses": 38200,
      "estimated_tax": 5602.50
    },
    "confidence_breakdown": {
      "high": 8,
      "medium": 7,
      "low": 3,
      "total": 18,
      "with_evidence": 15
    },
    "low_confidence_transactions": [
      {"id": 195, "amount": 3200, "date": "2025-01-05", "reason": "Manual entry, no photo"}
    ],
    "summary_id": 7,
    "generated_at": "2025-01-20T14:22:00Z"
  }
}
```

```
GET /clients/:id/filing-summary/export?summary_id=7&format=excel
────────────────────────────────
Returns Excel file as attachment.
Content-Disposition: attachment; filename="RameshTeaShop_Jan2025_GSTR3B.xlsx"

Excel structure:
  Sheet 1: Summary (totals, tax liability, confidence breakdown)
  Sheet 2: All transactions (date, type, amount, confidence, evidence ref)
  Sheet 3: Low confidence items (needs CA review before filing)
```

---

### 5.7 Reminders

```
POST /reminders/send-bulk
────────────────────────────────
Auth: ca_owner or ca_staff
Request:
{
  "client_ids": [42, 43, 44],  // or "all" for all active clients
  "message": "GSTR-3B due January 20. Please enter your remaining transactions.",
  "type": "deadline"
}

Response 200:
{
  "data": {
    "sent": 3,
    "failed": 0,
    "details": [
      {"client_id": 42, "client_name": "Ramesh Tea Shop", "status": "delivered"}
    ]
  }
}
```

---

## 6. 30-60-90 Day Build Roadmap

### Conventions
- Sprint = 1 week (Mon-Fri, ~35 working hours for 2 devs = 70 hours/sprint)
- Dev A = Backend-focused
- Dev B = Frontend-focused
- "Ship" = deployed to production URL, not just local

---

### DAYS 1-7 (Sprint 1): Fix Foundation + Switch to PostgreSQL

**Goal: Remove all known bugs from bc_core/. Ship a deployable backend.**

| Day | Dev A (Backend) | Dev B (Frontend) |
|-----|----------------|-----------------|
| 1-2 | Switch SQLite → PostgreSQL (Supabase). Update Config. Run existing migrations. | Set up React (Vite) + TailwindCSS project. Configure API base URL. |
| 3 | Create new migrations for updated User + Organization schema (add phone, fcm_token, etc.) | Build CA login + register pages (forms only, no dashboard) |
| 4 | Fix permission system: add `org_members` table, add `@require_org_access` decorator, apply to all existing routes | Build OTP verification screen |
| 5 | Set up Railway deployment. Configure env variables. Verify HTTPS. | Deploy frontend to Vercel. Connect to Railway API URL. |
| 5 | Write smoke tests: auth register → login → get me → create org → list orgs | Test full auth flow end-to-end in deployed environment |

**What NOT to build this sprint:** Anything client-facing. Any compliance feature. Any dashboard.

**Milestone:** CA can register, verify OTP, log in — in the deployed production URL.

---

### DAYS 8-14 (Sprint 2): Client Model + Invite System

**Goal: CA can create a client and generate an invite link.**

| Day | Dev A | Dev B |
|-----|-------|-------|
| 8-9 | Create `clients` table + migration. Build `POST /clients` API. Implement `generate_invite_code()`. Generate compliance deadlines on client creation (hardcode Indian dates). | Build CA dashboard skeleton: navbar, client list page (empty state with "Add Client" button) |
| 10 | Build `GET /clients` API with compliance_color logic (red/yellow/green). Build `GET /clients/:id`. | Build "Add Client" form modal. Wire to `POST /clients` API. Show invite link + QR code on success. |
| 11 | Build `POST /invite/accept` + `POST /invite/verify-otp` (client phone OTP). | Build invite landing page (public, no auth): shows CA name + "Join BharatCompliance" |
| 12-13 | Build `POST /auth/client-login` (phone + PIN). Build client role JWT payload. | Build PWA shell: manifest.json, service worker, "Add to Home Screen" prompt. Connect client login to PWA. |
| 14 | End-to-end test: CA creates client → invite link → client opens link → registers → logs into PWA | Fix any broken flows from test |

**Milestone:** CA can invite a client. Client opens link on phone, registers, and lands in the PWA. This is the distribution mechanism working.

---

### DAYS 15-21 (Sprint 3): In-App Guided Chat (Client PWA)

**Goal: Client can enter a daily sales transaction from the PWA.**

| Day | Dev A | Dev B |
|-----|-------|-------|
| 15-16 | Build `POST /transactions` API with validation (amount > 0, not future date, duplicate check). Build `GET /my/transactions`. | Build chat UI component: renders "steps" from a flow config JSON. First flow: daily_sales (amount input → done). |
| 17 | Build anomaly detection service: outlier check (5x rolling avg), duplicate check. Return `warnings` array in transaction response. | Build expense entry flow (type selector → amount input → done). Integrate both flows into chat screen. |
| 18-19 | Build `GET /my/summary` — client's current month totals. | Build transaction history view in PWA (chat history style — each entry as a card). Build "My Summary" screen (monthly totals). |
| 20-21 | Test the full client flow: login → enter sale → enter expense → view history. Fix edge cases. | Make chat UI offline-capable: queue transactions in localStorage if offline, retry on reconnect. |

**DO NOT BUILD YET:** Evidence upload, OCR. The chat flow must work perfectly first.

**Milestone:** A real micro-business owner can open the PWA, enter "today's sales ₹8,200" in under 60 seconds, and see it saved.

---

### DAYS 22-28 (Sprint 4): CA Dashboard (Core)

**Goal: CA can see all clients with health status and drill into a client's transactions.**

| Day | Dev A | Dev B |
|-----|-------|-------|
| 22-23 | Build `GET /dashboard` API (stats: total clients, red/yellow/green counts, upcoming deadlines, recent alerts). Build `GET /clients/:id/transactions` with filters + totals. | Build CA dashboard overview screen: stat cards at top, client list table with red/yellow/green dots. |
| 24-25 | Build alerts generation service: daily batch job (APScheduler) that creates `missing_data` alerts for clients with >3 day gaps. Build `GET /alerts` endpoint. | Build client detail screen: transaction list, totals, next deadline. |
| 26-27 | Build deadline service: `GET /clients/:id/deadlines`, `GET /deadlines/upcoming` (all clients). Build `POST /deadlines/:id/complete`. | Build deadlines view in CA dashboard (list of upcoming deadlines sortable by date). Build "Mark as Filed" button on deadline. |
| 28 | End-to-end test: CA logs in → sees client list with colors → opens Ramesh Tea Shop → sees his 5 transactions → sees GSTR-3B deadline. | Fix any visual issues. Ensure dashboard loads in <2 seconds. |

**Milestone:** CA can see their client dashboard. The product now has something to show a real CA.

---

### DAYS 29-35 (Sprint 5): Evidence Upload + OCR

**Goal: Client can upload a bill photo. CA sees the OCR result linked to the transaction.**

| Day | Dev A | Dev B |
|-----|-------|-------|
| 29-30 | Set up Cloudinary account. Configure signed upload preset. Build `POST /evidence/upload`: file validation → quality check → Cloudinary upload → insert evidence → spawn OCR thread. | Add camera/upload button to PWA transaction chat flow. Show "Photo saved, scanning..." feedback. |
| 31 | Build async OCR service: Gemini Vision prompt, JSON parse, confidence scoring, strength classification, update evidence + linked transaction confidence. Build `GET /evidence/:id` (polling endpoint). | Add OCR result display to PWA: "Bill scanned! Amount: ₹8,200. Date: Jan 20." If mismatch, show "Which is correct?" prompt. |
| 32-33 | Wire evidence to transactions: when evidence OCR succeeds and transaction exists, update transaction.confidence. Build `GET /clients/:id/evidence`. | Show evidence thumbnails in CA client detail view. Show strength indicator (strong/medium/weak) on each. |
| 34-35 | Test OCR with 20 different real bill photos. Measure accuracy. Tune Gemini prompt. | Build evidence viewer modal in CA dashboard (fullscreen photo + OCR extracted data). |

**Milestone:** Client uploads a bill photo → CA sees it with OCR data → transaction shows "High confidence" instead of "Low confidence."

---

### DAYS 36-42 (Sprint 6): Filing Summary + Export

**Goal: CA can generate a filing prep summary for any client for any month and export to Excel.**

| Day | Dev A | Dev B |
|-----|-------|-------|
| 36-37 | Build `GET /clients/:id/filing-summary` API: aggregates transactions by period, computes totals, confidence breakdown, flags low-confidence items. | Build "Prepare Filing" button on client detail page. Show filing summary screen with totals and breakdown. |
| 38 | Build Excel export using `openpyxl` (add to requirements.txt): 3 sheets — Summary, All Transactions, Low Confidence Items. `GET /clients/:id/filing-summary/export`. | Wire "Download Excel" button to export API. Test file download in browser. |
| 39 | Build `POST /reminders/send-bulk`: FCM push to selected clients. Set up Firebase project + service account JSON. | Build "Send Reminder" UI: checkbox select clients → type message → send. Show delivery status. |
| 40-42 | Full system test: CA creates client → client enters 20 transactions over a "month" → CA generates filing summary → exports Excel. Fix anything broken. | Polish all screens. Fix responsive issues. Add loading states everywhere. |

**Milestone: This is the MVP.** A CA can now complete a full filing cycle using BharatCompliance.

---

### DAYS 43-56 (Sprint 7-8): First CA Onboarding + Real-World Testing

**Goal: 3-5 real CA firms using the product with their real clients.**

| Activity | Owner | Timeline |
|----------|-------|---------|
| Identify 5 CA firms from network/ICAI chapter | Non-dev team member | Week 7 start |
| Onboard CA Firm 1: register, create 5 clients, walk through invite flow | Dev team + CA | Day 43-44 |
| Daily check-in with CA Firm 1 for first week | Any team member | Day 44-50 |
| Fix bugs from CA Firm 1 feedback | Dev A | Day 45-50 |
| Onboard CA Firms 2-3 | Day 50-56 | |
| Track: D7 client retention, transactions/day, any data errors | Dev team | Ongoing |

**NOT building in this sprint:** New features. Only bug fixes and UX polish based on real CA feedback.

**Milestone:** First real transaction entered by a real micro-business client. First filing summary exported by a real CA.

---

### DAYS 57-90 (Sprints 9-12): Stabilize + Scale to 10 CAs

**Week 9 (Days 57-63):** Fix everything broken from real usage. Prioritize by how many users it affects.
**Week 10 (Days 64-70):** Add data validation improvements based on real transaction patterns seen in the wild.
**Week 11 (Days 71-77):** Add CA-level reporting: "Month summary for all clients" view.
**Week 12 (Days 78-84):** Onboard CA firms 4-10. Performance testing.
**Days 85-90:** Security review. Fix any critical findings. Prepare first version of pricing page.

**Features explicitly NOT in 90-day plan (build after Day 90):**
- GST filing integration
- Multi-language (Hindi)
- Tally import/export
- Loan/credit features
- Multi-org support (CA staff working for multiple firms)
- SMS fallback for push notifications
- Advanced analytics

---

## 7. MVP Security & Trust Essentials

These are non-negotiable. None of these are over-engineering — they are the minimum a CA firm handling client financial data requires.

### 7.1 Authentication Security

```python
# JWT Configuration (in bc_core/core/config.py)
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
# Add this to check blocklist on every protected request:
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return db.session.query(
        JWTBlocklist.query.filter_by(jti=jti).exists()
    ).scalar()
```

Password requirements: min 8 chars, 1 number. Enforced server-side, not just client-side.
PIN (clients): 4-digit. Rate limit to 5 failed attempts, then 30-minute lockout.
OTP: 6 digits. 10-minute expiry. Max 3 sends per hour per phone/email.

### 7.2 Data Isolation (Most Critical)

Every single route that touches client/transaction/evidence data MUST go through this check:

```python
# bc_core/core/dependencies.py

def require_org_access(f):
    """Decorator: ensures JWT user belongs to the org being accessed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_jwt_identity()
        # Get org_id from route param or from client's org_id
        org_id = kwargs.get('org_id') or get_org_id_from_context(kwargs)

        membership = OrgMember.query.filter_by(
            user_id=user_id,
            org_id=org_id
        ).first()

        if not membership:
            return jsonify({"success": False, "error": "Access denied"}), 403

        g.current_user_role = membership.role
        g.org_id = org_id
        return f(*args, **kwargs)
    return decorated

def require_client_ownership(f):
    """Decorator for client-role users: ensures they only access their own data."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role == 'client':
            client = Client.query.filter_by(owner_user_id=user_id).first()
            requested_client_id = kwargs.get('client_id')
            if requested_client_id and client.id != int(requested_client_id):
                return jsonify({"success": False, "error": "Access denied"}), 403
        return f(*args, **kwargs)
    return decorated
```

No route that returns client data should ever be accessible without one of these decorators.

### 7.3 Input Validation

Use Marshmallow (already in codebase) for all request body validation. Never trust client-sent data.

```python
class CreateTransactionSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf(
        ["sale", "expense", "purchase", "salary_paid", "other"]
    ))
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=0.01, max=9999999))
    transaction_date = fields.Date(required=True, validate=lambda d: d <= date.today())
    description = fields.Str(load_default=None, validate=validate.Length(max=500))
    is_estimated = fields.Bool(load_default=False)
    evidence_id = fields.Int(load_default=None)
```

### 7.4 File Upload Security

```python
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_upload(file):
    # Check extension
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Only JPG, PNG, PDF allowed")

    # Check MIME type from file content, not just extension
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)
    if mime not in ['image/jpeg', 'image/png', 'application/pdf']:
        raise ValidationError("Invalid file type")

    # Check size
    file.seek(0, 2)  # seek to end
    if file.tell() > MAX_FILE_SIZE:
        raise ValidationError("File too large (max 10MB)")
    file.seek(0)
```

Add `python-magic` to requirements.txt for MIME detection.

### 7.5 API Rate Limiting

```python
# Add flask-limiter to requirements.txt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address, default_limits=["200 per hour"])

# Stricter limits on auth routes
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login(): ...

@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("5 per minute")
def verify_otp(): ...
```

### 7.6 HTTPS + Headers

On Railway, HTTPS is automatic. Add these response headers to every response:

```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 7.7 Audit Logging

Every state-changing action gets an audit log entry:

```python
def log_action(user_id, org_id, action, entity_type=None, entity_id=None, metadata=None):
    log = AuditLog(
        user_id=user_id,
        org_id=org_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=request.remote_addr,
        metadata=metadata or {}
    )
    db.session.add(log)
    # Do NOT db.session.commit() here — let the calling function commit together
```

Log these actions: `login`, `logout`, `create_client`, `edit_client`, `create_transaction`, `edit_transaction`, `delete_transaction`, `verify_transaction`, `generate_filing_summary`, `export_filing`, `mark_deadline_complete`, `send_reminder`.

### 7.8 What NOT to Implement for MVP Security

- Two-factor auth for CAs (add after Day 90)
- IP allowlisting (enterprise feature)
- Data encryption at rest (Supabase handles this)
- SOC 2 compliance (not needed until ₹1 crore ARR)
- Penetration testing (do this before raising money, not before MVP)

---

## 8. Early Scaling Plan

### Phase 1: 1 CA → 10 CAs (Days 43-90)

**Infrastructure:** Single Railway instance ($5/month), Supabase free tier, Cloudinary free tier.
**Capacity:** This handles 10 CA firms with 50 clients each easily. No optimization needed.
**What to monitor:** Response time of `GET /dashboard` — if it exceeds 1.5 seconds, add a database index.

**What breaks first at 10 CAs:**

1. **OCR threads pile up:** 50 clients × 5 photos/day = 250 concurrent threads possible on a busy day. Python threading will struggle.
   Fix: Add a simple in-memory queue (Python `queue.Queue`) with max 10 worker threads. Requests beyond 10 are queued, not dropped.

2. **Dashboard query is slow:** `GET /dashboard` queries multiple tables. Add these indexes and a materialized view:
   ```sql
   -- Add if not already there:
   CREATE INDEX idx_transactions_client_date ON transactions(client_id, transaction_date DESC);

   -- Cache client stats: run as a nightly job, store in clients table
   UPDATE clients SET
       compliance_score = calculate_score(id),
       last_transaction_at = (SELECT MAX(transaction_date) FROM transactions WHERE client_id = clients.id),
       monthly_turnover_cache = (SELECT SUM(amount) FROM transactions
                                  WHERE client_id = clients.id
                                  AND type = 'sale'
                                  AND transaction_date >= DATE_TRUNC('month', NOW()))
   WHERE status = 'active';
   ```

3. **Cloudinary free tier bandwidth:** 25GB/month. At 10 CA firms × 50 clients × 5 photos/day × 100KB avg = ~7.5GB/month. You're fine.

---

### Phase 2: 10 CAs → 50 CAs (Days 90-180)

**Infrastructure changes needed:**
- Upgrade Supabase to $25/month tier (8GB storage, no row limits)
- Add Redis + Celery to replace Python threads for OCR (Railway Redis: $5/month)
- Consider adding a read replica if dashboard queries slow down

**Add Celery for async OCR:**
```python
# Replace threading approach with:
from celery import Celery

celery = Celery('bharatcompliance', broker='redis://redis:6379/0')

@celery.task
def process_ocr(evidence_id, file_url):
    with app.app_context():
        run_ocr_and_update(evidence_id, file_url)

# In upload route, replace thread.start() with:
process_ocr.delay(evidence.id, file_url)
```

**Add connection pooling:**
```python
# In config.py — add SQLAlchemy pool settings
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_TIMEOUT = 30
```

**New features to add at 50 CAs:**
- Hindi language support (just translate UI strings)
- Excel import for existing CA client data (one-time migration feature)
- Email weekly digest to CAs (Resend, free tier handles this)

---

### Phase 3: 50 CAs → 100+ CAs (Day 180+)

**Infrastructure:**
- Move to dedicated PostgreSQL (Railway or Neon.tech)
- Add CDN for React frontend (already on Vercel — fine)
- Consider horizontal scaling of Flask: 2-3 Railway instances behind a load balancer
- Cloudinary paid plan ($89/month) — 225GB storage

**What breaks at 100 CAs:**
- APScheduler running inside Flask process becomes unreliable (multiple instances, duplicate jobs). Move scheduled jobs to a separate worker process or use a job queue (Celery Beat).
- Filing summary generation for large clients (500+ transactions) may time out. Add async generation with a "ready" webhook.

**Pricing update at 100 CAs:** Move from flat ₹999/month to tiered pricing:
- Starter: ₹999/month — up to 20 clients
- Growth: ₹2,499/month — up to 75 clients
- Practice: ₹4,999/month — unlimited clients

---

## 9. Risk Register

### Technical Risks

---

**RISK T1: OCR accuracy on Indian informal bills is low**
Likelihood: High
Impact: High — wrong amounts → CA loses trust
Details: Indian bills are often handwritten, in regional scripts, with non-standard formats. Real-world OCR accuracy on unstructured informal bills is 50-70%, not 95%.

Mitigation:
- Never auto-apply OCR amount to the transaction without client confirmation. Always show "OCR found ₹8,200. Is this correct?"
- Train the Gemini prompt on 50+ real bill types before launch (test manually in Sprint 5)
- Build "OCR mismatch" alert that flags when entered amount and OCR amount differ by >10%
- Position OCR as a "helpful suggestion" not an automatic data entry tool

---

**RISK T2: PWA push notifications fail on some Android devices**
Likelihood: Medium
Impact: Medium — reminders don't reach clients
Details: FCM push to PWA requires the browser to support service workers and the user to grant notification permission. Some cheap Android phones (Jio phones, old Redmi) have aggressive battery optimization that kills background processes.

Mitigation:
- Always have SMS as fallback for critical deadline reminders (use Twilio or Fast2SMS — ₹0.15 per SMS)
- In the PWA onboarding flow, explicitly ask user to disable battery optimization for Chrome
- In CA dashboard, show "notification delivery status" so CA knows if clients are receiving reminders

---

**RISK T3: Cloudinary free tier limits exceeded**
Likelihood: Low (in 90 days)
Impact: Low — uploads fail
Details: 25GB free. At scale this could be exceeded.

Mitigation: Monitor Cloudinary usage weekly. At 80% free tier, add image compression before upload (resize to max 1200px width, JPEG quality 80%) — reduces average file size from 3MB to ~300KB.

---

**RISK T4: Railway deployment downtime**
Likelihood: Low
Impact: Medium
Mitigation: Enable Railway health checks. Add uptime monitoring (UptimeRobot free tier — 50 monitors). Keep the last working Docker image as rollback option.

---

### Adoption Risks

---

**RISK A1: Clients don't adopt the PWA**
Likelihood: High
Impact: Critical — without client data, CA has no value
Details: Getting a non-tech micro-business owner to add a PWA to their home screen requires multiple steps that feel foreign.

Mitigation:
- Make the invite link open directly to a mobile-optimized page that auto-prompts PWA install
- Build the first "Add to Home Screen" step as part of the invite flow — don't let user skip it
- CA must do first transaction WITH the client the first time (hand-hold the first entry)
- Add an in-app video (15-second screen recording) showing how to enter a sale
- **Critical:** First transaction should be completable in under 60 seconds or clients won't return

---

**RISK A2: CAs don't push clients to use the app**
Likelihood: Medium
Impact: High — if CA doesn't mandate it, clients ignore it
Details: If CA sees it as "optional" they won't push clients. Clients won't push themselves.

Mitigation:
- Show CA exactly what they're missing: "You have 8 clients who haven't entered any data this month. Here's a reminder you can send in one click."
- During CA onboarding, walk them through sending an invite to 3 clients on the first day — don't leave it to them to figure out later
- Create a "low client adoption" alert in CA dashboard: "Only 40% of your clients are using the app. Send a reminder?"

---

**RISK A3: CA churns because OCR gives wrong data once**
Likelihood: Medium
Impact: High
Details: Trust is fragile. One wrong amount on a filing summary, and the CA tells every CA they know to avoid BharatCompliance.

Mitigation:
- File the CA's first filing summary manually alongside them — don't let them do it alone. Find the errors together before it's a problem.
- Add a "CA Review" step before any filing summary is marked exportable — CA must explicitly confirm low-confidence transactions
- Never claim the product is "automated filing" — it's "filing prep support with human CA review"

---

### Cost Risks

---

**RISK C1: Gemini Vision API costs spike with high usage**
Likelihood: Low (until 100+ CAs)
Impact: Low
Details: $0.075 per 1M tokens. 1 OCR call ≈ 1,000 tokens. 5,000 photos/month = $0.375. Even at 100,000 photos/month = $7.50. Not a real risk until massive scale.

Mitigation: None needed for 90-day plan. Add cost monitoring alert at $50/month.

---

**RISK C2: Team runs out of money before first paying customer**
Likelihood: Medium
Impact: Critical
Details: Bootstrap startup. Infrastructure is $10-15/month. Personal costs are the real constraint.

Mitigation:
- Charge for the product from Day 1 of public access (after pilot period). Don't let free access go beyond 6 weeks for any CA firm.
- Pilot CAs (first 5) pay ₹0 for 3 months, then ₹999/month. Get verbal commitment upfront.
- Keep team to 2-3 people. Don't hire until ₹5 lakh MRR.

---

### Legal Risks

---

**RISK L1: CA holds your platform liable for a wrong compliance score**
Likelihood: Medium
Impact: High
Details: If BharatCompliance says "compliance score 85" and the client gets a GST notice, the CA may blame the tool.

Mitigation:
- Terms of Service (before CA account creation) must state: "BharatCompliance is a data organization tool. All compliance decisions remain the responsibility of the CA professional. We do not provide legal or tax advice."
- Never use the word "compliant" to describe a client. Use "data complete" or "filing ready."
- Compliance score is labeled "Data Completeness Score" — not a legal compliance verdict
- Get a one-page Terms of Service reviewed by a CA + one lawyer before first paying customer

---

**RISK L2: Client financial data stored without explicit consent**
Likelihood: Medium
Impact: Medium
Details: India's Digital Personal Data Protection Act (DPDPA) 2023 requires consent for processing personal data.

Mitigation:
- During client PWA onboarding, show explicit consent screen: "By joining, you allow [CA Firm Name] to access and manage your business compliance data using BharatCompliance."
- Store `consent_given_at` timestamp and `consent_version` in the users table
- Privacy policy (one page, plain language) linked from all onboarding screens
- Don't store Aadhaar, bank account numbers, or any government ID beyond GSTIN/PAN which businesses already share with their CA

---

**RISK L3: WhatsApp/Meta dependency removed but Google (Gemini) dependency remains**
Likelihood: Low
Impact: Medium
Details: If Google changes Gemini pricing or API terms, OCR costs could spike.

Mitigation:
- OCR is a confidence-booster, not a required feature. The product works without OCR (lower confidence transactions are flagged for CA review).
- If Gemini becomes expensive, the fallback is: skip OCR entirely for photos below a certain quality score, and mark all photo-evidenced transactions as "medium confidence" without extraction.

---

**Assumption Log (things assumed, not confirmed from docs):**

1. Team has access to a Cloudinary account — assumed, takes 5 minutes to create
2. Team can get Firebase project credentials — free, 10 minutes
3. Railway deployment is acceptable — $5/month, free trial available
4. First 5 pilot CAs will come from existing personal/hackathon network — assumed feasible given team is from ByteQuest community
5. `openpyxl` is acceptable for Excel generation (no LibreOffice dependency) — assumed
6. APScheduler running inside Flask process is acceptable until 50 CAs — assumed, documented in scaling plan
7. Existing `bc_core/` modules for `compliance/` and `alerts/` will be deleted and rebuilt fresh — assumed based on audit docs saying they are empty and misaligned
8. Client will use Android PWA, not iOS — 92% of India's mobile market is Android; iOS PWA has limited push notification support

---

*Document version: 1.0 | Last updated: Day 0 | Next review: End of Sprint 2 (Day 14)*
