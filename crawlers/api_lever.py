"""
Lever job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.

Lever's ?mode=json endpoint returns a flat JSON array (not a dict),
so the extractor receives a list instead of the usual dict.
"""


def extract_lever_jobs(data) -> list[tuple[str, str]]:
    """Extract (title, absolute_url) pairs from a Lever board API response."""
    if not isinstance(data, list):
        return []
    return [
        (job["text"], job["hostedUrl"])
        for job in data
        if job.get("text") and job.get("hostedUrl")
    ]
