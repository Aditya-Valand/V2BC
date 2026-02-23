import sys
sys.path.insert(0, '.')
from app import app, db

with app.app_context():
    try:
        db.create_all()
        print('Created all tables successfully')
        
        # Check what tables were created
        import sqlite3
        conn = sqlite3.connect('bc_dev.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = c.fetchall()
        print(f'Tables in database: {len(tables)}')
        for table in tables:
            print(f'  - {table[0]}')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
