from datetime import datetime

from core.extensions import db


# ------------------------------------------------------------------ #
# User
# ------------------------------------------------------------------ #

class User(db.Model):
    """
    Represents every person in the system.

    Roles
    -----
    ca_owner  — registered CA, owns an org, full access
    ca_staff  — added to an org by a ca_owner, limited access
    client    — micro-business owner, can only see their own data
    """
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)   # nullable for client (phone-only) users
    phone = db.Column(db.String(15), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="ca_owner")

    # Preferences / push
    fcm_token = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(5), nullable=False, default="en")

    # Email verification + OTP
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    otp_code = db.Column(db.String(10), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, nullable=False, default=0)
    otp_last_sent_at = db.Column(db.DateTime, nullable=True)  # cooldown enforcement

    # Audit
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    memberships = db.relationship(
        "OrgMember", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

    # ---------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------- #

    @property
    def is_ca(self):
        return self.role in ("ca_owner", "ca_staff")

    @property
    def primary_org(self):
        """Returns the Organization for a ca_owner (first owned org)."""
        membership = (
            self.memberships
            .filter_by(role="ca_owner")
            .first()
        )
        return membership.org if membership else None

    def clear_otp(self):
        """Called after successful verification or explicit invalidation."""
        self.otp_code = None
        self.otp_expires_at = None
        self.otp_attempts = 0

    def is_otp_expired(self):
        if not self.otp_expires_at:
            return True
        return datetime.utcnow() > self.otp_expires_at

    def is_otp_locked(self, max_attempts: int):
        return self.otp_attempts >= max_attempts


# ------------------------------------------------------------------ #
# OrgMember  (replaces UserOrganizationPermission)
# ------------------------------------------------------------------ #

class OrgMember(db.Model):
    """
    Join table between User and Organization.
    Controls which users can access which CA firm and at what privilege level.
    """
    __tablename__ = "org_members"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    org_id = db.Column(
        db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    # ca_owner  — full access, can add/remove staff
    # manager   — can manage clients, cannot add org members
    # staff     — read + limited write on assigned clients
    role = db.Column(db.String(20), nullable=False, default="staff")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "org_id", name="uq_org_member_user_org"),
    )

    # Relationships
    user = db.relationship("User", back_populates="memberships")
    org = db.relationship("Organization", back_populates="members")

    def __repr__(self):
        return f"<OrgMember user={self.user_id} org={self.org_id} role={self.role}>"


# ------------------------------------------------------------------ #
# JWTBlocklist
# ------------------------------------------------------------------ #

class JWTBlocklist(db.Model):
    """
    Stores revoked JWT token IDs (jti).
    Used by the jwt.token_in_blocklist_loader callback to honour logout.

    Cleanup: run a weekly job —
        DELETE FROM jwt_blocklist WHERE expires_at < NOW()
    """
    __tablename__ = "jwt_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # 'access' or 'refresh'
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<JWTBlocklist jti={self.jti} type={self.token_type}>"


# ------------------------------------------------------------------ #
# Backward-compatibility alias
# Other modules (e.g. compliance/routes.py) that were written against
# the old model name continue to work without changes.
# New code should use OrgMember directly.
# ------------------------------------------------------------------ #
UserOrganizationPermission = OrgMember
