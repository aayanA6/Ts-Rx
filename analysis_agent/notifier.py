from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from analysis_agent.config import get_settings

if TYPE_CHECKING:
    from analysis_agent.models import NotificationSettings

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_incident_notification(
    notif: NotificationSettings,
    service_name: str,
    incident_id: str,
    confidence: float,
    summary_text: str,
    job_id: str,
) -> None:
    """Fire all enabled notification channels. Errors are logged, never raised."""
    short_summary = _truncate(summary_text, 400)
    confidence_pct = int(confidence * 100)
    dashboard_url = f"{settings.app_url.rstrip('/')}/#incident-{job_id}"

    if notif.discord_enabled and notif.discord_webhook_url:
        await _send_discord(notif.discord_webhook_url, service_name, incident_id, confidence_pct, short_summary, dashboard_url)

    if notif.slack_enabled and notif.slack_webhook_url:
        await _send_slack(notif.slack_webhook_url, service_name, incident_id, confidence_pct, short_summary, dashboard_url)

    if notif.email_enabled:
        await _send_email(notif.user.email, service_name, incident_id, confidence_pct, short_summary, dashboard_url)


async def _send_discord(webhook_url: str, service: str, incident_id: str, confidence_pct: int, summary: str, url: str) -> None:
    color = 0xEF4444 if confidence_pct >= 70 else 0xF59E0B
    payload = {
        "embeds": [{
            "title": f"🚨 Incident: {service}",
            "description": summary,
            "color": color,
            "fields": [
                {"name": "Incident ID", "value": incident_id, "inline": True},
                {"name": "Confidence", "value": f"{confidence_pct}%", "inline": True},
            ],
            "url": url,
            "footer": {"text": "TS-RX • Self-healing network dashboard"},
        }]
    }
    await _post_webhook("discord", webhook_url, payload)


async def _send_slack(webhook_url: str, service: str, incident_id: str, confidence_pct: int, summary: str, url: str) -> None:
    payload = {
        "attachments": [{
            "color": "#EF4444",
            "title": f"🚨 Incident: {service}",
            "title_link": url,
            "text": summary,
            "fields": [
                {"title": "Incident ID", "value": incident_id, "short": True},
                {"title": "Confidence", "value": f"{confidence_pct}%", "short": True},
            ],
            "footer": "TS-RX",
        }]
    }
    await _post_webhook("slack", webhook_url, payload)


async def _post_webhook(name: str, url: str, payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to send %s notification: %s", name, exc)


async def _send_email(to: str, service: str, incident_id: str, confidence_pct: int, summary: str, url: str) -> None:
    if not settings.smtp_host or not settings.smtp_user:
        return
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        body = (
            f"Incident detected on {service}\n\n"
            f"ID: {incident_id}\n"
            f"Confidence: {confidence_pct}%\n\n"
            f"{summary}\n\n"
            f"View in dashboard: {url}"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[TS-RX] Incident on {service}"
        msg["From"] = settings.smtp_from
        msg["To"] = to

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
    except Exception as exc:
        logger.warning("Failed to send email notification: %s", exc)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."
