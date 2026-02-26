import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ------------------------------------------------------------------ #
    # Flask
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.getenv("APP_ENV", "development") == "development"

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///bc_dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Connection pool settings — matters for PostgreSQL in production
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_pre_ping": True,   # validate connection before use
    }

    # ------------------------------------------------------------------ #
    # JWT
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"
    # Enables the token_in_blocklist_loader callback used for logout
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]

    # ------------------------------------------------------------------ #
    # Rate limiting  (flask-limiter)
    # ------------------------------------------------------------------ #
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = "memory://"   # swap to Redis URI in production
    RATELIMIT_HEADERS_ENABLED = True       # expose X-RateLimit-* headers

    # ------------------------------------------------------------------ #
    # Email / SMTP  (used for OTP delivery)
    # ------------------------------------------------------------------ #
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@bharatcompliance.in")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "BharatCompliance")

    # ------------------------------------------------------------------ #
    # OTP settings
    # ------------------------------------------------------------------ #
    OTP_EXPIRY_MINUTES = 10
    OTP_MAX_ATTEMPTS = 5          # lock OTP after this many wrong tries
    OTP_RESEND_COOLDOWN_SECONDS = 60  # min gap between resend requests

    # ------------------------------------------------------------------ #
    # App
    # ------------------------------------------------------------------ #
    APP_ENV = os.getenv("APP_ENV", "development")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
