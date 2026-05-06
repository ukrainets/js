"""
Ashby job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_ashby_jobs(data: dict) -> list[tuple[str, str]]:
    """
    Extract (title, jobUrl) pairs from an Ashby job-board API response.
    Filters out isListed=False entries so unlisted jobs are never surfaced.
    """
    jobs = data.get("jobs", []) or []
    return [
        (job["title"], job["jobUrl"])
        for job in jobs
        if job.get("isListed") is True
        and job.get("title")
        and job.get("jobUrl")
    ]
