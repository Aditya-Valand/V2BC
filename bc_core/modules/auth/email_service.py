"""
Email delivery service for BharatCompliance.

Behaviour
---------
- Production (APP_ENV=production): sends real emails via SMTP.
- Development (default): prints OTP to stdout — no SMTP required.

The caller should never crash if email fails; all exceptions are caught
and logged.  The OTP is still stored in the DB regardless of delivery.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _build_otp_email(to_email: str, to_name: str, otp: str, firm_name: str) -> MIMEMultipart:
    """Build a plain-text + HTML multipart OTP email."""
    cfg = current_app.config
    from_addr = f"{cfg['SMTP_FROM_NAME']} <{cfg['SMTP_FROM']}>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your BharatCompliance verification code"
    msg["From"] = from_addr
    msg["To"] = to_email

    plain = (
        f"Hello {to_name},\n\n"
        f"Your BharatCompliance verification code is: {otp}\n\n"
        f"This code expires in 10 minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"If you did not register for BharatCompliance, please ignore this email.\n\n"
        f"— BharatCompliance Team"
    )

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:480px;margin:auto">
      <h2 style="color:#1a56db">BharatCompliance</h2>
      <p>Hello <strong>{to_name}</strong>,</p>
      <p>Use the code below to verify your account for <strong>{firm_name}</strong>:</p>
      <div style="background:#f4f7ff;border-radius:8px;padding:24px;text-align:center;margin:24px 0">
        <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a56db">{otp}</span>
      </div>
      <p style="color:#666;font-size:13px">This code expires in <strong>10 minutes</strong>. Do not share it.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#999;font-size:11px">If you did not create a BharatCompliance account, ignore this email.</p>
    </body></html>
    """

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _send_via_smtp(to_email: str, msg: MIMEMultipart) -> None:
    """Send a pre-built email message via SMTP with STARTTLS."""
    cfg = current_app.config
    context = ssl.create_default_context()

    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.sendmail(cfg["SMTP_FROM"], to_email, msg.as_string())


def _log_to_console(to_email: str, otp: str) -> None:
    """Development fallback — prints OTP so the dev can test without SMTP."""
    border = "=" * 60
    print(f"\n{border}")
    print(f"  [DEV] OTP EMAIL — would have been sent to: {to_email}")
    print(f"  OTP CODE: {otp}")
    print(f"{border}\n")
    logger.info("[DEV] OTP for %s: %s", to_email, otp)


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def send_otp_email(to_email: str, to_name: str, otp: str, firm_name: str = "") -> bool:
    """
    Send an OTP verification email.

    Returns True on success, False on failure.
    Never raises — failures are logged.
    """
    cfg = current_app.config
    is_production = cfg.get("APP_ENV", "development") == "production"

    if not is_production or not cfg.get("SMTP_USER"):
        # Development mode or SMTP not configured
        _log_to_console(to_email, otp)
        return True

    try:
        msg = _build_otp_email(to_email, to_name, otp, firm_name)
        _send_via_smtp(to_email, msg)
        logger.info("OTP email sent to %s", to_email)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check SMTP_USER / SMTP_PASSWORD.")
    except smtplib.SMTPConnectError:
        logger.error("Could not connect to SMTP server %s:%s", cfg["SMTP_HOST"], cfg["SMTP_PORT"])
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_email, exc)
    except Exception as exc:
        logger.exception("Unexpected error sending OTP email to %s: %s", to_email, exc)

    return False
