"""
Auth routes — Feature 1.

Endpoints
---------
POST  /auth/register      — create CA + firm, send OTP
POST  /auth/verify-otp    — confirm OTP, receive tokens
POST  /auth/resend-otp    — request a fresh OTP (with cooldown)
POST  /auth/login         — email + password login
POST  /auth/refresh       — rotate access token with refresh token
GET   /auth/me            — get current user profile
POST  /auth/logout        — revoke the current token

All routes follow a consistent response envelope:
  {"success": true/false, "data": {...}, "error": null/"message"}
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError

from core.extensions import limiter
from modules.auth import service
from modules.auth.email_service import send_otp_email
from modules.auth.models import OrgMember, User
from modules.auth.schemas import (
    AuthTokenSchema,
    ChangePasswordSchema,
    ClientLoginSchema,
    LoginSchema,
    RegisterResponseSchema,
    RegisterSchema,
    ResendOTPSchema,
    UpdateProfileSchema,
    UserPublicSchema,
    OrgPublicSchema,
    VerifyOTPSchema,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _ok(data: dict, status: int = 200):
    return jsonify({"success": True, "data": data, "error": None}), status


def _err(message: str, status: int = 400):
    return jsonify({"success": False, "data": None, "error": message}), status


def _token_expires_at(token_str: str) -> datetime:
    """Decode token to get its expiry as a UTC datetime (for blocklist storage)."""
    decoded = get_jwt()
    exp_ts = decoded.get("exp", 0)
    return datetime.fromtimestamp(exp_ts, tz=timezone.utc).replace(tzinfo=None)


# ------------------------------------------------------------------ #
# POST /auth/register
# ------------------------------------------------------------------ #

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")          # per-IP: prevents mass account creation
def register():
    """
    Create a new CA user + their CA firm organisation.

    On success, stores an OTP in the DB and dispatches it via email.
    The user must call /auth/verify-otp before they can log in.

    Edge cases handled
    ------------------
    - Email already registered          → 409
    - Phone already registered          → 409
    - Weak password                     → 400 (from schema)
    - Missing required fields           → 400 (from schema)
    - Email delivery failure            → 201 still returned (OTP is in DB;
                                          user can call /auth/resend-otp)
    - DB write failure                  → 500
    """
    try:
        data = RegisterSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, org, otp = service.register_ca(
            name=data["name"],
            email=data["email"],
            password=data["password"],
            firm_name=data["firm_name"],
            city=data["city"],
            state=data["state"],
            phone=data.get("phone"),
            license_number=data.get("license_number"),
        )
    except ValueError as exc:
        # Business-rule violation (duplicate email/phone, etc.)
        return _err(str(exc), 409)
    except Exception as exc:
        logger.exception("register: unexpected error — %s", exc)
        return _err("Registration failed due to a server error.", 500)

    # Send OTP; failure is non-fatal
    email_sent = send_otp_email(
        to_email=user.email,
        to_name=user.name,
        otp=otp,
        firm_name=org.name,
    )
    if not email_sent:
        logger.warning("register: OTP email delivery failed for user_id=%d", user.id)

    response_data = {
        "user_id": user.id,
        "message": (
            f"Account created! We've sent a 6-digit verification code to {user.email}."
            if email_sent
            else
            "Account created! Email delivery failed — please use /auth/resend-otp to get your code."
        ),
    }

    # In development, include OTP in the response so devs can test without SMTP
    if current_app.config.get("APP_ENV", "development") != "production":
        response_data["otp_dev_only"] = otp

    return _ok(response_data, 201)


# ------------------------------------------------------------------ #
# POST /auth/verify-otp
# ------------------------------------------------------------------ #

@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("10 per minute")       # per-IP brute-force guard
def verify_otp():
    """
    Confirm the OTP sent during registration.

    On success, marks the user as verified and returns both tokens.

    Edge cases handled
    ------------------
    - Invalid OTP                       → 400 (remaining attempts shown)
    - OTP expired                       → 400
    - OTP locked (too many attempts)    → 400
    - Already verified                  → 400
    - user_id not found                 → 404
    """
    try:
        data = VerifyOTPSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, org = service.verify_otp(
            user_id=data["user_id"],
            otp=data["otp"],
        )
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "not found" in msg.lower() else 400
        return _err(msg, status)
    except Exception as exc:
        logger.exception("verify_otp: unexpected error — %s", exc)
        return _err("Verification failed due to a server error.", 500)

    tokens = service.create_tokens(user, org)

    return _ok({
        **tokens,
        "token_type": "Bearer",
        "user": UserPublicSchema().dump(user),
        "org": OrgPublicSchema().dump(org) if org else None,
    })


# ------------------------------------------------------------------ #
# POST /auth/resend-otp
# ------------------------------------------------------------------ #

@auth_bp.route("/resend-otp", methods=["POST"])
@limiter.limit("5 per hour")          # per-IP guard
def resend_otp():
    """
    Issue a fresh OTP for an unverified user.

    An additional per-user cooldown is enforced inside the service layer
    (OTP_RESEND_COOLDOWN_SECONDS) so rotating IPs can't bypass this.

    Edge cases handled
    ------------------
    - user_id not found                 → 404
    - Already verified                  → 400
    - Within cooldown window            → 429
    - Email delivery failure            → 200 (OTP still updated in DB)
    """
    try:
        data = ResendOTPSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, new_otp = service.resend_otp(user_id=data["user_id"])
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            return _err(msg, 404)
        if "wait" in msg.lower():
            return _err(msg, 429)
        return _err(msg, 400)
    except Exception as exc:
        logger.exception("resend_otp: unexpected error — %s", exc)
        return _err("Could not resend OTP due to a server error.", 500)

    email_sent = send_otp_email(
        to_email=user.email,
        to_name=user.name,
        otp=new_otp,
    )

    response_data = {
        "user_id": user.id,
        "message": (
            f"A new OTP has been sent to {user.email}."
            if email_sent
            else "OTP refreshed but email delivery failed. Please check server logs."
        ),
    }
    if current_app.config.get("APP_ENV", "development") != "production":
        response_data["otp_dev_only"] = new_otp

    return _ok(response_data)


# ------------------------------------------------------------------ #
# POST /auth/login
# ------------------------------------------------------------------ #

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")       # per-IP brute-force guard
def login():
    """
    Authenticate a CA user with email + password.

    Returns access + refresh tokens on success.

    Edge cases handled
    ------------------
    - Wrong email OR wrong password     → 401 (vague message, no leakage)
    - Email not verified                → 403
    - Non-CA role                       → 401 (treated same as wrong creds)
    - DB / unexpected errors            → 500
    """
    try:
        data = LoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, org = service.login(
            email=data["email"],
            password=data["password"],
        )
    except ValueError as exc:
        msg = str(exc)
        # Differentiate verified-but-wrong-creds (401) vs not-verified (403)
        if "verify your email" in msg.lower():
            return _err(msg, 403)
        return _err(msg, 401)
    except Exception as exc:
        logger.exception("login: unexpected error — %s", exc)
        return _err("Login failed due to a server error.", 500)

    tokens = service.create_tokens(user, org)

    return _ok({
        **tokens,
        "token_type": "Bearer",
        "user": UserPublicSchema().dump(user),
        "org": OrgPublicSchema().dump(org) if org else None,
    })


# ------------------------------------------------------------------ #
# POST /auth/client-login
# ------------------------------------------------------------------ #

@auth_bp.route("/client-login", methods=["POST"])
@limiter.limit("10 per minute")       # per-IP brute-force guard
def client_login():
    """
    Authenticate a client user with phone + PIN.

    Returns access + refresh tokens on success.

    Edge cases handled
    ------------------
    - Wrong phone OR wrong PIN           → 401 (vague, no leakage)
    - Non-client role                    → 401
    - Account not yet verified           → 403
    - DB / unexpected errors             → 500
    """
    try:
        data = ClientLoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    try:
        user, org = service.client_login(
            phone=data["phone"],
            pin=data["pin"],
        )
    except ValueError as exc:
        msg = str(exc)
        if "not yet verified" in msg.lower():
            return _err(msg, 403)
        return _err(msg, 401)
    except Exception as exc:
        logger.exception("client_login: unexpected error — %s", exc)
        return _err("Login failed due to a server error.", 500)

    tokens = service.create_tokens(user, org)

    return _ok({
        **tokens,
        "token_type": "Bearer",
        "user": UserPublicSchema().dump(user),
        "org": OrgPublicSchema().dump(org) if org else None,
    })


# ------------------------------------------------------------------ #
# POST /auth/refresh
# ------------------------------------------------------------------ #

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)          # requires Authorization: Bearer <refresh_token>
@limiter.limit("30 per minute")
def refresh():
    """
    Issue a new short-lived access token using a valid refresh token.

    The refresh token itself is NOT rotated here (stateless rotation).
    To fully revoke, the client should call /auth/logout.

    Edge cases handled
    ------------------
    - Expired refresh token             → 401 (JWT middleware)
    - Revoked / blocklisted token       → 401 (JWT middleware)
    - Wrong token type (access used)    → 401 (JWT middleware)
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()

    # Re-fetch user to ensure they haven't been deactivated since the token
    # was issued.  Cheap single-row lookup.
    user = User.query.get(user_id)
    if not user or not user.is_verified:
        return _err("Account not found or not verified.", 401)

    org_id = claims.get("org_id")

    # Self-heal: if org_id is missing from an old token (data-integrity gap),
    # re-look it up from DB so the new access token is valid for CA routes.
    if not org_id and user.role in ("ca_owner", "ca_staff"):
        membership = OrgMember.query.filter_by(user_id=user_id).first()
        if membership:
            org_id = membership.org_id
        else:
            from modules.organizations.models import Organization as _Org
            _org = _Org.query.filter_by(owner_id=user_id).first()
            if _org:
                org_id = _org.id

    additional_claims = {
        "role": claims.get("role", user.role),
        "org_id": org_id,
    }
    new_access_token = create_access_token(
        identity=str(user_id),   # PyJWT 2.9+: sub must be a string
        additional_claims=additional_claims,
    )

    return _ok({
        "access_token": new_access_token,
        "token_type": "Bearer",
    })


# ------------------------------------------------------------------ #
# GET /auth/me
# ------------------------------------------------------------------ #

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Return the currently authenticated user's profile + organisation.

    Edge cases handled
    ------------------
    - Expired / invalid / revoked token → 401 (JWT middleware)
    - user_id in token no longer in DB  → 404
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return _err("User not found.", 404)

    membership = OrgMember.query.filter_by(user_id=user.id).first()
    org = membership.org if membership else None

    return _ok({
        "user": UserPublicSchema().dump(user),
        "org": OrgPublicSchema().dump(org) if org else None,
        "org_role": membership.role if membership else None,
    })


# ------------------------------------------------------------------ #
# POST /auth/logout
# ------------------------------------------------------------------ #

@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
@limiter.limit("30 per hour")
def update_me():
    """Update name and/or phone for the current user."""
    try:
        data = UpdateProfileSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    user_id = int(get_jwt_identity())
    try:
        user = service.update_profile(
            user_id,
            name=data.get("name"),
            phone=data.get("phone"),
        )
    except ValueError as exc:
        return _err(str(exc), 409 if "already" in str(exc) else 400)
    except Exception as exc:
        logger.exception("update_me: unexpected error — %s", exc)
        return _err("Update failed due to a server error.", 500)

    return _ok({"user": UserPublicSchema().dump(user), "message": "Profile updated."})


@auth_bp.route("/me/password", methods=["PUT"])
@jwt_required()
@limiter.limit("10 per hour")
def change_password():
    """Change the current user's password."""
    try:
        data = ChangePasswordSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _err(exc.messages, 400)

    user_id = int(get_jwt_identity())
    try:
        service.change_password(
            user_id,
            current_password=data["current_password"],
            new_password=data["new_password"],
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:
        logger.exception("change_password: unexpected error — %s", exc)
        return _err("Password change failed due to a server error.", 500)

    return _ok({"message": "Password changed successfully."})


@auth_bp.route("/fcm-token", methods=["PUT"])
@jwt_required()
@limiter.limit("20 per hour")
def register_fcm_token():
    """Store or update the FCM device token for push notifications."""
    data = request.get_json(silent=True) or {}
    token = (data.get("fcm_token") or "").strip()
    if not token:
        return _err("fcm_token is required.", 400)

    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return _err("User not found.", 404)

    from core.extensions import db as _db
    user.fcm_token = token
    _db.session.commit()
    logger.info("FCM token registered for user_id=%d", user_id)
    return _ok({"message": "FCM token registered."})


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)     # accept both access and refresh tokens
def logout():
    """
    Revoke the current token by adding its jti to the blocklist.

    Call this with the access token OR the refresh token (or both in
    two separate requests) to fully invalidate a session.

    Edge cases handled
    ------------------
    - Already expired token             → still blocklisted (idempotent)
    - DB error during blocklist insert  → 500
    """
    jwt_data = get_jwt()
    jti = jwt_data.get("jti")
    token_type = jwt_data.get("type", "access")
    exp_ts = jwt_data.get("exp", 0)
    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc).replace(tzinfo=None)

    try:
        service.revoke_token(jti=jti, token_type=token_type, expires_at=expires_at)
    except Exception as exc:
        logger.exception("logout: failed to revoke token jti=%s — %s", jti, exc)
        return _err("Logout failed. Please try again.", 500)

    return _ok({"message": "Successfully logged out."})
