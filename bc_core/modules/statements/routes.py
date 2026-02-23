from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from modules.statements.models import BusinessStatement

statements_bp = Blueprint("statements", __name__)

@statements_bp.route("/business/<int:business_id>")
@jwt_required()
def list_statements(business_id):
    stmts = BusinessStatement.query.filter_by(business_id=business_id).order_by(BusinessStatement.created_at.desc()).all()
    return jsonify([
        {
            "id": s.id,
            "type": s.statement_type,
            "amount": s.amount,
            "confidence": s.confidence_level,
            "created_at": s.created_at
        } for s in stmts
    ])
