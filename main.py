"""
Job Search Automation
Scans company career pages for matching QA/SQA job titles using fuzzy matching.

Usage:
    python main.py
    python main.py --threshold 85
    python main.py --companies input_data/companies.csv --titles input_data/sqa_titles.csv
    python main.py --no-headless
"""

import argparse
import csv
import random
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rapidfuzz import fuzz

# ── Constants ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = 80          # default fuzzy match score (0–100)
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

def find_matches(page_text: str, titles: list[str], threshold: int) -> list[tuple[str, int]]:
    """
    Fuzzy-match each title against individual lines of the page text.
    Uses partial_ratio so short titles match within longer strings
    (e.g. "QA Engineer" matches "Senior QA Engineer II").

    Returns a list of (title, score) for every title that matched,
    one entry per title regardless of how many lines matched.
    """
    matches = []
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for title in titles:
        best_score = 0
        for line in lines:
            score = fuzz.partial_ratio(title.lower(), line.lower())
            if score > best_score:
                best_score = score
            if best_score == 100:   # perfect match, no need to keep scanning
                break
        if best_score >= threshold:
            matches.append((title, best_score))
    return matches


# ── Browser / scraping ───────────────────────────────────────────────────────

def get_page_text(page) -> str:
    """Extract all visible text from the page body."""
    return page.inner_text("body")


# ── Main run loop ─────────────────────────────────────────────────────────────

def run(companies_path: str, titles_path: str, threshold: int, headless: bool) -> None:
    companies = load_companies(companies_path)
    titles    = load_titles(titles_path)

    print(f"Companies loaded : {len(companies)}")
    print(f"Titles loaded    : {len(titles)}")
    print(f"Match threshold  : {threshold}%")
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
            print(f"\nScanning : {name}")
            print(f"URL      : {url}")
            try:
                # networkidle waits until no network requests for 500ms —
                # important for JS-heavy ATS platforms (Greenhouse, Ashby, etc.)
                page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
                text    = get_page_text(page)
                matches = find_matches(text, titles, threshold)

                if matches:
                    for title, score in matches:
                        print(f"  [MATCH] {name} | {url} | {title} (score: {score}%)")
                        total_matches += 1
                else:
                    print(f"  [NO MATCH]")

            except PlaywrightTimeoutError:
                print(f"  [TIMEOUT] Page took too long to load — skipping")
            except Exception as e:
                print(f"  [ERROR] {e}")

            # Polite delay — reduces chance of rate-limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        browser.close()

    print("\n" + "─" * 60)
    print(f"Searched : {len(companies)} companies")
    print(f"Matches  : {total_matches}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scan company career pages for matching job titles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--threshold", type=int, default=MATCH_THRESHOLD,
        help="Fuzzy match score threshold (0–100)"
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
        threshold=args.threshold,
        headless=not args.no_headless,
    )


if __name__ == "__main__":
    main()
