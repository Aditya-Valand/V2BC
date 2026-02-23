from flask import Flask
from core.config import Config
from core.extensions import db, migrate, jwt
from core.dependencies import register_error_handlers

# Import all models to register with SQLAlchemy
from modules.auth.models import User, UserOrganizationPermission
from modules.organizations.models import Organization
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.whatsapp.models import WhatsAppMessage
# Phase-3: Compliance models
from modules.compliance.models import ComplianceSignal, ComplianceProfile, ComplianceAlert


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from modules.auth.routes import auth_bp
    from modules.organizations.routes import org_bp
    from modules.businesses.routes import business_bp
    from modules.statements.routes import statements_bp
    from modules.evidence.routes import evidence_bp
    from modules.whatsapp.routes import whatsapp_bp
    from modules.compliance.routes import compliance_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(org_bp, url_prefix="/orgs")
    app.register_blueprint(business_bp, url_prefix="/businesses")
    app.register_blueprint(statements_bp, url_prefix="/statements")
    app.register_blueprint(evidence_bp, url_prefix="/evidence")
    app.register_blueprint(whatsapp_bp, url_prefix="/whatsapp")
    app.register_blueprint(compliance_bp, url_prefix="/compliance")
    register_error_handlers(app)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
