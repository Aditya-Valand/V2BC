# BharatCompliance: CRITICAL ISSUES - ACTION ITEMS

## 🔴 BLOCKING ISSUES (Must Fix Before Phase-1 Works)

### Issue #1: WhatsApp Webhook is COMPLETELY EMPTY
**Severity:** CRITICAL  
**Impact:** No way to receive WhatsApp messages  
**Current:** `modules/whatsapp/routes.py` and `modules/whatsapp/webhook.py` are both empty

**Required Implementation:**
- POST `/whatsapp/webhook` endpoint to receive messages from WhatsApp Business API
- GET `/whatsapp/webhook` endpoint for WhatsApp verification
- Webhook signature validation
- Phone number → Business lookup
- Trigger statement creation for text messages
- Trigger evidence creation for media

**Effort:** 3-4 hours  
**Blocking:** Everything else in Phase-1

---

### Issue #2: No Phone-to-Business Mapping
**Severity:** CRITICAL  
**Impact:** Cannot link WhatsApp messages to a business  
**Current:** Business model has no `whatsapp_phone` field

**Required Changes:**
```python
# Add to Business model:
whatsapp_phone = db.Column(db.String(20), unique=True, nullable=True)
owner_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
```

**Effort:** 1 hour  
**Blocking:** Webhook implementation

---

### Issue #3: Missing Routes Registration
**Severity:** CRITICAL  
**Impact:** Statements and evidence endpoints don't exist  
**Current:** `app.py` only registers auth, org, business blueprints

**Required Fix:**
```python
# In app.py, add:
from modules.evidence.routes import evidence_bp
from modules.statements.routes import statements_bp
from modules.whatsapp.routes import whatsapp_bp

app.register_blueprint(evidence_bp, url_prefix="/evidence")
app.register_blueprint(statements_bp, url_prefix="/statements")
app.register_blueprint(whatsapp_bp, url_prefix="/whatsapp")
```

**Effort:** 15 minutes  
**Blocking:** API testing

---

### Issue #4: Zero Permission Checking
**Severity:** CRITICAL  
**Impact:** Security disaster - any user can see any data  
**Current:** No permission validation on any route

**Required Implementation:**
- UserOrganizationPermission model
- Helper function: `has_org_access(user_id, org_id)`
- Helper function: `can_access_business(user_id, business_id)`
- Add checks to every protected route

**Effort:** 4-5 hours  
**Blocking:** Production deployment

---

## 🟠 HIGH PRIORITY (Phase-1 Cannot Be Complete Without These)

### Issue #5: Statement Parser is Too Simplistic
**Severity:** HIGH  
**Impact:** Wrong amount extraction  
**Current:** Takes last number found, no decimal support, no date extraction

**Example Breaking Case:**
```
Input: "Today sale 8200 but 100 customers came"
Current Output: 100 (WRONG)
Expected: 8200
```

**Required Improvements:**
- Handle: ₹12500, 12,500, 12500.50
- Extract amount with context
- Handle "approx" or "around" prefixes
- Extract dates
- Don't break on embedded numbers

**Effort:** 2-3 hours

---

### Issue #6: No CA Visibility APIs
**Severity:** HIGH  
**Impact:** CA firm cannot monitor compliance  
**Current:** No endpoints to view statements, evidence, or dashboards

**Required APIs:**
1. `GET /businesses/<id>/statements` - view all statements
2. `GET /businesses/<id>/evidence` - view all evidence with filtering
3. `GET /orgs/<id>/dashboard` - monthly summary for entire CA firm
4. `GET /orgs/<id>/weak-evidence` - flag potential issues

**Effort:** 4-5 hours

---

### Issue #7: Confidence Tracking Doesn't Update
**Severity:** HIGH  
**Impact:** All statements stay "low" confidence even after OCR  
**Current:** Confidence set to "low" on creation, never updated

**Required Fix:**
- When OCR runs and extracts amount + GSTIN → confidence = "high"
- When OCR extracts amount only → confidence = "medium"
- When OCR fails → confidence = "low"
- Update BusinessStatement when evidence changes

**Effort:** 1-2 hours

---

### Issue #8: Missing Evidence Strength Classification
**Severity:** HIGH  
**Impact:** Cannot distinguish weak vs strong evidence  
**Current:** `status` field (uploaded/weak/usable) vs `evidence_strength` (not implemented)

**Required:** Add `evidence_strength` field with clear criteria:
- **strong:** Clear invoice/bill with OCR'd GSTIN, amount, and date
- **medium:** Handwritten note with amount OCR'd but no GSTIN
- **weak:** Blurry image, manually entered data, no supporting OCR

**Effort:** 2 hours

---

## 🟡 MEDIUM PRIORITY (Phase-1 Polish)

### Issue #9: OCR Field Extraction Incomplete
**Severity:** MEDIUM  
**Impact:** Missing useful fields for compliance  
**Current:** Only extracts amount, date, GSTIN

**Missing Fields:**
- Vendor/business name
- Item category
- Payment method (cash/bank/UPI)
- HSN/SAC codes

**Effort:** 3-4 hours

---

### Issue #10: Wrong Modules Exist
**Severity:** MEDIUM  
**Impact:** Code confusion and bloat  

**Delete:**
- `modules/documents/` - doesn't fit product spec
- `modules/compliance/` - Phase-2 only, don't implement in Phase-1
- `modules/alerts/` - Phase-2+ only

**Effort:** 30 minutes

---

### Issue #11: No User Role Hierarchy
**Severity:** MEDIUM  
**Impact:** Hard to implement permission model later  
**Current:** `role = "CA"` or `"staff"` or `"client"` (simple string)

**Required Refinement:**
- CA_OWNER
- CA_STAFF
- CLIENT (micro-business owner)
- Link via UserOrganizationPermission

**Effort:** 2 hours

---

### Issue #12: No Background Jobs for OCR
**Severity:** MEDIUM  
**Impact:** Webhook will hang while OCR runs  
**Current:** `run_ocr()` is synchronous

**Fix:** Make OCR async (use Celery or similar)

**Effort:** 3-4 hours

---

## Recommended Execution Order

### Week 1: Unblock Phase-1
1. Add whatsapp_phone to Business model + migration
2. Implement WhatsApp webhook receiver
3. Register missing blueprints
4. Implement permission model + checks
5. Fix statement parser

### Week 2: Complete Phase-1
6. Build CA visibility APIs
7. Implement confidence updating
8. Add evidence_strength logic
9. Delete wrong modules

### Week 3: Polish & Testing
10. Improve OCR extraction
11. Add background job system
12. Add comprehensive error handling
13. Write tests

---

## Code Changes Required Summary

**Files to Create/Modify:**
- `bc_core/modules/whatsapp/routes.py` ← EMPTY, needs webhook handler
- `bc_core/modules/whatsapp/webhook.py` ← EMPTY, needs webhook logic
- `bc_core/modules/whatsapp/service.py` ← Add phone-to-business logic
- `bc_core/modules/businesses/models.py` ← Add whatsapp_phone, owner_user_id
- `bc_core/modules/auth/models.py` ← Add UserOrganizationPermission
- `bc_core/modules/evidence/service.py` ← Update confidence on OCR
- `bc_core/modules/statements/parser.py` ← Improve parsing logic
- `bc_core/modules/statements/service.py` ← Add schema for create endpoint
- `bc_core/app.py` ← Register missing blueprints, add permission checks
- `bc_core/core/dependencies.py` ← Add permission checking utilities
- `bc_core/migrations/` ← Add new migration files

**Files to Delete:**
- `bc_core/modules/documents/` (entire folder)
- `bc_core/modules/compliance/` (entire folder) - or keep as stub for Phase-2
- `bc_core/modules/alerts/` (entire folder) - or keep as stub for Phase-2

---

## Risk Assessment

| Risk | Current State | Impact | Mitigation |
|------|---------------|--------|------------|
| No webhook | Not built | Phase-1 blocked | Build immediately |
| No permissions | Not implemented | Data leak | Add before launch |
| Simple parser | Extracts wrong amounts | Bad data | Improve parsing |
| No CA APIs | Don't exist | CA can't use product | Build before launch |
| OCR async | Not async | API hangs | Add job queue |

---

**Next Steps:**
1. Read the full `ARCHITECTURE_AUDIT.md`
2. Start with Issue #1-4 (blocking issues)
3. Get back in touch after webhook is implemented
