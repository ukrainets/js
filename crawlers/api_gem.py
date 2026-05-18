"""
Gem job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.

Gem's API returns a flat JSON array with the same field names as Greenhouse.
"""


def extract_gem_jobs(data) -> list[tuple[str, str, dict]]:
    """Extract (title, absolute_url, meta) triples from a Gem board API response."""
    if not isinstance(data, list):
        return []
    result = []
    for job in data:
        title = job.get("title")
        url = job.get("absolute_url")
        if not title or not url:
            continue
        loc = job.get("location") or {}
        loc_str = loc.get("name", "") if isinstance(loc, dict) else str(loc)
        result.append((title, url, {
            "location": loc_str,
            "country": "",
            "state": "",
            "is_remote": None,
            "is_full_time": None,
        }))
    return result
