"""
Greenhouse job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_greenhouse_jobs(data: dict) -> list[tuple[str, str]]:
    """Extract (title, absolute_url) pairs from a Greenhouse board API response."""
    jobs = data.get("jobs", []) or []
    return [
        (job["title"], job["absolute_url"])
        for job in jobs
        if job.get("title") and job.get("absolute_url")
    ]
