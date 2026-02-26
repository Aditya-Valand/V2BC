from marshmallow import Schema, fields, validate, validates, ValidationError, pre_load
import re


class TransactionCreateSchema(Schema):
    type              = fields.String(required=True, validate=validate.OneOf(["sale", "expense"]))
    amount            = fields.Float(required=True)
    category          = fields.String(load_default=None)   # expense category
    transaction_date  = fields.Date(load_default=None)     # default = today
    description       = fields.String(load_default=None)

    @validates("amount")
    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError("Amount must be greater than 0.")
        if value > 100_000_000:
            raise ValidationError("Amount seems unrealistically large.")

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class TransactionConfirmSchema(Schema):
    """For resolving OCR amount conflicts."""
    amount = fields.Float(required=True)

    @validates("amount")
    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError("Amount must be greater than 0.")


class TransactionSchema(Schema):
    id               = fields.Integer()
    business_id      = fields.Integer()
    type             = fields.String(attribute="statement_type")
    amount           = fields.Float()
    category         = fields.String(attribute="raw_text")
    description      = fields.String()
    transaction_date = fields.DateTime()
    source           = fields.String()
    confidence_level = fields.String()
    verified         = fields.Boolean()
    created_at       = fields.DateTime()
    updated_at       = fields.DateTime()
    # Evidence fields (populated when evidence exists)
    evidence_id      = fields.Integer(allow_none=True)
    evidence_status  = fields.String(allow_none=True)


class MonthlySummarySchema(Schema):
    month              = fields.String()
    total_sales        = fields.Float()
    total_expenses     = fields.Float()
    net_income         = fields.Float()
    transaction_count  = fields.Integer()
    daily_breakdown    = fields.List(fields.Dict())
    expense_by_category = fields.Dict()
