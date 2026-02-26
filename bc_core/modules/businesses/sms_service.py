"""
SMS service stub — OTP delivery for client phone verification.

In production, replace _send_sms_production() with your SMS gateway
(MSG91, Twilio, AWS SNS, etc.).  The interface is intentionally
identical to email_service.py so both can be swapped without changing
callers.
"""
import logging

from flask import current_app

logger = logging.getLogger(__name__)


def send_otp_sms(to_phone: str, otp: str, name: str = "") -> bool:
    """
    Send an OTP to `to_phone` via SMS.

    Returns True if delivered (or dev mode), False on failure.
    Never raises — errors are logged and the caller decides.
    """
    env = current_app.config.get("APP_ENV", "development")

    if env != "production":
        # ── Development mode: log to console, skip real SMS ────────── #
        logger.info(
            "\n============================================================\n"
            "  [DEV] SMS OTP — would have been sent to: %s\n"
            "  OTP CODE: %s\n"
            "============================================================",
            to_phone, otp,
        )
        return True

    # ── Production mode: swap this block for your SMS provider ─────── #
    try:
        _send_sms_production(to_phone, otp, name)
        return True
    except Exception as exc:
        logger.error("SMS delivery failed to %s: %s", to_phone, exc)
        return False


def _send_sms_production(to_phone: str, otp: str, name: str) -> None:
    """
    Real SMS delivery.  Implement with your provider, e.g.:

        import requests
        requests.post(
            "https://api.msg91.com/api/v5/otp",
            json={"template_id": "...", "mobile": to_phone, "otp": otp},
            headers={"authkey": current_app.config["MSG91_AUTH_KEY"]},
        ).raise_for_status()
    """
    raise NotImplementedError("Configure an SMS provider for production.")
