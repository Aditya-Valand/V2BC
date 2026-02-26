import sys
import os
sys.path.insert(0, '.')
os.chdir('c:\\Users\\bhati\\OneDrive\\Desktop\\bybt\\GFGBQ-Team-teamzero\\bc_core')

from flask import Flask
from core.extensions import db

app = Flask(__name__)

# Use absolute path
db_path = 'c:\\Users\\bhati\\OneDrive\\Desktop\\bybt\\GFGBQ-Team-teamzero\\bc_core\\bc_dev.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Import models
from modules.auth.models import User, OrgMember, UserOrganizationPermission, JWTBlocklist
from modules.organizations.models import Organization
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.whatsapp.models import WhatsAppMessage

with app.app_context():
    db.create_all()
    print('Tables created successfully')
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f'Tables in DB ({len(tables)}):')
    for t in tables:
        print(f'  - {t[0]}')
    conn.close()
