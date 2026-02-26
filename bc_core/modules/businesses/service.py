"""
Client + Invite service layer.

All business logic lives here.  Routes only validate input, call
these functions, and format responses.
"""
import io
import logging
import random
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple

import segno
from flask import current_app
from sqlalchemy import func

from core.extensions import db
from core.security import hash_password, verify_password
from modules.auth.models import OrgMember, User
from modules.businesses.models import Business
from modules.organizations.models import Organization

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _generate_invite_code() -> str:
    """8-char uppercase alphanumeric invite code (e.g. KX7P2MQ1)."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.SystemRandom().choices(alphabet, k=8))
        if not Business.query.filter_by(invite_code=code).first():
            return code


def _generate_otp(length: int = 6) -> str:
    return "".join(random.SystemRandom().choices(string.digits, k=length))


def _otp_expiry() -> datetime:
    minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    return datetime.utcnow() + timedelta(minutes=minutes)


def _normalise_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits


def _make_invite_url(invite_code: str) -> str:
    frontend = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
    return f"{frontend}/invite/{invite_code}"


def _make_qr_svg(url: str) -> str:
    """Return a compact SVG string for the invite URL."""
    buf = io.BytesIO()
    qr = segno.make_qr(url)
    qr.save(buf, kind="svg", scale=4, border=2)
    return buf.getvalue().decode("utf-8")


# ------------------------------------------------------------------ #
# CA-side: create / list / get / update clients
# ------------------------------------------------------------------ #

def create_client(
    *,
    org_id: int,
    name: str,
    business_type: Optional[str] = None,
    state: Optional[str] = None,
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    expected_turnover: Optional[float] = None,
    phone: Optional[str] = None,
    whatsapp_phone: Optional[str] = None,
) -> dict:
    """
    CA creates a client record.

    Returns dict with the Business object + invite metadata (invite_url, qr_svg).
    Raises ValueError on business-rule violations.
    """
    # Duplicate GSTIN / PAN guard within the org
    if gstin:
        existing = Business.query.filter_by(org_id=org_id, gstin=gstin).first()
        if existing:
            raise ValueError(f"A client with GSTIN {gstin} already exists in this organisation.")

    if pan:
        existing = Business.query.filter_by(org_id=org_id, pan=pan).first()
        if existing:
            raise ValueError(f"A client with PAN {pan} already exists in this organisation.")

    if phone:
        phone = _normalise_phone(phone)
    if whatsapp_phone:
        whatsapp_phone = _normalise_phone(whatsapp_phone)
        existing = Business.query.filter_by(whatsapp_phone=whatsapp_phone).first()
        if existing:
            raise ValueError("This WhatsApp number is already linked to another client.")

    invite_code = _generate_invite_code()

    business = Business(
        org_id=org_id,
        name=name,
        business_type=business_type,
        state=state,
        gstin=gstin,
        pan=pan,
        expected_turnover=expected_turnover,
        phone=phone,
        whatsapp_phone=whatsapp_phone,
        invite_code=invite_code,
        invite_status="pending",
    )

    try:
        db.session.add(business)
        # Increment the org's denormalised client_count
        org = Organization.query.get(org_id)
        if org:
            org.client_count = (org.client_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    invite_url = _make_invite_url(invite_code)
    qr_svg     = _make_qr_svg(invite_url)

    logger.info("Client created: business_id=%d org_id=%d invite_code=%s",
                business.id, org_id, invite_code)

    return {
        "business":   business,
        "invite_url": invite_url,
        "qr_svg":     qr_svg,
    }


def list_clients(org_id: int) -> list:
    """
    Return all clients for an org with summary stats (statement count,
    last activity date, compliance score).

    Uses a single query with LEFT JOINs to avoid N+1.
    """
    from modules.statements.models import BusinessStatement
    from modules.compliance.models import ComplianceProfile

    # Subquery: statement count + latest date per business
    stmt_sq = (
        db.session.query(
            BusinessStatement.business_id.label("bid"),
            func.count(BusinessStatement.id).label("stmt_count"),
            func.max(BusinessStatement.transaction_date).label("last_activity"),
        )
        .group_by(BusinessStatement.business_id)
        .subquery()
    )

    # Subquery: compliance score per business
    cp_sq = (
        db.session.query(
            ComplianceProfile.business_id.label("bid"),
            ComplianceProfile.discipline_score.label("score"),
        )
        .subquery()
    )

    rows = (
        db.session.query(
            Business,
            func.coalesce(stmt_sq.c.stmt_count, 0).label("statement_count"),
            stmt_sq.c.last_activity.label("last_activity"),
            cp_sq.c.score.label("compliance_score"),
        )
        .filter(Business.org_id == org_id)
        .outerjoin(stmt_sq, Business.id == stmt_sq.c.bid)
        .outerjoin(cp_sq,  Business.id == cp_sq.c.bid)
        .order_by(Business.created_at.desc())
        .all()
    )

    result = []
    for business, stmt_count, last_activity, comp_score in rows:
        result.append({
            "id":               business.id,
            "name":             business.name,
            "business_type":    business.business_type,
            "state":            business.state,
            "phone":            business.phone,
            "invite_status":    business.invite_status,
            "is_active":        business.is_active,
            "created_at":       business.created_at,
            "statement_count":  stmt_count,
            "last_activity":    last_activity,
            "compliance_score": comp_score,
        })
    return result


def get_client(org_id: int, client_id: int) -> dict:
    """
    Fetch a single client belonging to the given org.
    Raises ValueError if not found or belongs to a different org.
    """
    business = Business.query.filter_by(id=client_id, org_id=org_id).first()
    if not business:
        raise ValueError("Client not found.")

    owner = business.owner
    return {
        "id":                business.id,
        "org_id":            business.org_id,
        "owner_user_id":     business.owner_user_id,
        "name":              business.name,
        "business_type":     business.business_type,
        "state":             business.state,
        "gstin":             business.gstin,
        "pan":               business.pan,
        "expected_turnover": business.expected_turnover,
        "phone":             business.phone,
        "whatsapp_phone":    business.whatsapp_phone,
        "invite_code":       business.invite_code,
        "invite_status":     business.invite_status,
        "invite_expires_at": business.invite_expires_at,
        "is_active":         business.is_active,
        "created_at":        business.created_at,
        "updated_at":        business.updated_at,
        "owner_name":        owner.name  if owner else None,
        "owner_phone":       owner.phone if owner else None,
    }


def update_client(org_id: int, client_id: int, data: dict) -> Business:
    """
    Update editable fields on a client.
    Raises ValueError if client not found or on constraint violations.
    """
    business = Business.query.filter_by(id=client_id, org_id=org_id).first()
    if not business:
        raise ValueError("Client not found.")

    # GSTIN / PAN uniqueness within org
    if "gstin" in data and data["gstin"]:
        dup = (Business.query
               .filter_by(org_id=org_id, gstin=data["gstin"])
               .filter(Business.id != client_id)
               .first())
        if dup:
            raise ValueError(f"Another client already has GSTIN {data['gstin']}.")

    if "pan" in data and data["pan"]:
        dup = (Business.query
               .filter_by(org_id=org_id, pan=data["pan"])
               .filter(Business.id != client_id)
               .first())
        if dup:
            raise ValueError(f"Another client already has PAN {data['pan']}.")

    if "whatsapp_phone" in data and data["whatsapp_phone"]:
        data["whatsapp_phone"] = _normalise_phone(data["whatsapp_phone"])
        dup = (Business.query
               .filter_by(whatsapp_phone=data["whatsapp_phone"])
               .filter(Business.id != client_id)
               .first())
        if dup:
            raise ValueError("This WhatsApp number is already linked to another client.")

    if "phone" in data and data["phone"]:
        data["phone"] = _normalise_phone(data["phone"])

    # is_active toggle: update invite_status to reflect
    if "is_active" in data and not data["is_active"]:
        business.invite_status = "revoked"

    for field, value in data.items():
        setattr(business, field, value)
    business.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return business


def regenerate_invite(org_id: int, client_id: int) -> dict:
    """
    Issue a new invite code for a client (e.g. old link expired/lost).
    Resets invite_status to 'pending'.
    Raises ValueError if client not found or already active.
    """
    business = Business.query.filter_by(id=client_id, org_id=org_id).first()
    if not business:
        raise ValueError("Client not found.")
    if business.invite_status == "active":
        raise ValueError(
            "Client has already accepted the invite. "
            "Deactivate the client first if you need to re-onboard."
        )

    business.invite_code   = _generate_invite_code()
    business.invite_status = "pending"
    business.updated_at    = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    invite_url = _make_invite_url(business.invite_code)
    return {
        "business":   business,
        "invite_url": invite_url,
        "qr_svg":     _make_qr_svg(invite_url),
    }


# ------------------------------------------------------------------ #
# Public invite flow: landing → accept → verify OTP
# ------------------------------------------------------------------ #

def get_invite_info(invite_code: str) -> dict:
    """
    Public endpoint data for the invite landing page.
    Returns CA name + client name + status.
    Raises ValueError if code is not found.
    """
    business = Business.query.filter_by(invite_code=invite_code).first()
    if not business:
        raise ValueError("Invite not found.")

    org = business.org
    is_expired = (
        business.invite_expires_at is not None
        and datetime.utcnow() > business.invite_expires_at
    )

    return {
        "invite_code":   business.invite_code,
        "ca_firm_name":  org.name if org else "Unknown",
        "client_name":   business.name,
        "invite_status": business.invite_status,
        "is_expired":    is_expired,
    }


def accept_invite(
    *,
    invite_code: str,
    name: str,
    phone: str,
    pin: str,
) -> Tuple[User, Business, str]:
    """
    Client accepts the invite.  Creates a User(role='client') and links
    it to the Business.

    Returns (user, business, otp_code).
    Raises ValueError on every failure path.
    """
    business = Business.query.filter_by(invite_code=invite_code).first()
    if not business:
        raise ValueError("Invalid invite code.")

    if business.invite_status == "revoked":
        raise ValueError("This invite has been revoked. Please contact your CA.")

    if business.invite_status == "active":
        raise ValueError("This invite has already been accepted.")

    if (business.invite_expires_at and
            datetime.utcnow() > business.invite_expires_at):
        raise ValueError("This invite link has expired. Please contact your CA for a new one.")

    phone = _normalise_phone(phone)

    # Phone must not already belong to another user
    existing = User.query.filter_by(phone=phone).first()
    if existing:
        raise ValueError("An account with this phone number already exists. Please log in.")

    otp  = _generate_otp()
    user = User(
        name=name,
        email=None,             # clients are phone-only
        phone=phone,
        password=hash_password(pin),   # PIN stored as bcrypt hash
        role="client",
        is_verified=False,
        otp_code=otp,
        otp_expires_at=_otp_expiry(),
        otp_attempts=0,
        otp_last_sent_at=datetime.utcnow(),
    )

    try:
        db.session.add(user)
        db.session.flush()

        # Link business to this user; keep invite_status='pending' until
        # OTP is verified (verify_client_otp flips it to 'active')
        business.owner_user_id = user.id
        # Store the phone on business too if not already set
        if not business.phone:
            business.phone = phone
        business.updated_at = datetime.utcnow()

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info("Invite accepted: business_id=%d user_id=%d phone=%s",
                business.id, user.id, phone)
    return user, business, otp


def verify_client_otp(*, user_id: int, otp: str) -> Tuple[User, Business]:
    """
    Verify phone OTP for a client after invite acceptance.

    On success:
      - User.is_verified = True
      - Business.invite_status = 'active'
      - Returns (user, business)

    Raises ValueError on every failure path.
    """
    cfg = current_app.config
    max_attempts = cfg.get("OTP_MAX_ATTEMPTS", 5)

    user = User.query.get(user_id)
    if not user or user.role != "client":
        raise ValueError("User not found.")

    if user.is_verified:
        raise ValueError("Account is already verified. Please log in.")

    if user.is_otp_locked(max_attempts):
        raise ValueError("Too many incorrect attempts. Please contact your CA for a new invite.")

    if user.is_otp_expired():
        raise ValueError("OTP has expired. Please contact your CA for a new invite.")

    if user.otp_code != otp:
        user.otp_attempts += 1
        remaining = max_attempts - user.otp_attempts
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        if remaining <= 0:
            raise ValueError("Too many incorrect attempts. Please contact your CA for a new invite.")
        raise ValueError(
            f"Invalid OTP. {remaining} attempt{'s' if remaining > 1 else ''} remaining."
        )

    # Success
    user.is_verified = True
    user.last_login  = datetime.utcnow()
    user.clear_otp()

    business = Business.query.filter_by(owner_user_id=user.id).first()
    if business:
        business.invite_status = "active"
        business.updated_at    = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info("Client OTP verified: user_id=%d business_id=%s",
                user.id, business.id if business else "none")
    return user, business
