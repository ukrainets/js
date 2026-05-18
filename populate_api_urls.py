#!/usr/bin/env python3
from __future__ import annotations

"""
populate_api_urls.py
====================
Reads the companies CSV, extracts board tokens from open_positions_url (or
derives them from the website domain), builds the full API endpoint URL for
each supported platform, and writes it back to the api_url column.

Supported platforms are defined in PLATFORM_REGISTRY — adding a new ATS is
a single dict entry.

Run once after adding new companies to keep the api_url column current.

Usage
-----
    python populate_api_urls.py
    python populate_api_urls.py --input data/companies.csv --output data/companies.csv
    python populate_api_urls.py --validate   # HEAD-check each generated URL
"""

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_INPUT  = "data/companies.csv"
DEFAULT_OUTPUT = "data/companies.csv"

PLATFORM_REGISTRY: dict[str, dict] = {
    "greenhouse": {
        "hosts":   {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"},
        "api_url": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
    },
    "ashby": {
        "hosts":   {"jobs.ashbyhq.com"},
        "api_url": "https://api.ashbyhq.com/posting-api/job-board/{token}",
    },
    "lever": {
        "hosts":   {"jobs.lever.co"},
        "api_url": "https://api.lever.co/v0/postings/{token}?mode=json",
    },
    "workable": {
        "hosts":   {"apply.workable.com"},
        "api_url": "https://apply.workable.com/api/v1/widget/accounts/{token}",
    },
    "gem": {
        "hosts":   {"jobs.gem.com"},
        "api_url": "https://api.gem.com/job_board/v0/{token}/job_posts/",
    },
}


def extract_board_token(url: str, platform: str) -> str | None:
    """
    Parse a job board URL for the given platform and return the board token.

    Looks up the platform's known hosts from PLATFORM_REGISTRY and extracts
    the first non-empty path segment as the token.
    Returns None for non-matching hosts, missing platforms, or malformed input.
    """
    if not url:
        return None
    config = PLATFORM_REGISTRY.get(platform)
    if not config:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.hostname not in config["hosts"]:
        return None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        return None
    return parts[0]


def build_api_url(token: str, platform: str) -> str:
    """Build the full API endpoint URL for a given token and platform."""
    return PLATFORM_REGISTRY[platform]["api_url"].format(token=token)


def probe_api(token: str, platform: str) -> bool:
    """
    Check whether the platform's board API responds for a given token.
    Returns True only on HTTP 200. Returns False for unknown platforms.
    """
    if platform not in PLATFORM_REGISTRY:
        return False
    url = build_api_url(token, platform)
    try:
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
        return r.status_code == 200 and str(r.url).startswith("https://")
    except Exception:
        return False


def derive_candidate_token(website_url: str) -> str:
    """
    Derive a board token candidate from a company website URL.
    Extracts the second-level domain, which companies typically use as their
    ATS board token.
    Returns an empty string on invalid/missing input.

    Examples:
      "https://www.upwork.com"  → "upwork"
      "https://www.vendhq.com"  → "vendhq"
    """
    if not website_url:
        return ""
    try:
        url = website_url if "://" in website_url else f"https://{website_url}"
        hostname = urlparse(url).hostname or ""
        parts = hostname.split(".")
        if len(parts) < 2:
            return ""
        return re.sub(r"[^a-z0-9]", "", parts[-2].lower())
    except Exception:
        return ""


def validate_url(url: str) -> bool:
    try:
        r = httpx.head(url, timeout=10.0, follow_redirects=True)
        return r.status_code < 400 and str(r.url).startswith("https://")
    except Exception:
        return False


def run(input_path: str, output_path: str, validate: bool) -> None:
    path = Path(input_path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]

    if "api_token" not in fieldnames:
        fieldnames.append("api_token")
        for row in rows:
            row["api_token"] = ""

    print("🔧  Populating API URLs...")

    per_platform = {plat: {"populated": 0, "guessed": 0, "skipped": 0} for plat in PLATFORM_REGISTRY}
    already_set = 0

    for row in rows:
        platform    = (row.get("hr_platform") or "").strip().lower()
        existing    = (row.get("api_token") or "").strip()
        name        = (row.get("company_name") or "(unknown)").strip()

        if existing:
            already_set += 1
            continue

        if platform not in PLATFORM_REGISTRY:
            continue

        token = extract_board_token(row.get("open_positions_url") or "", platform)

        if token:
            if validate:
                if not validate_url(build_api_url(token, platform)):
                    print(f"   ⚠️  {name} — generated URL returned error, skipping")
                    per_platform[platform]["skipped"] += 1
                    continue
            row["api_token"] = token
            per_platform[platform]["populated"] += 1
            print(f"   ✅  {name} → {token}")
        else:
            candidate = derive_candidate_token(row.get("website") or "")
            if candidate and probe_api(candidate, platform):
                row["api_token"] = candidate
                per_platform[platform]["guessed"] += 1
                print(f"   ✅  {name} → {candidate}  (token guessed from website domain)")
            else:
                per_platform[platform]["skipped"] += 1
                print(f"   ⚠️  {name} — custom URL, domain-guess failed (will use Playwright)")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n📊  Summary:")
    for plat, counts in per_platform.items():
        total = counts["populated"] + counts["guessed"] + counts["skipped"]
        if total > 0:
            print(f"    {plat.capitalize():<12}: {counts['populated']} from URL, {counts['guessed']} guessed, {counts['skipped']} skipped")
    print(f"    Already set  : {already_set}")
    print(f"📄  Written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate api_url column for supported ATS platforms")
    parser.add_argument("--input",    default=DEFAULT_INPUT,  help="Path to input CSV")
    parser.add_argument("--output",   default=DEFAULT_OUTPUT, help="Path to output CSV")
    parser.add_argument("--validate", action="store_true",    help="HEAD-check each generated URL")
    args = parser.parse_args()

    run(input_path=args.input, output_path=args.output, validate=args.validate)


if __name__ == "__main__":
    main()
