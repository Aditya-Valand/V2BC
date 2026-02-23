from core.extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20))  # CA, staff, client
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserOrganizationPermission(db.Model):
    """
    Maps users to organizations with specific roles.
    Controls who can access which organizations and their businesses.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    role = db.Column(db.String(50), default="staff")  # owner, manager, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure one role per user per organization
    __table_args__ = (db.UniqueConstraint('user_id', 'organization_id', name='uq_user_org'),)
