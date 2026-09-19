"""Thin synchronous wrapper for sending Telegram messages from regular Django
views/signals, plus a demo-friendly fallback that just logs to NotificationLog
when no bot token is configured (or the call fails) so the platform is fully
demoable without a live Telegram bot."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(chat_id, text, reply_markup=None):
    """Best-effort send. Returns True on success, False otherwise (never raises)."""
    if not chat_id or not settings.TELEGRAM_BOT_TOKEN:
        return False
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(
            TELEGRAM_API_URL.format(token=settings.TELEGRAM_BOT_TOKEN),
            json=payload,
            timeout=5,
        )
        return response.ok
    except requests.RequestException:
        logger.warning("Failed to send Telegram message to %s", chat_id, exc_info=True)
        return False


def notify(recipient, message, related_attendance=None, related_subject_attendance=None):
    """Notify a recipient (a User or Parent instance) via Telegram, and always
    record the attempt in NotificationLog so the demo shows the fan-out even
    when TELEGRAM_BOT_TOKEN isn't set. related_attendance/related_subject_attendance
    are mutually exclusive — pass whichever check-in triggered this notification,
    or neither."""
    from attendance.models import NotificationLog

    chat_id = getattr(recipient, "telegram_chat_id", None)
    sent = send_telegram_message(chat_id, message)
    label = str(recipient)
    if not sent:
        label += " (not linked to Telegram)" if not chat_id else " (send failed)"
    NotificationLog.objects.create(
        recipient_label=label,
        message=message,
        related_attendance=related_attendance,
        related_subject_attendance=related_subject_attendance,
    )
    return sent
