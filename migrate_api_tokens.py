#!/usr/bin/env python3
"""
One-off migration: replace full Greenhouse/Ashby API URLs in the api_url
column with just the board token (slug).

Before: https://boards-api.greenhouse.io/v1/boards/canopytax/jobs
After:  canopytax
"""

import csv
from pathlib import Path

CSV_PATH = "data/companies.csv"

TOKEN_EXTRACTORS = {
    "greenhouse": lambda url: url.split("/boards/")[1].split("/")[0] if "/boards/" in url else None,
    "ashby":      lambda url: url.split("/job-board/")[1].split("/")[0] if "/job-board/" in url else None,
}


def main() -> None:
    path = Path(CSV_PATH)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]

    changed = 0
    for row in rows:
        platform = (row.get("hr_platform") or "").strip().lower()
        api_url  = (row.get("api_url") or "").strip()
        name     = row.get("company_name", "(unknown)")

        if not api_url or platform not in TOKEN_EXTRACTORS:
            continue

        token = TOKEN_EXTRACTORS[platform](api_url)
        if token and token != api_url:
            row["api_url"] = token
            print(f"  {name}: {api_url!r} → {token!r}")
            changed += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone — {changed} rows updated.")


if __name__ == "__main__":
    main()
