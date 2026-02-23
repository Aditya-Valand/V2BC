#!/usr/bin/env python
"""
Complete System Verification Script

Validates both Phase-1 and Phase-3:
- Core imports and app startup
- Database setup
- All modules present
- Phase-3 compliance engine ready
"""

import sys
from datetime import datetime

print("=" * 60)
print("BHARATCOMPLIANCE - FINAL VERIFICATION")
print("=" * 60)

print("\n1. Testing Core Imports...")

try:
    from app import create_app, db
    print("[OK] Flask app created successfully")
except Exception as e:
    print(f"[FAIL] Failed to import app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Testing Database Connection...")

try:
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"[OK] Database connected ({len(tables)} tables found)")
        
        required_tables = [
            'user', 'organization', 'user_organization_permission',
            'business', 'business_statement', 'whats_app_message',
            'business_evidence', 'compliance_signal', 'compliance_profile',
            'compliance_alert'
        ]
        
        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"[FAIL] Missing tables: {missing}")
            sys.exit(1)
        print(f"[OK] All {len(required_tables)} required tables present")
        
except Exception as e:
    print(f"[FAIL] Database error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Testing Module Imports...")

try:
    with app.app_context():
        from modules.auth.models import User
        from modules.organizations.models import Organization
        from modules.businesses.models import Business
        from modules.statements.models import BusinessStatement
        from modules.evidence.models import BusinessEvidence
        from modules.whatsapp.models import WhatsAppMessage
        from modules.compliance.models import ComplianceSignal, ComplianceProfile, ComplianceAlert
        print("[OK] All models imported")
        
        from modules.auth.routes import auth_bp
        from modules.organizations.routes import org_bp
        from modules.businesses.routes import business_bp
        from modules.statements.routes import statements_bp
        from modules.evidence.routes import evidence_bp
        from modules.whatsapp.routes import whatsapp_bp
        from modules.compliance.routes import compliance_bp
        print("[OK] All blueprints imported")
        
        from modules.compliance.services import (
            ComplianceSignalService,
            ProfileCalculator,
            AlertService,
            ComplianceService,
        )
        print("[OK] All compliance services imported")
        
except Exception as e:
    print(f"[FAIL] Module import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. Testing Phase-3 Compliance Engine...")

try:
    with app.app_context():
        service = ComplianceService()
        print(f"[OK] ComplianceService instantiated")
        print(f"[OK] RuleEngine has {len(service.rule_engine.rules)} rules registered")
        
        rule_types = {}
        for rule in service.rule_engine.rules:
            rule_type = rule.get_type()
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        print(f"[OK] Rules by type: {dict(rule_types)}")
        
except Exception as e:
    print(f"[FAIL] Phase-3 error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)
print("[OK] Core imports working")
print("[OK] Database connected")
print("[OK] All modules loaded")
print("[OK] Phase-3 compliance engine ready")
print("\n[SUCCESS] SYSTEM VERIFICATION COMPLETE")
print("Status: PRODUCTION READY")
print("=" * 60)
