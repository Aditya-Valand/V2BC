# BharatCompliance: Quick Fix Checklist

## Print This Out and Check Off As You Go

---

## PHASE-0: FOUNDATION

### Auth & Users
- [x] User signup/login
- [x] JWT tokens
- [x] Password hashing
- [ ] Email verification (nice to have)
- [ ] User roles (CA, staff, client)
- [ ] **MISSING: Permission model** ⚠️
- [ ] **MISSING: Business owner link** ⚠️

### Organizations
- [x] Create organization
- [x] List organizations
- [ ] **MISSING: Permission checks** ⚠️
- [ ] **MISSING: Invite team members** (Phase-1.5)

### Businesses
- [x] Create business
- [x] List businesses
- [ ] **ADD: whatsapp_phone field** 🔴
- [ ] **ADD: owner_user_id field** 🔴
- [ ] **MISSING: Permission checks** ⚠️

### Database
- [x] User table
- [x] Organization table
- [x] Business table
- [ ] **CREATE: Migration for whatsapp_phone** 🔴
- [ ] **CREATE: Migration for UserOrganizationPermission** 🔴

---

## PHASE-1: WHATSAPP & STATEMENTS

### WhatsApp Ingestion
- [ ] **CREATE: webhook_verify() GET endpoint** 🔴
- [ ] **CREATE: webhook_receiver() POST endpoint** 🔴
- [ ] **CREATE: Signature verification** 🔴
- [ ] **CREATE: Phone-to-business lookup** 🔴
- [ ] **CREATE: Message routing logic** 🔴
- [ ] **ADD: Error handling** 🟠
- [ ] **ADD: Logging** 🟠

### WhatsApp Models & Storage
- [x] WhatsAppMessage model
- [ ] **MISSING: Migration for WhatsAppMessage** ⚠️
- [ ] **ADD: Is this phone unknown tracking** 🟡

### Statement Parsing
- [x] Parser exists (basic)
- [ ] **FIX: Handle decimals (₹12500.50)** 🟠
- [ ] **FIX: Handle currency symbols** 🟠
- [ ] **FIX: Extract dates properly** 🟠
- [ ] **FIX: Don't break on embedded numbers** 🟠
- [ ] **ADD: Support weak data ("approx 12000")** 🟠
- [ ] **MISSING: Migration for BusinessStatement** ⚠️

### Statement Models & Storage
- [x] BusinessStatement model
- [x] create_statement() service
- [ ] Statement GET endpoint
- [ ] **MISSING: Statement filtering** 🟡

### Evidence Upload & Storage
- [x] BusinessEvidence model
- [x] save_evidence() service
- [x] Quality checking (Laplacian blur)
- [x] Evidence upload endpoint
- [ ] **ADD: evidence_strength field** 🟠
- [ ] **ADD: confidence_reason field** 🟠
- [ ] **FIX: Classify evidence type properly** 🟠
- [ ] **MISSING: Migration for BusinessEvidence** ⚠️
- [ ] **ADD: Media download from WhatsApp** 🟠

### Confidence & Status Tracking
- [x] confidence_level field exists
- [x] status field exists
- [ ] **FIX: Update confidence on OCR** 🟠
- [ ] **ADD: Track confidence reason** 🟠
- [ ] **ADD: Manual confidence override** 🟡

### CA Visibility APIs
- [ ] **CREATE: GET /businesses/<id>/statements** 🔴
- [ ] **CREATE: GET /businesses/<id>/evidence** 🔴
- [ ] **CREATE: GET /orgs/<id>/dashboard** 🔴
- [ ] **CREATE: GET /orgs/<id>/weak-evidence** 🟠
- [ ] **ADD: Monthly aggregation** 🟠
- [ ] **ADD: Filtering & sorting** 🟡
- [ ] **ADD: Pagination** 🟡

### Permissions
- [ ] **CREATE: UserOrganizationPermission model** 🔴
- [ ] **CREATE: Permission check decorators** 🔴
- [ ] **ADD: Permission checks to all routes** 🔴
- [ ] **ADD: Business access validation** 🔴

### Route Registration
- [x] Auth routes registered
- [x] Org routes registered
- [x] Business routes registered
- [ ] **ADD: Evidence routes to app.py** 🔴
- [ ] **ADD: Statements routes to app.py** 🔴
- [ ] **ADD: WhatsApp routes to app.py** 🔴

### Error Handling
- [ ] **ADD: Webhook error handling** 🟡
- [ ] **ADD: Database error handling** 🟡
- [ ] **ADD: File upload error handling** 🟡
- [ ] **ADD: OCR error handling** 🟡

---

## PHASE-2: OCR & INTELLIGENCE

### OCR Integration
- [x] Google Vision API connected
- [x] Text extraction works
- [x] Field extraction (amount, date, GSTIN)
- [ ] **IMPROVE: Extract vendor name** 🟡
- [ ] **IMPROVE: Extract item category** 🟡
- [ ] **IMPROVE: Extract payment method** 🟡
- [ ] **IMPROVE: Extract HSN/SAC codes** 🟡

### OCR Processing
- [x] run_ocr() service exists
- [ ] **FIX: Update BusinessStatement confidence** 🟠
- [ ] **ADD: Async processing** 🟠
- [ ] **ADD: Error recovery** 🟡
- [ ] **ADD: Fallback strategies** 🟡

### Evidence Quality
- [x] Laplacian blur detection
- [ ] **IMPROVE: Color/saturation check** 🟡
- [ ] **IMPROVE: Text region detection** 🟡
- [ ] **IMPROVE: Document boundary detection** 🟡

---

## CLEANUP: DELETE THESE

- [ ] **DELETE: modules/documents/** 🔴
  - models.py (empty anyway)
  - routes.py (empty anyway)
  - schemas.py (if exists)
  - Reason: Everything is Evidence, not Documents

- [ ] **DELETE or STUB: modules/compliance/** 🟡
  - Only put placeholder when needed
  - Reason: Phase-2 only, not Phase-1

- [ ] **DELETE or STUB: modules/alerts/** 🟡
  - Only put placeholder when needed
  - Reason: Phase-2+ only, not Phase-1

---

## ENVIRONMENT VARIABLES TO ADD

Add these to your .env file:

```env
# WhatsApp
WHATSAPP_VERIFY_TOKEN=your-token-here
WHATSAPP_BUSINESS_ACCOUNT_TOKEN=your-token-here
WHATSAPP_WEBHOOK_SECRET=your-secret-here
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
```

---

## TESTING CHECKLIST

### Unit Tests to Write
- [ ] test_parse_statement() - various inputs
- [ ] test_extract_amount() - with decimals
- [ ] test_image_quality_score() - various images
- [ ] test_permission_check() - various cases

### Integration Tests
- [ ] test_webhook_receiver() - valid message
- [ ] test_webhook_receiver() - invalid signature
- [ ] test_webhook_receiver() - unknown phone
- [ ] test_create_statement_from_webhook()
- [ ] test_ca_permission_on_business()

### Manual Testing
- [ ] Webhook signature verification works
- [ ] Message saved to database
- [ ] Statement parsed correctly
- [ ] Confidence updated after OCR
- [ ] CA can only see own org's businesses
- [ ] Dashboard shows correct totals

---

## GIT COMMITS TO MAKE

When you're ready to commit, use these commit messages:

```bash
# Phase-0 fixes
git commit -m "feat: add WhatsApp phone and owner_user_id to Business"
git commit -m "feat: implement UserOrganizationPermission model"
git commit -m "feat: add permission decorators and validation"

# Phase-1 foundation
git commit -m "feat: implement WhatsApp webhook receiver"
git commit -m "feat: implement phone-to-business message routing"
git commit -m "feat: register missing blueprints in app.py"

# Phase-1 completion
git commit -m "feat: implement CA visibility APIs (statements, evidence, dashboard)"
git commit -m "fix: update confidence when OCR extracts fields"
git commit -m "feat: add evidence strength classification"
git commit -m "fix: improve statement parser for edge cases"

# Cleanup
git commit -m "chore: remove unused documents module"
git commit -m "chore: prepare compliance and alerts modules for Phase-2"
```

---

## Time Estimate for Each Task

| Task | Time | Priority |
|------|------|----------|
| WhatsApp webhook | 3-4h | 🔴 |
| Phone-to-business | 1h | 🔴 |
| Permission system | 4-5h | 🔴 |
| Route registration | 15m | 🔴 |
| Statement parser fixes | 2-3h | 🟠 |
| CA dashboards | 4-5h | 🟠 |
| Confidence updating | 1-2h | 🟠 |
| Evidence strength | 2h | 🟠 |
| Testing | 3-4h | 🟡 |
| Cleanup | 30m | 🟡 |
| OCR improvements | 3-4h | 🟡 |
| Async processing | 3-4h | 🟡 |
| Error handling | 2-3h | 🟡 |

**Total: ~38-50 hours**  
**Focused work: 2-3 weeks**

---

## Success Criteria

### Phase-1 is Complete When:
- [ ] CA receives WhatsApp message
- [ ] System maps phone → business
- [ ] Statement is parsed and stored
- [ ] Evidence quality is checked
- [ ] OCR extracts fields
- [ ] Confidence is updated
- [ ] CA can view statements
- [ ] CA can view evidence
- [ ] CA can see dashboard
- [ ] CA can only see own org's data
- [ ] All tests pass
- [ ] Error handling works

### You Can Launch When:
- [ ] All of Phase-1 complete
- [ ] No major security issues
- [ ] Error messages are user-friendly
- [ ] Performance is acceptable
- [ ] Documentation is complete
- [ ] You've tested with real WhatsApp messages

---

## Questions to Ask Yourself Before Starting

1. **Do you have WhatsApp Business Account API credentials?**
   - If not, get them first (takes ~1 week)
   - You need: verify_token, webhook_secret, business_account_token

2. **Do you have Google Cloud credentials for Vision API?**
   - Already seems to be set up (see modules/ocr/client.py)
   - Make sure credentials file is secure

3. **Do you want OCR to be synchronous or async?**
   - MVP: Synchronous (current approach)
   - Later: Add Celery for async

4. **What confidence levels do you want?**
   - Current: low, medium, high
   - Consider: very_low, low, medium, high, very_high

5. **Do you want role-based permissions?**
   - CA_OWNER: Can see all, invite staff, etc.
   - CA_STAFF: Can see assigned businesses
   - CLIENT: Can only send messages
   - Implement this after Phase-1 if MVP is tight

---

**Status: Ready to Implement ✅**

Print this checklist, stick it to your monitor, and work through it methodically.

You've got this!
