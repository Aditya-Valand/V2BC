from datetime import datetime

from core.extensions import db


class Business(db.Model):
    """
    A micro-business client registered under a CA firm (org).

    Lifecycle
    ---------
    CA creates    → invite_status='pending', invite_code set
    Client accepts invite → owner_user_id set, invite_status='active'
    CA deactivates → is_active=False
    """
    __tablename__ = "business"

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(
        db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Client's user account (set after invite is accepted)
    owner_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )

    # Business identity
    name              = db.Column(db.String(150), nullable=False)
    business_type     = db.Column(db.String(50),  nullable=True)
    state             = db.Column(db.String(50),  nullable=True)
    gstin             = db.Column(db.String(20),  nullable=True)
    pan               = db.Column(db.String(20),  nullable=True)
    expected_turnover = db.Column(db.Float,       nullable=True)

    # Contact
    phone          = db.Column(db.String(15), nullable=True)
    whatsapp_phone = db.Column(db.String(20), unique=True, nullable=True)

    # Invite
    invite_code       = db.Column(db.String(12), unique=True, nullable=True, index=True)
    invite_status     = db.Column(db.String(20), nullable=False, default="pending")
    # pending  — created by CA, not yet accepted by client
    # active   — client accepted and verified phone
    # revoked  — CA deactivated this client
    invite_expires_at = db.Column(db.DateTime, nullable=True)

    # Status
    is_active  = db.Column(db.Boolean,  nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owner = db.relationship("User", foreign_keys=[owner_user_id], lazy="select")
    org   = db.relationship(
        "Organization",
        backref=db.backref("businesses", lazy="dynamic")
    )

    def __repr__(self):
        return f"<Business id={self.id} name={self.name} org={self.org_id}>"
