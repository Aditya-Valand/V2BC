from core.extensions import db
from modules.organizations.models import Organization

def create_org(name, owner_id):
    org = Organization(name=name, owner_id=owner_id)
    db.session.add(org)
    db.session.commit()
    return org

def get_orgs(owner_id):
    return Organization.query.filter_by(owner_id=owner_id).all()
