from marshmallow import Schema, fields

class BusinessCreateSchema(Schema):
    org_id = fields.Int(required=True)
    name = fields.String(required=True)
    business_type = fields.String()
    state = fields.String()
    gstin = fields.String()
    pan = fields.String()
    expected_turnover = fields.Float()

class BusinessResponseSchema(Schema):
    id = fields.Int()
    name = fields.String()
    business_type = fields.String()
    state = fields.String()
