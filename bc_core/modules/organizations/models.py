from datetime import datetime

from core.extensions import db


class Organization(db.Model):
    """
    Represents a CA firm.
    One CA firm can have many clients and multiple staff members.
    """
    __tablename__ = "organization"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )

    # Location
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)

    # Optional professional credential
    license_number = db.Column(db.String(50), nullable=True)  # ICAI membership no.

    # Billing plan
    plan = db.Column(db.String(20), nullable=False, default="free")  # free | paid
    plan_expires_at = db.Column(db.DateTime, nullable=True)

    # Denormalized count — updated when clients are added/removed
    # Avoids a COUNT(*) query on every dashboard load
    client_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    members = db.relationship(
        "OrgMember", back_populates="org", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization id={self.id} name={self.name}>"
