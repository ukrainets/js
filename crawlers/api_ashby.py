"""
Ashby job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_ashby_jobs(data: dict) -> list[tuple[str, str, dict]]:
    """
    Extract (title, jobUrl, meta) triples from an Ashby job-board API response.
    Filters out isListed=False entries so unlisted jobs are never surfaced.
    """
    jobs = data.get("jobs", []) or []
    result = []
    for job in jobs:
        if job.get("isListed") is not True:
            continue
        title = job.get("title")
        url = job.get("jobUrl")
        if not title or not url:
            continue
        loc = job.get("locationName") or job.get("location") or ""
        if not isinstance(loc, str):
            loc = ""
        is_remote = job.get("isRemote")
        if is_remote is None and loc and "remote" in loc.lower():
            is_remote = True
        emp_type = job.get("employmentType", "")
        is_full_time = (emp_type in ("FullTime", "FULL_TIME")) if emp_type else None
        result.append((title, url, {
            "location": loc,
            "country": "",
            "state": "",
            "is_remote": is_remote,
            "is_full_time": is_full_time,
        }))
    return result
