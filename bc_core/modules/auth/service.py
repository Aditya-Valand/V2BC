"""
Auth service layer.

All business logic for registration, OTP, login, and logout lives here.
Routes only validate input, call these functions, and format responses.
"""
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from core.extensions import db
from core.security import hash_password, verify_password
from modules.auth.models import JWTBlocklist, OrgMember, User
from modules.organizations.models import Organization

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Sentinel hash used to prevent timing attacks on login.
# We run verify_password even for unknown emails so the response time
# is indistinguishable from a real wrong-password attempt.
# Pre-computed bcrypt hash of "BharatC0mpliance_sentinel_x9k2m"
# ------------------------------------------------------------------ #
_DUMMY_HASH = "$2b$12$vK8Pjz9mXQw3rN5LhYdT4uWsIoA2cE6fGbHjKlMnOpQrStUvWxYz0"


# ------------------------------------------------------------------ #
# OTP helpers
# ------------------------------------------------------------------ #

def _generate_otp(length: int = 6) -> str:
    """Return a cryptographically random numeric OTP string."""
    return "".join(random.SystemRandom().choices(string.digits, k=length))


def _otp_expiry() -> datetime:
    minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    return datetime.utcnow() + timedelta(minutes=minutes)


# ------------------------------------------------------------------ #
# Registration
# ------------------------------------------------------------------ #

def register_ca(
    *,
    name: str,
    email: str,
    password: str,
    firm_name: str,
    city: str,
    state: str,
    phone: Optional[str] = None,
    license_number: Optional[str] = None,
) -> Tuple[User, Organization, str]:
    """
    Create a CA user + their organisation + owner OrgMember in one
    atomic transaction.

    Returns (user, org, otp_code).
    Raises ValueError with a user-friendly message on business-rule failures.
    Raises IntegrityError (from SQLAlchemy) if email/phone already exists —
    the route layer converts this to a 409.
    """
    # -- Uniqueness guard (before hitting the DB constraint) ---------- #
    if User.query.filter_by(email=email).first():
        raise ValueError("An account with this email address already exists.")

    if phone:
        normalised_phone = _normalise_phone(phone)
        if User.query.filter_by(phone=normalised_phone).first():
            raise ValueError("An account with this phone number already exists.")
    else:
        normalised_phone = None

    # -- Create all objects ------------------------------------------ #
    otp = _generate_otp()

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role="ca_owner",
        phone=normalised_phone,
        is_verified=False,
        otp_code=otp,
        otp_expires_at=_otp_expiry(),
        otp_attempts=0,
        otp_last_sent_at=datetime.utcnow(),
    )

    org = Organization(
        name=firm_name,
        city=city,
        state=state,
        license_number=license_number,
        plan="free",
        client_count=0,
    )

    # Wrap in a single transaction so partial writes are impossible
    try:
        db.session.add(user)
        db.session.flush()       # assigns user.id without committing

        org.owner_id = user.id
        db.session.add(org)
        db.session.flush()       # assigns org.id

        membership = OrgMember(
            user_id=user.id,
            org_id=org.id,
            role="ca_owner",
        )
        db.session.add(membership)
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    logger.info("New CA registered: user_id=%d org_id=%d email=%s", user.id, org.id, email)
    return user, org, otp


def _normalise_phone(phone: str) -> str:
    """Strip all non-digit chars and ensure we store the 10-digit local number."""
    import re
    digits = re.sub(r"\D", "", phone)
    # Strip leading country code if present
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits


# ------------------------------------------------------------------ #
# OTP verification
# ------------------------------------------------------------------ #

def verify_otp(*, user_id: int, otp: str) -> Tuple[User, Organization]:
    """
    Validate the OTP for a given user and mark them verified.

    Returns (user, org) on success.
    Raises ValueError with a specific message on every failure path.
    """
    cfg = current_app.config
    max_attempts = cfg.get("OTP_MAX_ATTEMPTS", 5)

    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found.")

    if user.is_verified:
        raise ValueError("This account is already verified. Please log in.")

    # -- Guard: too many wrong attempts ------------------------------ #
    if user.is_otp_locked(max_attempts):
        raise ValueError(
            "Too many incorrect attempts. Please request a new OTP."
        )

    # -- Guard: OTP expired ------------------------------------------ #
    if user.is_otp_expired():
        raise ValueError(
            "This OTP has expired. Please request a new one."
        )

    # -- Guard: wrong OTP -------------------------------------------- #
    if user.otp_code != otp:
        user.otp_attempts += 1
        remaining = max_attempts - user.otp_attempts
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        if remaining <= 0:
            raise ValueError(
                "Too many incorrect attempts. Please request a new OTP."
            )
        raise ValueError(
            f"Invalid OTP. {remaining} attempt{'s' if remaining > 1 else ''} remaining."
        )

    # -- Success: mark verified, clear OTP --------------------------- #
    user.is_verified = True
    user.last_login = datetime.utcnow()
    user.clear_otp()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # Fetch org for the response
    membership = OrgMember.query.filter_by(user_id=user.id).first()
    org = membership.org if membership else None

    logger.info("User verified: user_id=%d", user.id)
    return user, org


# ------------------------------------------------------------------ #
# Resend OTP
# ------------------------------------------------------------------ #

def resend_otp(*, user_id: int) -> Tuple[User, str]:
    """
    Issue a fresh OTP for a user who has not yet verified.

    Enforces a per-user cooldown (OTP_RESEND_COOLDOWN_SECONDS) to prevent
    abuse even when the IP-level rate limit is not hit (e.g. rotating IPs).

    Returns (user, new_otp).
    Raises ValueError on every failure path.
    """
    cfg = current_app.config
    cooldown = cfg.get("OTP_RESEND_COOLDOWN_SECONDS", 60)

    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found.")

    if user.is_verified:
        raise ValueError("Account is already verified. Please log in.")

    # -- Cooldown check --------------------------------------------- #
    if user.otp_last_sent_at:
        elapsed = (datetime.utcnow() - user.otp_last_sent_at).total_seconds()
        if elapsed < cooldown:
            wait = int(cooldown - elapsed)
            raise ValueError(
                f"Please wait {wait} second{'s' if wait != 1 else ''} before requesting another OTP."
            )

    new_otp = _generate_otp()
    user.otp_code = new_otp
    user.otp_expires_at = _otp_expiry()
    user.otp_attempts = 0                 # reset attempt counter on resend
    user.otp_last_sent_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user, new_otp


# ------------------------------------------------------------------ #
# Login
# ------------------------------------------------------------------ #

def login(*, email: str, password: str) -> Tuple[User, Organization]:
    """
    Authenticate a CA user by email + password.

    SECURITY: This function always runs verify_password even when the
    email is not found (constant-time defence against user enumeration).

    Returns (user, org) on success.
    Raises ValueError with a deliberately vague message to avoid leaking
    whether the email exists.
    """
    _VAGUE_ERROR = "Invalid email or password."

    user: Optional[User] = User.query.filter_by(email=email).first()

    # Always call verify_password so timing is identical regardless of
    # whether the email exists.
    hash_to_check = user.password if user else _DUMMY_HASH
    password_ok = verify_password(password, hash_to_check)

    if not user or not password_ok:
        raise ValueError(_VAGUE_ERROR)

    # -- Email not yet verified -------------------------------------- #
    if not user.is_verified:
        raise ValueError(
            "Please verify your email before logging in. "
            "Check your inbox for the OTP or request a new one."
        )

    # -- Only CA users can log in via this endpoint ------------------ #
    if user.role not in ("ca_owner", "ca_staff"):
        raise ValueError(_VAGUE_ERROR)

    # -- Record login time ------------------------------------------- #
    user.last_login = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    membership = OrgMember.query.filter_by(user_id=user.id).first()
    org = membership.org if membership else None

    logger.info("User logged in: user_id=%d", user.id)
    return user, org


# ------------------------------------------------------------------ #
# Token generation helpers
# ------------------------------------------------------------------ #

def create_tokens(user: User, org: Optional[Organization]) -> dict:
    """
    Build the access + refresh token pair.

    The JWT `identity` is the user's integer ID.
    Additional claims (role, org_id) are stored in the token for fast
    access without a DB round-trip.
    """
    additional_claims = {
        "role": user.role,
        "org_id": org.id if org else None,
    }
    # PyJWT 2.9+ requires the sub claim to be a string (RFC 7519 strict mode).
    # We store the user id as a string here and convert back to int on read.
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims=additional_claims,
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


# ------------------------------------------------------------------ #
# Logout  (blocklist)
# ------------------------------------------------------------------ #

def revoke_token(jti: str, token_type: str, expires_at: datetime) -> None:
    """
    Add a token's jti to the blocklist.
    Called on logout.  Works for both access and refresh tokens.
    """
    entry = JWTBlocklist(
        jti=jti,
        token_type=token_type,
        expires_at=expires_at,
    )
    try:
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def purge_expired_blocklist_entries() -> int:
    """
    Remove expired entries from the JWT blocklist.
    Call this from a scheduled job (weekly is sufficient).
    Returns the number of rows deleted.
    """
    deleted = JWTBlocklist.query.filter(
        JWTBlocklist.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    db.session.commit()
    return deleted
