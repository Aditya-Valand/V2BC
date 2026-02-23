from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from modules.businesses.schemas import BusinessCreateSchema, BusinessResponseSchema
from modules.businesses.service import create_business, list_businesses

business_bp = Blueprint("businesses", __name__)

@business_bp.route("", methods=["POST"])
@jwt_required()
def create():
    data = BusinessCreateSchema().load(request.json)
    b = create_business(data)
    return jsonify(BusinessResponseSchema().dump(b))

@business_bp.route("/<int:org_id>")
@jwt_required()
def list_all(org_id):
    bs = list_businesses(org_id)
    return jsonify(BusinessResponseSchema(many=True).dump(bs))
