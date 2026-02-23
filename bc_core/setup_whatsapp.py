#!/usr/bin/env python
"""
Update database schema for enhanced WhatsApp integration.

Adds/updates:
1. WhatsAppMessage table with enhanced fields for message tracking
2. BusinessStatement table with new fields for verification and metadata
3. Proper indexes and constraints
"""

from app import create_app, db
from modules.whatsapp.models import WhatsAppMessage
from modules.statements.models import BusinessStatement
from sqlalchemy import inspect, text
import sys

def setup_whatsapp_tables():
    """Set up or update WhatsApp tables in database"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("=" * 60)
        print("WhatsApp Integration Setup")
        print("=" * 60)
        
        # Drop and recreate whats_app_message table if it has old schema
        if 'whats_app_message' in tables:
            print("\n[1] Checking whats_app_message table schema...")
            columns = {col['name'] for col in inspector.get_columns('whats_app_message')}
            
            # Required columns for new schema
            required_columns = {
                'whatsapp_message_id', 'business_id', 'sender_phone',
                'message_type', 'raw_text', 'parsed_text',
                'media_url', 'media_mime_type',
                'extracted_amount', 'extracted_date', 'extracted_type',
                'confidence_score', 'status', 'processing_error',
                'statement_id', 'evidence_id', 'metadata',
                'processed_at', 'created_at', 'updated_at'
            }
            
            missing = required_columns - columns
            if missing or 'sender' in columns or 'processed' in columns or 'media_path' in columns:
                print(f"   [WARN] Old schema detected, recreating table...")
                try:
                    db.session.execute(text('DROP TABLE IF EXISTS whats_app_message'))
                    db.session.commit()
                    print(f"   [OK] Old table dropped")
                except Exception as e:
                    print(f"   [ERROR] Could not drop table: {e}")
                    db.session.rollback()
            else:
                print(f"   [OK] Schema looks good ({len(columns)} columns)")
        
        # Drop and recreate business_statement table if needed
        if 'business_statement' in tables:
            print("\n[2] Checking business_statement table schema...")
            columns = {col['name'] for col in inspector.get_columns('business_statement')}
            
            required_columns = {
                'business_id', 'statement_type', 'amount', 'currency',
                'transaction_date', 'source', 'confidence_level',
                'confidence_reason', 'description', 'verified',
                'verified_by', 'verified_at', 'created_at', 'updated_at'
            }
            
            missing = required_columns - columns
            if missing:
                print(f"   [WARN] Missing columns: {missing}")
                print(f"   [WARN] Recreating table...")
                try:
                    db.session.execute(text('DROP TABLE IF EXISTS business_statement'))
                    db.session.commit()
                    print(f"   [OK] Old table dropped")
                except Exception as e:
                    print(f"   [ERROR] Could not drop table: {e}")
                    db.session.rollback()
            else:
                print(f"   [OK] Schema looks good ({len(columns)} columns)")
        
        # Create or update tables
        print("\n[3] Creating/updating tables...")
        try:
            db.create_all()
            print("   [OK] All tables created/updated")
        except Exception as e:
            print(f"   [ERROR] Failed to create tables: {e}")
            db.session.rollback()
            return False
        
        # Verify tables
        print("\n[4] Verifying tables...")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'whats_app_message' in tables:
            columns = [col['name'] for col in inspector.get_columns('whats_app_message')]
            print(f"   [OK] whats_app_message table ({len(columns)} columns)")
        else:
            print(f"   [ERROR] whats_app_message table not found")
            return False
        
        if 'business_statement' in tables:
            columns = [col['name'] for col in inspector.get_columns('business_statement')]
            print(f"   [OK] business_statement table ({len(columns)} columns)")
        else:
            print(f"   [ERROR] business_statement table not found")
            return False
        
        print("\n" + "=" * 60)
        print("[SUCCESS] WhatsApp integration tables ready!")
        print("=" * 60)
        return True


if __name__ == '__main__':
    success = setup_whatsapp_tables()
    sys.exit(0 if success else 1)
