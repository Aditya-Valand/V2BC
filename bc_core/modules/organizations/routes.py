from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.organizations.schemas import OrganizationCreateSchema, OrganizationResponseSchema
from modules.organizations.service import create_org, get_orgs

org_bp = Blueprint("orgs", __name__)

@org_bp.route("", methods=["POST"])
@jwt_required()
def create():
    data = OrganizationCreateSchema().load(request.json)
    org = create_org(data["name"], get_jwt_identity())
    return jsonify(OrganizationResponseSchema().dump(org))

@org_bp.route("", methods=["GET"])
@jwt_required()
def list_orgs():
    orgs = get_orgs(get_jwt_identity())
    return jsonify(OrganizationResponseSchema(many=True).dump(orgs))
