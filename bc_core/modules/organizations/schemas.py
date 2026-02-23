from marshmallow import Schema, fields

class OrganizationCreateSchema(Schema):
    name = fields.String(required=True)

class OrganizationResponseSchema(Schema):
    id = fields.Int()
    name = fields.String()
