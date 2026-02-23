from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from modules.auth.service import create_user, authenticate
from modules.auth.schemas import RegisterSchema, LoginSchema, UserResponseSchema
from modules.auth.models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = RegisterSchema().load(request.json)
    user = create_user(data["name"], data["email"], data["password"])
    return jsonify(UserResponseSchema().dump(user))

@auth_bp.route("/login", methods=["POST"])
def login():
    data = LoginSchema().load(request.json)
    user = authenticate(data["email"], data["password"])
    if not user:
        return jsonify({"msg": "invalid creds"}), 401
    token = create_access_token(identity=user.id)
    return jsonify({"access_token": token})

@auth_bp.route("/me")
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    return jsonify(UserResponseSchema().dump(user))
