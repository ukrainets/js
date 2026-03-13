"""
CSV I/O — reading input data and writing output results.
"""

import csv
import uuid
from pathlib import Path

# ── Output schema ─────────────────────────────────────────────────────────────
CSV_COLUMNS = ["id", "company_name", "match_position_url", "time_found", "reviewed", "comment"]


def load_companies(path: str) -> list[tuple[str, str]]:
    """
    Read companies CSV and return a sorted, deduplicated list of (company_name, open_positions_url).

    Filtering:
    - Only rows where no_click == "TRUE" are included.
    - Rows with missing name or URL are skipped.
    - Duplicate URLs are skipped.

    Ordering:
    - Sorted by rating descending (1–5). Companies with no rating go last.
    """
    companies, seen = [], set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            no_click = row.get("no_click", "").strip().upper()
            if no_click != "TRUE":
                continue

            name = row["company_name"].strip()
            url  = row["open_positions_url"].strip()
            if not name or not url or url in seen:
                continue

            seen.add(url)
            raw_rating = row.get("rating", "").strip()
            rating = float(raw_rating) if raw_rating else 0.0
            companies.append((name, url, rating))

    companies.sort(key=lambda c: c[2], reverse=True)
    return [(name, url) for name, url, _ in companies]


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


def load_known_urls(path: str) -> set[str]:
    """
    Read all match_position_url values from the existing output CSV.
    Returns an empty set if the file does not exist.
    Called once at startup to pre-populate the in-memory duplicate guard.
    Rows with an empty id field are skipped (artifact of Google Sheets edits).
    """
    p = Path(path)
    if not p.exists():
        return set()
    with open(p, newline="", encoding="utf-8") as f:
        return {
            row["match_position_url"]
            for row in csv.DictReader(f)
            if row.get("id") and row.get("match_position_url")
        }


def append_match_row(match: dict, path: str) -> None:
    """
    Append a single match row to the output CSV.
    Creates the file and header row if it does not exist.
    Must be called under asyncio.Lock — never invoked concurrently.

    Guard: if the file exists but its last byte is not \\n (e.g. after a
    Google Sheets export), a newline is prepended so the new row starts
    on its own line rather than being fused with the previous last line.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output.exists()

    # Guard: Google Sheets export strips trailing newline — fix before appending
    if file_exists and output.stat().st_size > 0:
        with open(output, "rb") as f_check:
            f_check.seek(-1, 2)
            if f_check.read(1) != b"\n":
                with open(output, "a", encoding="utf-8") as f_fix:
                    f_fix.write("\n")

    with open(output, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "id":                 str(uuid.uuid4()),
            "company_name":       match["company_name"],
            "match_position_url": match["match_position_url"],
            "time_found":         match["time_found"],
            "reviewed":           "",
            "comment":            "",
        })
