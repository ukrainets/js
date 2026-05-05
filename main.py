"""
Job Search Automation — Async Edition
Scans company career pages concurrently for matching QA/SQA job titles.

Usage:
    python main.py
    python main.py --concurrency 10
    python main.py --companies data/companies.csv --titles data/sqa_titles.csv
    python main.py --no-headless
"""

import argparse
import asyncio
from datetime import datetime

import httpx
from playwright.async_api import async_playwright

from config import load_config, API_CONCURRENCY
from logger import start_log, stop_log
from csv_io import load_companies, load_titles, load_known_urls
from integrations.notifier import SLACK_WEBHOOK, notify_match_found
from utils import format_duration
from crawlers.scanner import scan_company
from crawlers.api_greenhouse import scan_greenhouse


# ── Main run loop ─────────────────────────────────────────────────────────────

async def run(
    companies_path: str,
    titles_path: str,
    headless: bool,
    concurrency: int,
    output_path: str,
) -> int:
    companies  = load_companies(companies_path)
    titles     = load_titles(titles_path)
    start_time = datetime.now()

    api_companies       = [c for c in companies if c["api_url"]]
    playwright_companies = [c for c in companies if not c["api_url"]]

    print(f"Start time        : {start_time.strftime('%H:%M')}")
    print(f"Companies to scan : {len(companies)}  (no_click=TRUE, sorted by rating ↓)")
    print(f"  → API           : {len(api_companies)}")
    print(f"  → Playwright    : {len(playwright_companies)}")
    print(f"Titles loaded     : {len(titles)}")
    print(f"Concurrency       : {concurrency} tab(s) / {API_CONCURRENCY} API")
    print(f"Headless          : {headless}")
    print("─" * 60)

    pw_semaphore  = asyncio.Semaphore(concurrency)
    api_semaphore = asyncio.Semaphore(API_CONCURRENCY)
    write_lock    = asyncio.Lock()
    known_urls    = load_known_urls(output_path)
    on_match      = notify_match_found if SLACK_WEBHOOK else None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        async with httpx.AsyncClient() as http_client:
            api_tasks = [
                scan_greenhouse(http_client, api_semaphore, c["company_name"], c["api_url"], titles, output_path, write_lock, known_urls, on_match)
                for c in api_companies
            ]
            pw_tasks = [
                scan_company(pw_semaphore, context, c["company_name"], c["open_positions_url"], titles, output_path, write_lock, known_urls, on_match)
                for c in playwright_companies
            ]
            results = await asyncio.gather(*api_tasks, *pw_tasks)

        await browser.close()

    new_matches   = [m for result in results for m in result]
    total_matches = len(new_matches)

    end_time = datetime.now()
    elapsed  = (end_time - start_time).total_seconds()

    print("\n" + "─" * 60)
    print(f"🏁  Done in {format_duration(elapsed)}")
    print(f"   - end time  : {end_time.strftime('%H:%M')}")
    print(f"   - searched  : {len(companies)} companies")
    print(f"   - found     : {total_matches} new match(es)")
    if new_matches:
        print(f"📄  New results saved to: {output_path}")

    return total_matches


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    config = load_config()

    parser = argparse.ArgumentParser(
        description="Scan company career pages for matching job titles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--companies", default=config["companies_file"],
        help="Path to companies CSV file"
    )
    parser.add_argument(
        "--titles", default=config["titles_file"],
        help="Path to titles CSV file"
    )
    parser.add_argument(
        "--concurrency", type=int, default=config["concurrency"],
        help="Number of parallel browser tabs"
    )
    parser.add_argument(
        "--output", default=config["output_file"],
        help="Path to output CSV file for matched positions"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run with a visible browser window (useful for debugging)"
    )
    parser.add_argument(
        "--no-log", action="store_true",
        help="Disable logging to file for this run"
    )
    args = parser.parse_args()

    if not args.no_log and config.get("logging_enabled", True):
        start_log(trigger="manual", config=config)
    try:
        asyncio.run(run(
            companies_path=args.companies,
            titles_path=args.titles,
            headless=not args.no_headless,
            concurrency=args.concurrency,
            output_path=args.output,
        ))
    finally:
        stop_log()


if __name__ == "__main__":
    main()
