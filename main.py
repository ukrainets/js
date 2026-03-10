"""
Job Search Automation — Async Edition
Scans company career pages concurrently for matching QA/SQA job titles.

Usage:
    python main.py
    python main.py --concurrency 10
    python main.py --companies input_data/companies.csv --titles input_data/sqa_titles.csv
    python main.py --no-headless
"""

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE  = "config.json"
PAGE_TIMEOUT = 30_000       # ms — max wait for a page to load

CONFIG_DEFAULTS = {
    "concurrency":    5,
    "companies_file": "input_data/companies.csv",
    "titles_file":    "input_data/sqa_titles.csv",
}


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """
    Load config.json and merge with defaults.
    Any key missing from the file falls back to CONFIG_DEFAULTS.
    """
    path = Path(CONFIG_FILE)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return {**CONFIG_DEFAULTS, **json.load(f)}
    return dict(CONFIG_DEFAULTS)


# ── Data loading ──────────────────────────────────────────────────────────────

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


# ── Matching ──────────────────────────────────────────────────────────────────

async def get_job_links(page, base_url: str) -> list[tuple[str, str]]:
    """
    Extract all anchor elements from the page.
    Returns a list of (link_text_line, absolute_url) pairs.

    Link text is split line by line — some ATS platforms put the job title
    on the first line followed by location/type on subsequent lines.
    Relative hrefs are resolved to absolute URLs using base_url.
    """
    result = []
    for anchor in await page.query_selector_all("a[href]"):
        href      = await anchor.get_attribute("href") or ""
        link_text = await anchor.inner_text() or ""
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


# ── Time helpers ──────────────────────────────────────────────────────────────

def format_duration(seconds: float) -> str:
    """Format elapsed seconds as 'Xh. Ymin. Zsec.' omitting leading zero units."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}h. {m}min. {s}sec."
    if m:
        return f"{m}min. {s}sec."
    return f"{s}sec."


# ── Async company scanner ─────────────────────────────────────────────────────

async def scan_company(
    semaphore: asyncio.Semaphore,
    context,
    name: str,
    url: str,
    titles: list[str],
) -> int:
    """
    Scan a single company's career page.
    Controlled by semaphore to cap concurrent open tabs.
    Collects all output lines then prints them atomically so results
    from parallel tabs don't interleave in the console.

    Returns the number of matches found.
    """
    async with semaphore:
        page = await context.new_page()
        lines = [f"\n🔎  Scanning : {name} - {url}"]
        match_count = 0
        try:
            await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
            links   = await get_job_links(page, url)
            matches = find_matches(links, titles)

            if matches:
                for title, job_url in matches:
                    lines.append(f"✅  Match for: [{title}] {job_url}")
                    match_count += 1
            else:
                lines.append("❌  No matches found")

        except PlaywrightTimeoutError:
            lines.append("⚠️   Timeout — page took too long to load, skipping")
        except Exception as e:
            lines.append(f"⚠️   Error — {e}")
        finally:
            await page.close()

        # Print all lines for this company in one shot — keeps output grouped
        print("\n".join(lines))
        return match_count


# ── Main run loop ─────────────────────────────────────────────────────────────

async def run(companies_path: str, titles_path: str, headless: bool, concurrency: int) -> None:
    companies  = load_companies(companies_path)
    titles     = load_titles(titles_path)
    start_time = datetime.now()

    print(f"Start time        : {start_time.strftime('%H:%M')}")
    print(f"Companies loaded  : {len(companies)}")
    print(f"Titles loaded     : {len(titles)}")
    print(f"Concurrency       : {concurrency} tab(s)")
    print(f"Headless          : {headless}")
    print("─" * 60)

    semaphore = asyncio.Semaphore(concurrency)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        tasks = [
            scan_company(semaphore, context, name, url, titles)
            for name, url in companies
        ]
        results = await asyncio.gather(*tasks)
        total_matches = sum(results)

        await browser.close()

    end_time = datetime.now()
    elapsed  = (end_time - start_time).total_seconds()

    print("\n" + "─" * 60)
    print(f"🏁  Done in {format_duration(elapsed)}")
    print(f"   - end time  : {end_time.strftime('%H:%M')}")
    print(f"   - searched  : {len(companies)} companies")
    print(f"   - found     : {total_matches} match(es)\n")


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
        "--no-headless", action="store_true",
        help="Run with a visible browser window (useful for debugging)"
    )
    args = parser.parse_args()

    asyncio.run(run(
        companies_path=args.companies,
        titles_path=args.titles,
        headless=not args.no_headless,
        concurrency=args.concurrency,
    ))


if __name__ == "__main__":
    main()
