from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.organizations.schemas import OrganizationCreateSchema, OrganizationResponseSchema
from modules.organizations.service import create_org, get_orgs

org_bp = Blueprint("orgs", __name__)


def _ok(data, status=200):
    return jsonify({"success": True,  "data": data,  "error": None}), status

def _err(msg, status=400):
    return jsonify({"success": False, "data": None, "error": msg}), status


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


@org_bp.route("/<int:org_id>/public", methods=["GET"])
def public_profile(org_id: int):
    """
    Public CA firm profile — no auth required.
    Returns enough information for a marketing/trust page.
    """
    from modules.organizations.models import Organization
    from modules.auth.models import User

    org = Organization.query.get(org_id)
    if not org:
        return _err("Firm not found.", 404)

    owner = User.query.get(org.owner_id) if org.owner_id else None

    return _ok({
        "id":             org.id,
        "name":           org.name,
        "city":           org.city,
        "state":          org.state,
        "license_number": org.license_number,
        "plan":           org.plan,
        "client_count":   org.client_count,
        "owner_name":     owner.name if owner else None,
        "created_at":     org.created_at.isoformat() if org.created_at else None,
    })
