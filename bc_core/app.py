import logging

from flask import Flask

from core.config import Config
from core.extensions import db, jwt, limiter, migrate
from core.dependencies import register_error_handlers, register_jwt_callbacks

# ------------------------------------------------------------------ #
# Model imports — required so SQLAlchemy/Alembic sees all table metadata
# ------------------------------------------------------------------ #
from modules.auth.models import JWTBlocklist, OrgMember, User          # noqa: F401
from modules.organizations.models import Organization                   # noqa: F401
from modules.businesses.models import Business                          # noqa: F401
from modules.statements.models import BusinessStatement                 # noqa: F401
from modules.evidence.models import BusinessEvidence                    # noqa: F401
from modules.whatsapp.models import WhatsAppMessage                     # noqa: F401
from modules.compliance.models import (                                 # noqa: F401
    ComplianceSignal, ComplianceProfile, ComplianceAlert
)
from modules.deadlines.models import ComplianceDeadline                  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ---------------------------------------------------------------- #
    # Extensions
    # ---------------------------------------------------------------- #
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # ---------------------------------------------------------------- #
    # JWT callbacks (blocklist, error responses)
    # ---------------------------------------------------------------- #
    register_jwt_callbacks(jwt)

    # ---------------------------------------------------------------- #
    # Flask error handlers
    # ---------------------------------------------------------------- #
    register_error_handlers(app)

    # ---------------------------------------------------------------- #
    # Blueprints
    # ---------------------------------------------------------------- #
    from modules.auth.routes import auth_bp
    from modules.organizations.routes import org_bp
    from modules.businesses.routes import clients_bp, invite_bp
    from modules.transactions.routes import transactions_bp, my_bp
    from modules.statements.routes import statements_bp
    from modules.evidence.routes import evidence_bp
    from modules.whatsapp.routes import whatsapp_bp
    from modules.compliance.routes import compliance_bp
    from modules.dashboard.routes import dashboard_bp
    from modules.reminders.routes import reminders_bp
    from modules.deadlines.routes import deadlines_bp
    from modules.validation.routes import validation_bp

    app.register_blueprint(auth_bp,         url_prefix="/auth")
    app.register_blueprint(org_bp,          url_prefix="/orgs")
    app.register_blueprint(clients_bp,      url_prefix="/clients")
    app.register_blueprint(invite_bp,       url_prefix="/invite")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(my_bp,           url_prefix="/my")
    app.register_blueprint(statements_bp,   url_prefix="/statements")
    app.register_blueprint(evidence_bp,     url_prefix="/evidence")
    app.register_blueprint(whatsapp_bp,     url_prefix="/whatsapp")
    app.register_blueprint(compliance_bp,   url_prefix="/compliance")
    app.register_blueprint(dashboard_bp,    url_prefix="/dashboard")
    app.register_blueprint(reminders_bp,    url_prefix="/reminders")
    app.register_blueprint(deadlines_bp,    url_prefix="/deadlines")
    app.register_blueprint(validation_bp,   url_prefix="/validation")

    # ---------------------------------------------------------------- #
    # APScheduler — daily deadline reminder job (Feature 6)
    # ---------------------------------------------------------------- #
    _init_scheduler(app)

    return app


def _init_scheduler(app):
    """
    Start APScheduler for daily deadline reminders.

    Runs at 9:00 AM IST (03:30 UTC) every day.
    Only starts in non-testing environments and when not in a reloader child.
    """
    import os
    if app.config.get("TESTING") or os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        app.logger.warning(
            "APScheduler not installed — daily deadline reminders disabled. "
            "Install with: pip install APScheduler"
        )
        return

    scheduler = BackgroundScheduler(daemon=True)

    from modules.deadlines.service import run_daily_reminder_job
    from modules.validation.service import run_gap_detection

    scheduler.add_job(
        func=run_daily_reminder_job,
        args=[app],
        trigger=CronTrigger(hour=3, minute=30),   # 03:30 UTC = 09:00 IST
        id="daily_deadline_reminders",
        name="Daily deadline reminder + missed marker",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        func=run_gap_detection,
        args=[app],
        trigger=CronTrigger(hour=4, minute=0),    # 04:00 UTC = 09:30 IST
        id="daily_gap_detection",
        name="Daily gap detection (Feature 7)",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    app.logger.info("APScheduler started -- daily jobs at 09:00/09:30 IST")


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True))
