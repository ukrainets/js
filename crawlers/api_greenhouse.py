"""
Greenhouse job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_greenhouse_jobs(data: dict) -> list[tuple[str, str, dict]]:
    """Extract (title, absolute_url, meta) triples from a Greenhouse board API response."""
    jobs = data.get("jobs", []) or []
    result = []
    for job in jobs:
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
