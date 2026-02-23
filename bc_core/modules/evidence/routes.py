from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from modules.evidence.service import save_evidence
from modules.ocr.service import run_ocr
evidence_bp = Blueprint("evidence", __name__)

@evidence_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload():
    file = request.files.get("file")
    business_id = request.form.get("business_id")
    statement_id = request.form.get("statement_id")

    ev = save_evidence(file, business_id, statement_id, source="web")

    return jsonify({
        "id": ev.id,
        "status": ev.status,
        "quality_score": ev.quality_score
    })
