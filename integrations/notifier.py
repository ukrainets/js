"""
Slack notifications via Incoming Webhooks.
Requires SLACK_WEBHOOK in .env (or environment). Gracefully skips if not set.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")


def _send(message: str) -> bool:
    """POST a plain-text message to Slack. Returns True on success."""
    if not SLACK_WEBHOOK:
        return False
    try:
        response = requests.post(
            SLACK_WEBHOOK,
            json={"text": message},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"⚠️  Slack notification failed: {e}")
        return False


def notify_scan_started(company_count: int) -> None:
    _send(f"🔎 Scheduled scan started for {company_count} companies.")


def notify_match_found(company_name: str, title: str, scraped_text: str, job_url: str) -> None:
    _send(f"🥳 New match found for [{title}]:\n{company_name} - {scraped_text}\n{job_url}")


def notify_scan_done(new_matches: int, duration: str) -> None:
    """Send scan completion summary — only called from the scheduler."""
    if new_matches:
        _send(f"✅ Scan done in {duration}. {new_matches} new match(es) found.")
    else:
        _send(f"ℹ️ Scan done in {duration}. No new matches found.")
