import sys
sys.path.insert(0, '.')

print("Step 1: Import Flask")
from flask import Flask

print("Step 2: Import Config")
from core.config import Config

print("Step 3: Create app")
app = Flask(__name__)
app.config.from_object(Config)

print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

print("Step 4: Import extensions")
from core.extensions import db

print("Step 5: Init db")
db.init_app(app)

print("Step 6: Import models")
from modules.auth.models import User, UserOrganizationPermission
from modules.organizations.models import Organization
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.whatsapp.models import WhatsAppMessage

print("Step 7: Create all tables")
with app.app_context():
    print(f"Registered models: {db.Model.registry.mappers}")
    db.create_all()
    print("Tables created")
    
    import sqlite3
    conn = sqlite3.connect('bc_dev.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"Tables in DB: {[t[0] for t in tables]}")
    conn.close()
