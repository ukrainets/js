#!/usr/bin/env python3
"""
populate_api_urls.py
====================
One-off helper that reads the companies data, extracts Greenhouse board tokens
from open_positions_url, builds the full API endpoint URL, and writes it back
to the `api` column.

For Greenhouse companies with a custom career page URL (token not extractable),
the script tries to derive a board token from the company name and probes the
Greenhouse API. Companies where the guessed token returns HTTP 200 get an api
URL populated; the rest fall back to the Playwright scanner.

Run once after adding new Greenhouse companies to keep the api column current.

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

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
GREENHOUSE_HOSTS    = {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}


def extract_board_token(url: str) -> str | None:
    """
    Parse a Greenhouse job board URL and return the board token, or None.

    Handles:
      https://job-boards.greenhouse.io/{token}/
      https://job-boards.eu.greenhouse.io/{token}/
    Returns None for custom/non-Greenhouse URLs and malformed/empty input.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    if parsed.hostname not in GREENHOUSE_HOSTS:
        return None

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        return None
    return parts[0]


def derive_candidate_token(website_url: str) -> str:
    """
    Derive a Greenhouse board token candidate from a company website URL.
    Extracts the second-level domain (SLD), which companies typically use
    as their Greenhouse board token.
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


def probe_greenhouse_api(token: str) -> bool:
    """
    Check whether the Greenhouse board API responds for a given token.
    Returns True only on HTTP 200 (a 404 JSON body comes back as HTTP 404).
    """
    url = GREENHOUSE_API_BASE.format(token=token)
    try:
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def validate_url(url: str) -> bool:
    try:
        r = httpx.head(url, timeout=10.0, follow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False


def run(input_path: str, output_path: str, validate: bool) -> None:
    path = Path(input_path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]

    if "api_url" not in fieldnames:
        fieldnames.append("api_url")
        for row in rows:
            row["api_url"] = ""

    print("🔧  Populating API URLs for Greenhouse companies...")

    populated = guessed = skipped = already_set = 0

    for row in rows:
        platform = row.get("hr_platform", "").strip().lower()
        existing_api = row.get("api_url", "").strip()

        if existing_api:
            already_set += 1
            continue

        if platform != "greenhouse":
            continue

        token = extract_board_token(row.get("open_positions_url", ""))
        name  = row.get("company_name", "(unknown)")

        if token:
            api_url = GREENHOUSE_API_BASE.format(token=token)
            if validate:
                ok = validate_url(api_url)
                if not ok:
                    print(f"   ⚠️  {name} — generated URL returned error, skipping")
                    skipped += 1
                    continue
            row["api_url"] = api_url
            populated += 1
            print(f"   ✅  {name} → {api_url}")
        else:
            candidate = derive_candidate_token(row.get("website", ""))
            if candidate and probe_greenhouse_api(candidate):
                api_url = GREENHOUSE_API_BASE.format(token=candidate)
                row["api_url"] = api_url
                guessed += 1
                print(f"   ✅  {name} → {api_url}  (token guessed from website domain)")
            else:
                skipped += 1
                print(f"   ⚠️  {name} — custom URL, domain-guess failed (will use Playwright)")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n📊  Summary: {populated} from URL, {guessed} guessed from name, {skipped} skipped, {already_set} already had API URLs")
    print(f"📄  Written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate api column for Greenhouse companies")
    parser.add_argument("--input",    default=DEFAULT_INPUT,  help="Path to input CSV")
    parser.add_argument("--output",   default=DEFAULT_OUTPUT, help="Path to output CSV")
    parser.add_argument("--validate", action="store_true",    help="HEAD-check each generated URL")
    args = parser.parse_args()

    run(input_path=args.input, output_path=args.output, validate=args.validate)


if __name__ == "__main__":
    main()
