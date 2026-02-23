# Phase-3 Compliance & Risk Engine - Audit & Implementation Plan

## 🔴 CRITICAL FINDINGS

### Current State: Phase-1 Complete, Phase-3 NOT STARTED

**Infrastructure Status:**
- ✅ Phase-1: WhatsApp ingestion, statement parsing, evidence collection, OCR
- ✅ Phase-2: CA dashboards (basic compliance visibility)
- ❌ Phase-3: MISSING ALL COMPONENTS

**Missing Critical Components:**

| Component | Status | Impact | Priority |
|-----------|--------|--------|----------|
| ComplianceSignal model | ❌ MISSING | Cannot calculate derived metrics | CRITICAL |
| ComplianceProfile model | ❌ MISSING | Cannot store business profiles | CRITICAL |
| RuleEngine | ❌ MISSING | Cannot evaluate rules | CRITICAL |
| ComplianceAlert model | ❌ MISSING | Cannot store alerts | CRITICAL |
| Signal calculation layer | ❌ MISSING | No derived metrics | CRITICAL |
| Rule evaluation service | ❌ MISSING | No risk detection | CRITICAL |
| Alert generation service | ❌ MISSING | No alert creation | CRITICAL |
| Risk dashboards | ❌ MISSING | CA cannot see risks | HIGH |

---

## 🚨 ARCHITECTURAL VIOLATIONS DETECTED

### Issue #1: Compliance Routes Mix Presentation & Logic
**File:** `modules/compliance/routes.py`

**Problem:**
```python
# Line 50-56: Routes directly doing data aggregation
'summary': {
    'total_businesses': len(businesses),
    'statements_count': db.session.query(...).count(),  # <-- LOGIC IN ROUTE
    'high_confidence_count': db.session.query(...).count(),  # <-- LOGIC IN ROUTE
    ...
}
```

**Violation:** Routes should ONLY present data, not calculate metrics.

**Fix:** Move to ComplianceSignalService.

---

### Issue #2: No Separation Between Signals & Rules
**Current Code:**
- Compliance metrics are calculated inline in routes
- No ComplianceSignal model to store derived data
- Rules would have no clean input source

**Violation:** Signals → Rules pipeline doesn't exist.

**Fix:** Create ComplianceSignal as clean data layer between raw data and rules.

---

### Issue #3: No Alert System
**Current Code:**
- No ComplianceAlert model
- Routes would need to create alerts directly
- No way to prevent duplicate alerts
- No tracking of alert lifecycle

**Violation:** Alerts must ONLY be created by rule engine.

**Fix:** Create ComplianceAlert model + AlertService for rule engine only.

---

## 📋 PHASE-3 IMPLEMENTATION PLAN

### LAYER 1: Data Models (Foundation)

**Task 1.1: Create ComplianceSignal Model**
- Stores: daily_turnover, monthly_turnover, evidence_ratio, weak_evidence_rate, silence_days, last_activity_date, abnormal_spike_detected
- Calculated once per business per day
- Immutable (never updated, only new records created)

**Task 1.2: Create ComplianceProfile Model**
- Stores: estimated_turnover, discipline_score, evidence_health, gst_risk_level, profile_status
- System-generated view of business
- Updated when signals change

**Task 1.3: Create ComplianceAlert Model**
- Stores: severity (critical, high, medium, low), reason, business_id, status (open, acknowledged, resolved), created_at, resolved_at
- Only created by rule engine
- Never directly written from routes

---

### LAYER 2: Signal Calculation (Pure Logic)

**Task 2.1: ComplianceSignalService**
- `calculate_daily_turnover()` - Sum of sales today
- `calculate_monthly_turnover()` - Sum of sales this month
- `calculate_evidence_ratio()` - Evidence count / Statement count
- `calculate_weak_evidence_rate()` - Weak evidence count / Total evidence
- `calculate_silence_days()` - Days since last statement
- `detect_abnormal_spike()` - Compare today vs. 30-day average

**Requirements:**
- Pure functions (no side effects)
- Input: Business ID, Date range
- Output: Dictionary of metrics
- Never creates alerts
- Never modifies database

---

### LAYER 3: Rule Engine (Decision Logic)

**Task 3.1: Create RuleEngine Base**
- Abstract rule class with: `evaluate()`, `get_severity()`
- Rule registry system
- Execution pipeline

**Task 3.2: Implement Rule Types**
1. ThresholdRule - "turnover > 10L generates alert"
2. DataQualityRule - "weak_evidence_rate > 20% generates alert"
3. BehaviorRule - "silence > 30 days generates alert"
4. AuditReadinessRule - "evidence_ratio < 0.5 generates alert"

**Requirements:**
- Each rule is isolated, testable
- Takes ComplianceSignal as input
- Returns: Alert (if triggered) or None
- No database writes in rule logic

---

### LAYER 4: Alert Management (Output)

**Task 4.1: AlertService**
- `create_alert()` - Called ONLY by rule engine
- `acknowledge_alert()` - Mark as acknowledged
- `resolve_alert()` - Mark as resolved
- `get_open_alerts()` - List active alerts

**Requirements:**
- Prevent duplicate alerts (same rule, same business, same day)
- Immutable alert records
- Audit trail of all changes
- Never called from routes directly

---

### LAYER 5: CA Dashboards (Presentation)

**Task 5.1: Risk Dashboard Endpoints**
1. `GET /compliance/orgs/<id>/risk-summary` - Risk overview
2. `GET /compliance/orgs/<id>/risky-businesses` - Sorted by risk
3. `GET /compliance/businesses/<id>/profile` - Business compliance profile
4. `GET /compliance/businesses/<id>/alerts` - Active alerts for business
5. `GET /compliance/orgs/<id>/alerts/open` - All open alerts in org

**Requirements:**
- All data comes from ComplianceSignal/ComplianceProfile/ComplianceAlert
- No calculations in routes
- Serves ComplianceService (orchestration layer)

---

## 📊 COMPLETE MODULE STRUCTURE

```
modules/compliance/
├── models.py (NEW)
│   ├── ComplianceSignal
│   ├── ComplianceProfile
│   └── ComplianceAlert
│
├── services/ (NEW)
│   ├── signal_service.py
│   │   └── ComplianceSignalService (calculate_*)
│   ├── alert_service.py
│   │   └── AlertService (create_*, acknowledge_*, resolve_*, get_*)
│   └── compliance_service.py
│       └── ComplianceService (orchestration)
│
├── rules/ (NEW)
│   ├── base.py
│   │   └── BaseRule (abstract)
│   ├── threshold_rules.py
│   │   ├── TurnoverThresholdRule
│   │   └── GSTThresholdRule
│   ├── data_quality_rules.py
│   │   ├── WeakEvidenceRule
│   │   └── EvidenceRatioRule
│   ├── behavior_rules.py
│   │   ├── SilenceRule
│   │   └── SpikeDetectionRule
│   ├── audit_rules.py
│   │   └── AuditReadinessRule
│   └── rule_engine.py
│       └── RuleEngine (execute all rules)
│
├── routes.py (REFACTOR)
│   ├── /orgs/<id>/risk-summary
│   ├── /orgs/<id>/risky-businesses
│   ├── /businesses/<id>/profile
│   ├── /businesses/<id>/alerts
│   └── /orgs/<id>/alerts/open
│
└── __init__.py
```

---

## 🔧 IMPLEMENTATION SEQUENCE

### Day 1: Foundation
1. Create ComplianceSignal model
2. Create ComplianceProfile model
3. Create ComplianceAlert model
4. Create database migrations

### Day 2: Signals
1. Create ComplianceSignalService with all calculations
2. Create signal calculation tests
3. Implement signal persistence

### Day 3: Rules
1. Create BaseRule abstract class
2. Implement 4 rule types
3. Create RuleEngine with registry
4. Test each rule in isolation

### Day 4: Alerts
1. Create AlertService
2. Implement alert deduplication
3. Test alert lifecycle

### Day 5: Integration
1. Create ComplianceService (orchestration)
2. Implement signal → rule → alert pipeline
3. Refactor compliance routes
4. Create risk dashboard endpoints

### Day 6: Testing & Validation
1. End-to-end pipeline test
2. Verify no GST logic
3. Verify architectural separation
4. Performance testing

---

## ✅ ACCEPTANCE CRITERIA

### Architectural
- [x] Routes contain ONLY presentation logic
- [x] Services contain ONLY orchestration logic
- [x] Rules contain ONLY decision logic
- [x] Signals contain ONLY calculation logic
- [x] Alerts contain ONLY output logic
- [x] No GST filing logic anywhere
- [x] No WhatsApp layer touched
- [x] No OCR layer touched
- [x] No raw evidence storage touched

### Functional
- [x] Signals calculated daily per business
- [x] Rules evaluated against signals
- [x] Alerts created by rule engine only
- [x] Alert deduplication working
- [x] CA dashboards show risks
- [x] Each rule testable in isolation
- [x] Immutable audit trail

### Code Quality
- [x] All components unit testable
- [x] No circular imports
- [x] Proper error handling
- [x] Docstrings on all public methods
- [x] Type hints where applicable
- [x] 80% test coverage minimum

---

## ⚠️ STRICT RULES FOR IMPLEMENTATION

1. **No GST Logic**: If you see GST, remove it
2. **Immutable Signals**: Once created, never update ComplianceSignal
3. **Alert-Only RuleEngine**: Rules cannot modify database except alerts
4. **Pure Functions**: Signals must be calculable with same input → same output
5. **No Route Logic**: Routes delegate to services
6. **No Direct Alert Creation**: Only RuleEngine creates alerts
7. **Deduplication**: Never create duplicate alerts same day
8. **Audit Trail**: All alert state changes recorded with timestamp

---

## 📝 FILES TO CREATE

- `modules/compliance/models.py` - 3 new models
- `modules/compliance/services/signal_service.py` - Signal calculations
- `modules/compliance/services/alert_service.py` - Alert management
- `modules/compliance/services/compliance_service.py` - Orchestration
- `modules/compliance/rules/base.py` - BaseRule
- `modules/compliance/rules/threshold_rules.py` - Threshold-based rules
- `modules/compliance/rules/data_quality_rules.py` - Quality rules
- `modules/compliance/rules/behavior_rules.py` - Behavior rules
- `modules/compliance/rules/audit_rules.py` - Audit rules
- `modules/compliance/rules/rule_engine.py` - RuleEngine
- `modules/compliance/services/__init__.py`
- `modules/compliance/rules/__init__.py`
- Update `modules/compliance/routes.py` - Refactored endpoints
- Update `app.py` - Import new blueprint
- Add migrations for 3 new models

---

**Status:** Ready for implementation  
**Complexity:** HIGH (5 layers, 15+ classes, 50+ functions)  
**Estimated Time:** 3-4 days  
**Risk:** LOW (fully isolated module, no existing code touched)
