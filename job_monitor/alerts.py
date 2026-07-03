"""Send alerts for new job postings."""

import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from job_monitor.config import (
    ALERT_EMAIL_TO,
    SLACK_WEBHOOK_URL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from job_monitor.linkedin_client import JobPosting
from job_monitor.local_alerts import send_local_alerts

logger = logging.getLogger(__name__)

PROFILE_LABELS = {
    "remote_india": "Remote Senior Data Engineer (India)",
    "kochi": "Senior Data Engineer / Similar (Kochi)",
    "trivandrum": "Senior Data Engineer / Similar (Trivandrum)",
}


def _format_job_line(job: JobPosting) -> str:
    return (
        f"• *{job.title}* at {job.company}\n"
        f"  Location: {job.location}\n"
        f"  {job.url}"
    )


def _format_message(jobs: List[JobPosting]) -> str:
    by_profile: dict = {}
    for job in jobs:
        by_profile.setdefault(job.profile, []).append(job)

    sections = []
    for profile, profile_jobs in by_profile.items():
        label = PROFILE_LABELS.get(profile, profile)
        lines = [_format_job_line(job) for job in profile_jobs]
        sections.append(f"*{label}* ({len(profile_jobs)} new)\n" + "\n".join(lines))

    header = f"🔔 *{len(jobs)} new LinkedIn job(s) found*\n\n"
    return header + "\n\n".join(sections)


def _format_email_body(jobs: List[JobPosting]) -> str:
    by_profile: dict = {}
    for job in jobs:
        by_profile.setdefault(job.profile, []).append(job)

    sections = []
    for profile, profile_jobs in by_profile.items():
        label = PROFILE_LABELS.get(profile, profile)
        lines = [
            f"- {job.title} at {job.company}\n"
            f"  Location: {job.location}\n"
            f"  {job.url}"
            for job in profile_jobs
        ]
        sections.append(f"{label} ({len(profile_jobs)} new):\n" + "\n".join(lines))

    return f"{len(jobs)} new LinkedIn job(s) found\n\n" + "\n\n".join(sections)


def send_slack_alert(jobs: List[JobPosting]) -> bool:
    if not SLACK_WEBHOOK_URL:
        return False

    payload = json.dumps({"text": _format_message(jobs)}).encode("utf-8")
    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status == 200:
                logger.info("Slack alert sent for %d job(s)", len(jobs))
                return True
    except urllib.error.URLError as exc:
        logger.error("Failed to send Slack alert: %s", exc)
    return False


def send_email_alert(jobs: List[JobPosting]) -> bool:
    if not all([ALERT_EMAIL_TO, SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        return False

    message = MIMEMultipart()
    message["From"] = SMTP_FROM
    message["To"] = ALERT_EMAIL_TO
    message["Subject"] = f"[Job Alert] {len(jobs)} new Senior Data Engineer job(s)"
    message.attach(MIMEText(_format_email_body(jobs), "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [ALERT_EMAIL_TO], message.as_string())
        logger.info("Email alert sent to %s for %d job(s)", ALERT_EMAIL_TO, len(jobs))
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email alert: %s", exc)
    return False


def send_alerts(jobs: List[JobPosting]) -> None:
    """Send alerts via all configured channels; always log to console."""
    if not jobs:
        logger.info("No new jobs to alert on")
        return

    logger.info("New jobs found:\n%s", _format_email_body(jobs))

    local_sent = send_local_alerts(jobs)
    slack_sent = send_slack_alert(jobs)
    email_sent = send_email_alert(jobs)

    if not local_sent and not slack_sent and not email_sent:
        logger.warning(
            "No alert channels delivered. Desktop notifications require notify-send "
            "(Linux) or macOS. Optional: SLACK_WEBHOOK_URL or SMTP_* / ALERT_EMAIL_TO."
        )
