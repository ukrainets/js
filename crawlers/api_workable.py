"""
Workable job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_workable_jobs(data: dict) -> list[tuple[str, str]]:
    """Extract (title, absolute_url) pairs from a Workable widget API response."""
    jobs = data.get("jobs", []) or []
    return [
        (job["title"], job["url"])
        for job in jobs
        if job.get("state") == "published"
        and job.get("title")
        and job.get("url")
    ]
