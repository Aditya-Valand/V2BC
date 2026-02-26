"""
Reminders service — Feature 5.

Push notifications via Firebase Cloud Messaging (FCM).

Dev mode  — no FIREBASE_SERVER_KEY set → logs and returns "dev_skip" success
Prod mode — sends FCM push to client's registered device token

FCM setup:
  1. Create a Firebase project (console.firebase.google.com)
  2. Project Settings → Cloud Messaging → Server Key
  3. Add to .env: FIREBASE_SERVER_KEY=<key>
  4. Client PWA registers device and calls PUT /auth/fcm-token to store it

HTTP Legacy FCM API used here (v1 API requires service account, overkill for MVP).
Replace with FCM v1 API (google-auth + firebase-admin) when scaling to 100+ CAs.
"""
import logging
import os

import requests as _requests

from core.extensions import db
from modules.auth.models import User
from modules.businesses.models import Business

logger = logging.getLogger(__name__)

FCM_URL    = "https://fcm.googleapis.com/fcm/send"
FCM_TITLES = {
    "deadline":  "Compliance Reminder",
    "general":   "BharatCompliance",
    "missing":   "Data Entry Reminder",
    "urgent":    "Urgent: Action Required",
}


def _send_fcm_push(fcm_token: str, title: str, body: str,
                   notification_type: str) -> tuple[bool, str]:
    """
    Send a single FCM push.

    Returns (success: bool, reason: str).
    In dev (no key) returns (True, 'dev_skip').
    """
    server_key = os.getenv("FIREBASE_SERVER_KEY")

    if not server_key:
        logger.info(
            "[DEV] FCM skip — would send to token=%.20s... type=%s body=%.60s",
            fcm_token, notification_type, body
        )
        return True, "dev_skip"

    try:
        resp = _requests.post(
            FCM_URL,
            headers={
                "Authorization": f"key={server_key}",
                "Content-Type":  "application/json",
            },
            json={
                "to": fcm_token,
                "notification": {
                    "title": title,
                    "body":  body,
                    "sound": "default",
                },
                "data": {
                    "type":    notification_type,
                    "message": body,
                },
                "priority": "high",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("success") == 1:
            return True, "delivered"
        # FCM returns failure details in results array
        error = ""
        if data.get("results"):
            error = data["results"][0].get("error", "unknown")
        return False, error or "fcm_failed"

    except _requests.Timeout:
        logger.warning("FCM push timed out for token %.20s...", fcm_token)
        return False, "timeout"
    except Exception as exc:
        logger.warning("FCM push error: %s", exc)
        return False, str(exc)[:80]


def send_reminders(
    org_id: int,
    client_ids,          # list[int] or the string "all"
    message: str,
    reminder_type: str = "general",
) -> dict:
    """
    Send push notifications to clients.

    Args:
        org_id        — must match client's org (auth guard)
        client_ids    — list of business IDs, or "all" for all active clients
        message       — notification body
        reminder_type — one of: deadline, general, missing, urgent

    Returns:
        {sent, failed, skipped, total, details: [{client_id, client_name, status, reason}]}
    """
    if not message or not message.strip():
        raise ValueError("Message cannot be empty.")

    if reminder_type not in FCM_TITLES:
        reminder_type = "general"
    title = FCM_TITLES[reminder_type]

    # Fetch target businesses
    if client_ids == "all":
        businesses = (
            Business.query
            .filter_by(org_id=org_id, invite_status="active", is_active=True)
            .all()
        )
    else:
        if not isinstance(client_ids, list) or len(client_ids) == 0:
            raise ValueError("client_ids must be a non-empty list or 'all'.")
        if len(client_ids) > 500:
            raise ValueError("Cannot send to more than 500 clients at once.")
        businesses = (
            Business.query
            .filter(
                Business.id.in_(client_ids),
                Business.org_id == org_id,
            )
            .all()
        )
        # Validate all IDs belong to this org
        found_ids = {b.id for b in businesses}
        bad_ids   = [cid for cid in client_ids if cid not in found_ids]
        if bad_ids:
            raise ValueError(f"Client IDs not found in your org: {bad_ids[:5]}")

    results = []

    for biz in businesses:
        base = {"client_id": biz.id, "client_name": biz.name}

        if not biz.owner_user_id:
            results.append({**base, "status": "skipped",
                             "reason": "No user account linked (invite not accepted)"})
            continue

        user = User.query.get(biz.owner_user_id)
        if not user:
            results.append({**base, "status": "failed", "reason": "User record not found"})
            continue

        if not user.fcm_token:
            results.append({**base, "status": "no_token",
                             "reason": "Device not registered for notifications"})
            continue

        ok, reason = _send_fcm_push(user.fcm_token, title, message, reminder_type)
        results.append({
            **base,
            "status": "delivered" if ok else "failed",
            "reason": reason,
        })

    sent    = sum(1 for r in results if r["status"] in ("delivered", "dev_skip"))
    failed  = sum(1 for r in results if r["status"] == "failed")
    skipped = len(results) - sent - failed

    return {
        "sent":    sent,
        "failed":  failed,
        "skipped": skipped,
        "total":   len(results),
        "details": results,
    }
