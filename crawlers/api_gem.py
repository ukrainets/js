"""
Gem job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.

Gem's API returns a flat JSON array with the same field names as Greenhouse.
"""


def extract_gem_jobs(data) -> list[tuple[str, str]]:
    """Extract (title, absolute_url) pairs from a Gem board API response."""
    if not isinstance(data, list):
        return []
    return [
        (job["title"], job["absolute_url"])
        for job in data
        if job.get("title") and job.get("absolute_url")
    ]
