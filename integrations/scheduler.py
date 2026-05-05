"""
Scheduler — runs the job search scan at configured times.
"""

import asyncio
import schedule
import time
from datetime import datetime

from config import load_config
from csv_io import load_companies
from integrations.notifier import SLACK_WEBHOOK, notify_match_found, notify_scan_started, notify_scan_done
from logger import start_log, stop_log
from main import run
from utils import format_duration


def run_scan() -> None:
    """Execute one full scan. Config is re-read each time so changes take effect."""
    config    = load_config()
    companies = load_companies(config["companies_file"])

    notifications = config.get("notifications_enabled", True)
    on_match      = notify_match_found if (SLACK_WEBHOOK and notifications) else None

    if notifications:
        notify_scan_started(len(companies))
    print(f"\n🕐  Scheduled scan triggered at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if config.get("logging_enabled", True):
        start_log(trigger="scheduler", config=config)
    try:
        start       = time.time()
        new_matches = asyncio.run(run(
            companies_path=config["companies_file"],
            titles_path=config["titles_file"],
            headless=True,
            concurrency=config["concurrency"],
            output_path=config["output_file"],
            on_match=on_match,
        ))
        duration = format_duration(time.time() - start)
        if notifications:
            notify_scan_done(new_matches, duration)
    except Exception as e:
        print(f"⚠️  Scan failed: {e}")
    finally:
        stop_log()


def run_scheduler(run_now: bool = False) -> None:
    config = load_config()
    times  = config.get("schedule_times", ["08:08", "13:13", "18:18"])

    for t in times:
        schedule.every().day.at(t).do(run_scan)

    next_run = schedule.next_run()
    print(f"🚀  Scheduler started — running every day at: {', '.join(times)}")
    print(f"    Next run : {next_run.strftime('%Y-%m-%d %H:%M') if next_run else 'none'}")
    print("    Press Ctrl+C to stop.\n")

    if run_now:
        run_scan()

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n⛔  Scheduler stopped.")
