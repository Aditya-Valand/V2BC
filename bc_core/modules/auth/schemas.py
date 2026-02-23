from marshmallow import Schema, fields

class RegisterSchema(Schema):
    name = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)

class UserResponseSchema(Schema):
    id = fields.Int()
    name = fields.String()
    email = fields.Email()
    role = fields.String()
