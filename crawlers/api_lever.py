"""
Lever job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.

Lever's ?mode=json endpoint returns a flat JSON array (not a dict),
so the extractor receives a list instead of the usual dict.
"""


def extract_lever_jobs(data) -> list[tuple[str, str, dict]]:
    """Extract (title, hostedUrl, meta) triples from a Lever board API response."""
    if not isinstance(data, list):
        return []
    result = []
    for job in data:
        title = job.get("text")
        url = job.get("hostedUrl")
        if not title or not url:
            continue
        categories = job.get("categories") or {}
        loc = categories.get("location", "")
        commitment = categories.get("commitment", "")
        workplace = job.get("workplaceType", "")

        if workplace == "remote":
            is_remote = True
        elif workplace in ("on-site", "hybrid"):
            is_remote = False
        elif loc and "remote" in loc.lower():
            is_remote = True
        else:
            is_remote = None

        is_full_time = ("full" in commitment.lower()) if commitment else None

        result.append((title, url, {
            "location": loc,
            "country": "",
            "state": "",
            "is_remote": is_remote,
            "is_full_time": is_full_time,
        }))
    return result
