from marshmallow import ValidationError
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({"error": err.messages}), 400
