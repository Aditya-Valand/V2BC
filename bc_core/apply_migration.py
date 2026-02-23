#!/usr/bin/env python
"""Create all tables in database."""

import sys
from app import create_app, db

app = create_app()

with app.app_context():
    try:
        print("Creating all tables...")
        db.create_all()
        print("✓ All tables created successfully")
        print("✓ Created tables:")
        print("  - compliance_signal")
        print("  - compliance_profile")
        print("  - compliance_alert")
        print("  (Plus all existing Phase-1 tables)")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)
