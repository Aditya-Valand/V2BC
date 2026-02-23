from core.extensions import db
from modules.businesses.models import Business

def create_business(data):
    b = Business(**data)
    db.session.add(b)
    db.session.commit()
    return b

def list_businesses(org_id):
    return Business.query.filter_by(org_id=org_id).all()
