"""
Marshmallow schemas for the auth module.

Request schemas  — validate + deserialise incoming JSON.
Response schemas — serialise outgoing data (never expose password/otp fields).
"""
import re

from marshmallow import (
    Schema, fields, validate, validates, ValidationError, pre_load, post_load
)


# ------------------------------------------------------------------ #
# Custom validators
# ------------------------------------------------------------------ #

def _validate_password_strength(value: str):
    """
    Rules:
    - At least 8 characters
    - At least 1 digit
    Maximum length is implicitly capped at 128 by the String field validator.
    """
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if not re.search(r"\d", value):
        raise ValidationError("Password must contain at least one number.")


def _validate_phone(value: str):
    """Accept 10-digit Indian numbers or E.164 format (+91XXXXXXXXXX)."""
    cleaned = re.sub(r"[\s\-()]", "", value)
    if not re.fullmatch(r"(\+?91)?[6-9]\d{9}", cleaned):
        raise ValidationError(
            "Enter a valid Indian mobile number (10 digits starting with 6-9)."
        )


# ------------------------------------------------------------------ #
# Nested sub-schemas used in responses
# ------------------------------------------------------------------ #

class OrgPublicSchema(Schema):
    """Safe org fields to include in auth responses."""
    id = fields.Int(dump_default=None)
    name = fields.Str()
    city = fields.Str()
    state = fields.Str()
    plan = fields.Str()
    client_count = fields.Int()


class UserPublicSchema(Schema):
    """Safe user fields. Password, OTP and internal fields are excluded."""
    id = fields.Int()
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    role = fields.Str()
    language = fields.Str()
    is_verified = fields.Bool()
    last_login = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class RegisterSchema(Schema):
    """
    POST /auth/register
    Creates a CA user + their organisation in a single request.
    """
    # Personal details
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=120, error="Name must be 2–120 characters.")
    )
    email = fields.Email(
        required=True,
        validate=validate.Length(max=120)
    )
    password = fields.Str(
        required=True,
        validate=[
            validate.Length(max=128, error="Password must be at most 128 characters."),
            _validate_password_strength,
        ],
        load_only=True   # never serialise the password back
    )
    phone = fields.Str(
        load_default=None,
        validate=_validate_phone,
        allow_none=True
    )

    # Firm details
    firm_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=150, error="Firm name must be 2–150 characters.")
    )
    city = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    state = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100)
    )
    license_number = fields.Str(
        load_default=None,
        validate=validate.Length(max=50),
        allow_none=True
    )

    @pre_load
    def normalise(self, data, **kwargs):
        """Strip whitespace and normalise email to lowercase before validation."""
        if isinstance(data.get("email"), str):
            data["email"] = data["email"].lower().strip()
        if isinstance(data.get("name"), str):
            data["name"] = data["name"].strip()
        if isinstance(data.get("firm_name"), str):
            data["firm_name"] = data["firm_name"].strip()
        return data


class VerifyOTPSchema(Schema):
    """POST /auth/verify-otp"""
    user_id = fields.Int(required=True)
    otp = fields.Str(
        required=True,
        validate=validate.Regexp(r"^\d{6}$", error="OTP must be exactly 6 digits.")
    )


class LoginSchema(Schema):
    """POST /auth/login"""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)

    @pre_load
    def normalise_email(self, data, **kwargs):
        if isinstance(data.get("email"), str):
            data["email"] = data["email"].lower().strip()
        return data


class ResendOTPSchema(Schema):
    """POST /auth/resend-otp"""
    user_id = fields.Int(required=True)


class ClientLoginSchema(Schema):
    """POST /auth/client-login — phone + PIN for client users."""
    phone = fields.Str(required=True, validate=_validate_phone)
    pin = fields.Str(
        required=True,
        validate=validate.Regexp(r"^\d{4,6}$", error="PIN must be 4–6 digits."),
        load_only=True,
    )

    @pre_load
    def normalise(self, data, **kwargs):
        if isinstance(data.get("phone"), str):
            data["phone"] = data["phone"].strip()
        return data


class RefreshSchema(Schema):
    """
    POST /auth/refresh
    No body needed — refresh token is read from the Authorization header
    by Flask-JWT-Extended.  Schema kept for completeness.
    """
    pass


class UpdateProfileSchema(Schema):
    """PUT /auth/me — update name and/or phone."""
    name = fields.Str(
        load_default=None,
        validate=validate.Length(min=2, max=120, error="Name must be 2–120 characters."),
        allow_none=True,
    )
    phone = fields.Str(
        load_default=None,
        validate=_validate_phone,
        allow_none=True,
    )

    @pre_load
    def normalise(self, data, **kwargs):
        if isinstance(data.get("name"), str):
            data["name"] = data["name"].strip()
        if isinstance(data.get("phone"), str):
            data["phone"] = data["phone"].strip()
        return data


class ChangePasswordSchema(Schema):
    """PUT /auth/me/password — change password."""
    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(
        required=True,
        validate=[
            validate.Length(max=128, error="Password must be at most 128 characters."),
            _validate_password_strength,
        ],
        load_only=True,
    )


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class RegisterResponseSchema(Schema):
    """Returned after a successful register call."""
    user_id = fields.Int()
    message = fields.Str()
    # Only populated in development (APP_ENV != production)
    otp_dev_only = fields.Str(allow_none=True)


class AuthTokenSchema(Schema):
    """Returned after verify-otp and login."""
    access_token = fields.Str()
    refresh_token = fields.Str()
    token_type = fields.Str(dump_default="Bearer")
    user = fields.Nested(UserPublicSchema)
    org = fields.Nested(OrgPublicSchema, allow_none=True)
