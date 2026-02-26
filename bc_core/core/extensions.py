from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# Rate limiter — key_func uses the real client IP.
# In production behind a reverse proxy, set APPLICATION_ROOT or use
# get_remote_address with X-Forwarded-For trust configured.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://",   # overridden by app config if RATELIMIT_STORAGE_URI set
)
