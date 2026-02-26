import logging
from functools import wraps

from flask import jsonify, g
from flask_jwt_extended import get_jwt_identity, get_jwt
from marshmallow import ValidationError

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# JWT blocklist callback
# ------------------------------------------------------------------ #

def register_jwt_callbacks(jwt):
    """Register all JWT event callbacks onto the JWTManager instance."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Called on every @jwt_required route. Returns True to block the token."""
        from modules.auth.models import JWTBlocklist
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        return JWTBlocklist.query.filter_by(jti=jti).first() is not None

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": "Token has expired.",
            "code": "TOKEN_EXPIRED"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "success": False,
            "error": "Invalid token.",
            "code": "TOKEN_INVALID"
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "success": False,
            "error": "Authorization token is required.",
            "code": "TOKEN_MISSING"
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": "Token has been revoked.",
            "code": "TOKEN_REVOKED"
        }), 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": "Fresh token required.",
            "code": "TOKEN_NOT_FRESH"
        }), 401

    # Note: wrong_token_type_loader was removed in Flask-JWT-Extended 4.x.
    # Wrong token type (e.g. using a refresh token where an access token is
    # expected) is now handled by the invalid_token_loader above.


# ------------------------------------------------------------------ #
# Access control decorators
# ------------------------------------------------------------------ #

def require_org_access(f):
    """
    Route decorator: verifies the JWT user is a member of the org_id
    supplied in the route kwargs.  Attaches g.current_member (OrgMember)
    so downstream code can check g.current_member.role.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from modules.auth.models import OrgMember
        user_id = int(get_jwt_identity())
        org_id = kwargs.get("org_id")
        if org_id is None:
            return jsonify({"success": False, "error": "org_id required."}), 400

        member = OrgMember.query.filter_by(
            user_id=user_id, org_id=org_id
        ).first()
        if not member:
            return jsonify({"success": False, "error": "Access denied."}), 403

        g.current_member = member
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """
    Route decorator: ensures the current org member has one of the
    specified roles.  Must be used AFTER @require_org_access.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            member = getattr(g, "current_member", None)
            if member is None or member.role not in roles:
                return jsonify({
                    "success": False,
                    "error": f"Requires one of these roles: {', '.join(roles)}."
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ------------------------------------------------------------------ #
# Flask error handlers
# ------------------------------------------------------------------ #

def register_error_handlers(app):
    """Register all application-level error handlers."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({"success": False, "error": err.messages}), 400

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify({"success": False, "error": "Bad request."}), 400

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"success": False, "error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        return jsonify({"success": False, "error": "Method not allowed."}), 405

    @app.errorhandler(429)
    def ratelimit_handler(err):
        return jsonify({
            "success": False,
            "error": "Too many requests. Please slow down.",
            "code": "RATE_LIMITED"
        }), 429

    @app.errorhandler(500)
    def internal_error(err):
        logger.exception("Unhandled 500 error: %s", err)
        return jsonify({"success": False, "error": "Internal server error."}), 500
