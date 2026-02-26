"""
Marshmallow schemas for the clients + invite feature.
"""
import re

from marshmallow import Schema, fields, validate, validates, ValidationError, pre_load


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class ClientCreateSchema(Schema):
    """CA creates a new client record."""
    name              = fields.String(required=True, validate=validate.Length(min=2, max=150))
    business_type     = fields.String(load_default=None)
    state             = fields.String(load_default=None)
    gstin             = fields.String(load_default=None)
    pan               = fields.String(load_default=None)
    expected_turnover = fields.Float(load_default=None)
    phone             = fields.String(load_default=None)
    whatsapp_phone    = fields.String(load_default=None)

    @validates("gstin")
    def validate_gstin(self, value):
        if value and not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}", value):
            raise ValidationError("Invalid GSTIN format.")

    @validates("pan")
    def validate_pan(self, value):
        if value and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", value):
            raise ValidationError("Invalid PAN format.")

    @validates("phone")
    def validate_phone(self, value):
        if value:
            digits = re.sub(r"\D", "", value)
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            if len(digits) != 10:
                raise ValidationError("Phone must be a valid 10-digit Indian mobile number.")

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class ClientUpdateSchema(Schema):
    """CA updates a client record — all fields optional."""
    name              = fields.String(validate=validate.Length(min=2, max=150))
    business_type     = fields.String()
    state             = fields.String()
    gstin             = fields.String()
    pan               = fields.String()
    expected_turnover = fields.Float()
    phone             = fields.String()
    whatsapp_phone    = fields.String()
    is_active         = fields.Boolean()

    @validates("gstin")
    def validate_gstin(self, value):
        if value and not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}", value):
            raise ValidationError("Invalid GSTIN format.")

    @validates("pan")
    def validate_pan(self, value):
        if value and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", value):
            raise ValidationError("Invalid PAN format.")

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class InviteAcceptSchema(Schema):
    """Payload when a client taps the invite link and fills in their details."""
    invite_code = fields.String(required=True)
    name        = fields.String(required=True, validate=validate.Length(min=2, max=120))
    phone       = fields.String(required=True)
    pin         = fields.String(required=True)

    @validates("phone")
    def validate_phone(self, value):
        digits = re.sub(r"\D", "", value)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10:
            raise ValidationError("Phone must be a valid 10-digit Indian mobile number.")

    @validates("pin")
    def validate_pin(self, value):
        if not re.fullmatch(r"\d{4,6}", value):
            raise ValidationError("PIN must be 4-6 digits.")

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class InviteVerifyOTPSchema(Schema):
    """Client submits their OTP after invite accept."""
    user_id = fields.Integer(required=True)
    otp     = fields.String(required=True,
                            validate=validate.Regexp(r"^\d{6}$", error="OTP must be 6 digits."))


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class ClientSummarySchema(Schema):
    """Compact view used in the clients list."""
    id               = fields.Integer()
    name             = fields.String()
    business_type    = fields.String()
    state            = fields.String()
    phone            = fields.String()
    invite_status    = fields.String()
    is_active        = fields.Boolean()
    created_at       = fields.DateTime()
    statement_count  = fields.Integer()
    last_activity    = fields.DateTime(allow_none=True)
    compliance_score = fields.Float(allow_none=True)


class ClientDetailSchema(Schema):
    """Full detail view for a single client."""
    id                = fields.Integer()
    org_id            = fields.Integer()
    owner_user_id     = fields.Integer(allow_none=True)
    name              = fields.String()
    business_type     = fields.String()
    state             = fields.String()
    gstin             = fields.String()
    pan               = fields.String()
    expected_turnover = fields.Float(allow_none=True)
    phone             = fields.String()
    whatsapp_phone    = fields.String()
    invite_code       = fields.String()
    invite_status     = fields.String()
    invite_expires_at = fields.DateTime(allow_none=True)
    is_active         = fields.Boolean()
    created_at        = fields.DateTime()
    updated_at        = fields.DateTime()
    owner_name        = fields.String(allow_none=True)
    owner_phone       = fields.String(allow_none=True)


class InviteLandingSchema(Schema):
    """Public invite landing page data (no sensitive info)."""
    invite_code   = fields.String()
    ca_firm_name  = fields.String()
    client_name   = fields.String()
    invite_status = fields.String()
    is_expired    = fields.Boolean()
