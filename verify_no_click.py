#!/usr/bin/env python3
from __future__ import annotations

"""
verify_no_click.py
==================
Visits every open_positions_url and sets the correct no_click value.

  TRUE  – all jobs visible on page load, no extra interaction needed
  FALSE – jobs hidden behind pagination, a search form, or a CTA click

Usage
-----
    python verify_no_click.py                         # default paths
    python verify_no_click.py --input  path/to/in.csv --output path/to/out.csv
    python verify_no_click.py --resume                # continue from checkpoint
    python verify_no_click.py --no-headless           # show browser window

Checkpoint
----------
Progress is saved to  verify_no_click_checkpoint.csv  every 25 rows.
Run with --resume to continue from where the script left off.
"""

import argparse
import csv
import json
import re
import random
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ── Paths ──────────────────────────────────────────────────────────────────
DEFAULT_INPUT      = "data/companies.csv"
DEFAULT_OUTPUT     = "data/companies_verified.csv"
CHECKPOINT_FILE    = "verify_no_click_checkpoint.csv"
CHECKPOINT_IDX     = "verify_no_click_checkpoint_idx.json"

# ── Timing ─────────────────────────────────────────────────────────────────
PAGE_TIMEOUT       = 25_000   # ms – navigation timeout
EXTRA_WAIT_MS      = 1_800    # ms – pause after domcontentloaded (JS settle)
MIN_DELAY          = 0.8      # s  – polite delay between requests
MAX_DELAY          = 2.0

# ── Platform URL patterns ──────────────────────────────────────────────────
# These are deterministic: if the URL loads, the no_click value is known.

TRUE_URL_PATTERNS: list[tuple[str, str]] = [
    (r"job-boards\.greenhouse\.io/",        "greenhouse-board"),
    (r"boards\.greenhouse\.io/",            "greenhouse-board"),
    (r"jobs\.ashbyhq\.com/",               "ashby"),
    (r"jobs\.lever\.co/",                  "lever"),
    (r"ats\.rippling\.com/[^/?]+/jobs",    "rippling"),
    (r"apply\.workable\.com/",             "workable"),
]

FALSE_URL_PATTERNS: list[tuple[str, str]] = [
    (r"\.myworkdayjobs\.com/",             "workday"),
    (r"/hcmUI/CandidateExperience/",       "taleo-cloud"),
    (r"fa\.[a-z0-9-]+\.oraclecloud\.com/", "oracle-cloud"),
    (r"taleo\.net/",                       "taleo"),
    (r"\.icims\.com/",                     "icims"),
    (r"phenom\.people/",                   "phenom"),
    (r"dayforcehcm\.com/",                 "dayforce"),
    (r"adp\.com/",                         "adp"),
]

# ── DOM selectors ──────────────────────────────────────────────────────────

PAGINATION_SELECTORS = [
    # Workday
    "[data-automation-id='paginationWidget']",
    # Generic
    ".pagination",
    "[aria-label='Pagination']",
    "[aria-label='pagination']",
    "nav.pagination",
    "[data-testid='pagination']",
    ".pager",
    "ul.pagination",
    "[class*='Pagination']:not([class*='PaginationLoading'])",
    "[role='navigation'][aria-label*='page' i]",
    # iCIMS / Phenom style
    ".iCIMS_Pager",
    "[data-ph-at-id='pagination']",
]

SEARCH_GATE_SELECTORS = [
    # Prominent search inputs that form the primary job-finding interface
    "input[type='search']",
    "input[data-testid*='search' i]",
    "input[placeholder*='search job' i]",
    "input[placeholder*='job title' i]",
    "input[aria-label*='search job' i]",
    "input[aria-label*='keyword' i]",
]

# Text that appears on CTA-gate pages (no jobs visible, button required)
CTA_REGEX = re.compile(
    r"\b("
    r"see open positions|view open positions|search (?:open )?jobs|"
    r"browse (?:open )?(?:careers|jobs|roles)|explore open roles|"
    r"see open roles|view opportunities|find (?:open )?jobs|"
    r"view all (?:open )?(?:jobs|positions|roles)|"
    r"see all (?:open )?(?:jobs|positions|roles)|"
    r"open positions →|join (?:our )?team →"
    r")\b",
    re.IGNORECASE,
)

# Words that indicate a link is navigation / footer, not a job title
NAV_WORDS = frozenset({
    "home", "about", "contact", "privacy", "terms", "blog",
    "login", "sign in", "sign up", "subscribe", "menu",
    "careers", "jobs", "search", "apply", "cookie", "back",
    "facebook", "twitter", "linkedin", "instagram", "youtube",
    "english", "deutsch", "français", "español", "italiano",
})


# ── Helpers ────────────────────────────────────────────────────────────────

def is_skip_row(row: dict) -> bool:
    """Rows with comment 'true+' were manually verified — skip them."""
    c = (row.get("comment") or "").strip().lower()
    return "true +" in c or "true+" in c


def classify_by_url(url: str) -> tuple[str | None, str]:
    """
    Returns ('TRUE'/'FALSE', platform_name) or (None, '') if unknown.
    Called AFTER confirming the URL is accessible.
    """
    for pattern, name in TRUE_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return "TRUE", name
    for pattern, name in FALSE_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return "FALSE", name
    return None, ""


def count_direct_job_links(page) -> int:
    """
    Count anchors that look like individual job posting links.
    Heuristic: 2+ words, not nav text, visible in the page body.
    Caps at 15 for speed.
    """
    count = 0
    selectors = [
        "main a[href]",
        "#content a[href]",
        "[role='main'] a[href]",
        ".content a[href]",
        "article a[href]",
        "body a[href]",         # fallback
    ]
    for sel in selectors:
        try:
            for anchor in page.query_selector_all(sel)[:60]:
                try:
                    text = (anchor.inner_text() or "").strip()
                    if not text or len(text) < 5 or len(text) > 120:
                        continue
                    words = text.lower().split()
                    if not words or words[0] in NAV_WORDS:
                        continue
                    if len(words) >= 2:
                        count += 1
                        if count >= 15:
                            return count
                except Exception:
                    continue
        except Exception:
            continue
        if count > 0:
            break  # stop at first selector that returned results
    return count


def page_has_pagination(page) -> bool:
    for sel in PAGINATION_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def page_has_search_gate(page) -> bool:
    for sel in SEARCH_GATE_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def page_has_cta_only(page) -> bool:
    try:
        body = (page.inner_text("body") or "").strip()
        return bool(CTA_REGEX.search(body))
    except Exception:
        return False


def analyze_custom_page(page) -> tuple[str, str]:
    """
    DOM-based heuristic for pages not matching a known platform URL.
    Returns ('TRUE'|'FALSE', reason).
    """
    # Pagination is the strongest FALSE signal
    if page_has_pagination(page):
        return "FALSE", "pagination detected"

    job_count = count_direct_job_links(page)

    # Many job links → TRUE
    if job_count >= 4:
        return "TRUE", f"{job_count}+ job links visible"

    # Search-required interface with few/no visible jobs
    if page_has_search_gate(page) and job_count < 3:
        return "FALSE", "search-gate UI, no direct job list"

    # CTA-only gate with no job links
    if page_has_cta_only(page) and job_count < 3:
        return "FALSE", "CTA-gate page, no direct job list"

    # Likely an accessible but empty job board
    return "TRUE", f"no gate elements ({job_count} links — possibly empty board)"


# ── Core verification ──────────────────────────────────────────────────────

def verify_url(page, url: str, existing: str) -> tuple[str, str]:
    """
    Navigate to url and determine no_click value.

    Returns
    -------
    (no_click_value, note)
        note is non-empty only for broken/error cases.
        note is intentionally empty for normal TRUE/FALSE results
        so we don't pollute the comment column.
    """
    url = url.strip()
    if not url:
        return existing, "broken - no URL"

    # Navigate
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        page.wait_for_timeout(EXTRA_WAIT_MS)
    except PWTimeout:
        return existing, "broken - timeout"
    except Exception as e:
        msg = str(e).splitlines()[0][:80]
        return existing, f"broken - {msg}"

    # HTTP error?
    if resp and resp.status >= 400:
        return existing, f"broken - HTTP {resp.status}"

    # Error page title?
    try:
        title = page.title()
        if re.search(r"\b(404|not found|forbidden|error|unavailable)\b", title, re.I):
            return existing, f"broken - error page ({title[:60]})"
    except Exception:
        pass

    # URL-based platform classification (URL confirmed live)
    url_result, _platform = classify_by_url(url)
    if url_result is not None:
        return url_result, ""

    # DOM analysis for custom / unknown pages
    result, _reason = analyze_custom_page(page)
    return result, ""


# ── Checkpoint helpers ─────────────────────────────────────────────────────

def save_checkpoint(rows: list[dict], fieldnames: list[str], last_idx: int) -> None:
    with open(CHECKPOINT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with open(CHECKPOINT_IDX, "w") as f:
        json.dump({"last_completed_index": last_idx}, f)


def load_checkpoint() -> tuple[list[dict], list[str], int]:
    with open(CHECKPOINT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    with open(CHECKPOINT_IDX) as f:
        last_idx = json.load(f).get("last_completed_index", -1)
    return rows, fieldnames, last_idx


# ── Main ───────────────────────────────────────────────────────────────────

def run(input_path: str, output_path: str, headless: bool, resume: bool) -> None:

    # Load data
    if resume and Path(CHECKPOINT_FILE).exists() and Path(CHECKPOINT_IDX).exists():
        rows, fieldnames, start_from = load_checkpoint()
        start_from += 1  # resume from next unprocessed row
        print(f"▶  Resuming from row {start_from + 1}")
    else:
        with open(input_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = [dict(r) for r in reader]
        start_from = 0

    total    = len(rows)
    to_do    = sum(1 for i, r in enumerate(rows) if i >= start_from and not is_skip_row(r))
    skipped  = sum(1 for r in rows if is_skip_row(r))

    print(f"Total rows   : {total}")
    print(f"Skip (true+) : {skipped}")
    print(f"To verify    : {to_do}")
    print(f"Headless     : {headless}")
    print(f"Start time   : {datetime.now().strftime('%H:%M')}")
    print("─" * 65)

    changes  = 0
    broken_n = 0
    done     = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )
        page = context.new_page()
        # Suppress noisy console errors from target pages
        page.on("console", lambda _: None)

        for idx, row in enumerate(rows):

            if idx < start_from:
                continue  # already processed in previous run

            name     = (row.get("company_name") or "").strip()
            url      = (row.get("open_positions_url") or "").strip()
            existing = (row.get("no_click") or "").strip()

            if is_skip_row(row):
                print(f"[{idx+1:>3}/{total}] ⏭️  {name} — skip (true+)")
                continue

            print(f"[{idx+1:>3}/{total}] 🔎  {name}")

            new_val, note = verify_url(page, url, existing)
            done += 1

            if note.startswith("broken"):
                broken_n += 1
                print(f"          ↳ ⚠️  {note}")
            elif new_val != existing:
                changes += 1
                print(f"          ↳ ✏️  {existing or '(blank)'} → {new_val}")
            else:
                print(f"          ↳ ✅  {new_val} confirmed")

            # Apply changes
            row["no_click"] = new_val
            if note:
                cur = (row.get("comment") or "").strip()
                if note not in cur:
                    row["comment"] = f"{cur}, {note}".strip(", ") if cur else note

            # Checkpoint every 25 rows
            if done % 25 == 0:
                save_checkpoint(rows, fieldnames, idx)
                print(f"          💾  checkpoint saved ({done} done, {changes} changed, {broken_n} broken)")

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        browser.close()

    # Final output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Clean up checkpoints on success
    Path(CHECKPOINT_FILE).unlink(missing_ok=True)
    Path(CHECKPOINT_IDX).unlink(missing_ok=True)

    end_time = datetime.now()
    print("\n" + "─" * 65)
    print(f"🏁  Done at {end_time.strftime('%H:%M')}")
    print(f"   Verified : {done}")
    print(f"   Changed  : {changes}")
    print(f"   Broken   : {broken_n}")
    print(f"   Output   : {output_path}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and update no_click values in companies CSV")
    parser.add_argument("--input",       default=DEFAULT_INPUT,  help="Path to input CSV")
    parser.add_argument("--output",      default=DEFAULT_OUTPUT, help="Path to output CSV")
    parser.add_argument("--no-headless", action="store_true",    help="Show browser window")
    parser.add_argument("--resume",      action="store_true",    help="Resume from checkpoint")
    args = parser.parse_args()

    run(
        input_path=args.input,
        output_path=args.output,
        headless=not args.no_headless,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()