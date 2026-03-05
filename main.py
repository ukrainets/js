"""
Job Search Automation
Scans company career pages for matching QA/SQA job titles.
Matching is case-insensitive exact match against page link text.

Usage:
    python main.py
    python main.py --companies input_data/companies.csv --titles input_data/sqa_titles.csv
    python main.py --no-headless
"""

import argparse
import csv
import random
import time
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ── Constants ────────────────────────────────────────────────────────────────
PAGE_TIMEOUT    = 30_000      # ms — max wait for page load
MIN_DELAY       = 1.0         # seconds — min pause between requests
MAX_DELAY       = 3.0         # seconds — max pause between requests

DEFAULT_COMPANIES = "input_data/companies.csv"
DEFAULT_TITLES    = "input_data/sqa_titles.csv"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_companies(path: str) -> list[tuple[str, str]]:
    """
    Read companies CSV and return a deduplicated list of (company_name, open_positions_url).
    Skips rows with missing name or URL.
    """
    companies, seen = [], set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["company_name"].strip()
            url  = row["open_positions_url"].strip()
            if name and url and url not in seen:
                seen.add(url)
                companies.append((name, url))
    return companies


def load_titles(path: str) -> list[str]:
    """
    Read titles CSV and return a deduplicated list of job title strings.
    Deduplication is case-insensitive.
    """
    titles, seen = [], set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row["title"].strip()
            if title and title.lower() not in seen:
                seen.add(title.lower())
                titles.append(title)
    return titles


# ── Matching ─────────────────────────────────────────────────────────────────

def get_job_links(page, base_url: str) -> list[tuple[str, str]]:
    """
    Extract all anchor elements from the page.
    Returns a list of (link_text_line, absolute_url) pairs.

    Link text is split line by line — some ATS platforms put the job title
    on the first line followed by location/type on subsequent lines.
    Relative hrefs are resolved to absolute URLs using base_url.
    """
    result = []
    for anchor in page.query_selector_all("a[href]"):
        href      = anchor.get_attribute("href") or ""
        link_text = anchor.inner_text() or ""
        if not href or not link_text.strip():
            continue
        absolute_url = urljoin(base_url, href)
        for line in link_text.splitlines():
            line = line.strip()
            if line:
                result.append((line, absolute_url))
    return result


def find_matches(links: list[tuple[str, str]], titles: list[str]) -> list[tuple[str, str]]:
    """
    Case-insensitive exact match of each title against anchor link text lines.

    Matching against individual link text (not full page text blob) ensures
    "Automation Engineer" won't match a link titled "Cloud Test Automation Engineer".

    Returns a deduplicated list of (matched_title, job_url).
    """
    titles_map = {t.lower(): t for t in titles}
    seen, matches = set(), []
    for line, href in links:
        key = line.lower()
        if key in titles_map and key not in seen:
            seen.add(key)
            matches.append((titles_map[key], href))
    return matches


# ── Browser / scraping ───────────────────────────────────────────────────────


# ── Main run loop ─────────────────────────────────────────────────────────────

def run(companies_path: str, titles_path: str, headless: bool) -> None:
    companies = load_companies(companies_path)
    titles    = load_titles(titles_path)

    print(f"Companies loaded : {len(companies)}")
    print(f"Titles loaded    : {len(titles)}")
    print(f"Headless         : {headless}")
    print("─" * 60)

    total_matches = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            # Realistic user-agent reduces bot-detection triggers
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for name, url in companies:
            print(f"\n🔎  Scanning : {name} - {url}")
            try:
                # networkidle waits until no network requests for 500ms —
                # important for JS-heavy ATS platforms (Greenhouse, Ashby, etc.)
                page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
                links   = get_job_links(page, url)
                matches = find_matches(links, titles)

                if matches:
                    for title, job_url in matches:
                        print(f"✅  Match for: [{title}] {job_url}")
                        total_matches += 1
                else:
                    print(f"❌  No matches found")

            except PlaywrightTimeoutError:
                print(f"⚠️   Timeout — page took too long to load, skipping")
            except Exception as e:
                print(f"⚠️   Error — {e}")

            # Polite delay — reduces chance of rate-limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        browser.close()

    print("\n" + "─" * 60)
    print(f"🏁  Done — searched {len(companies)} companies, found {total_matches} matching position(s)")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scan company career pages for matching job titles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--companies", default=DEFAULT_COMPANIES,
        help="Path to companies CSV file"
    )
    parser.add_argument(
        "--titles", default=DEFAULT_TITLES,
        help="Path to titles CSV file"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run with a visible browser window (useful for debugging)"
    )
    args = parser.parse_args()

    run(
        companies_path=args.companies,
        titles_path=args.titles,
        headless=not args.no_headless,
    )


if __name__ == "__main__":
    main()
