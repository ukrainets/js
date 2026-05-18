"""
Workable job-board API extractor.

Pure transformation — no HTTP, no async, no I/O.
Used by scan_api() in api_scanner.py.
"""


def extract_workable_jobs(data: dict) -> list[tuple[str, str, dict]]:
    """Extract (title, url, meta) triples from a Workable widget API response."""
    jobs = data.get("jobs", []) or []
    result = []
    for job in jobs:
        if job.get("state") != "published":
            continue
        title = job.get("title")
        url = job.get("url")
        if not title or not url:
            continue
        loc = job.get("location") or {}
        country = loc.get("country", "") if isinstance(loc, dict) else ""
        state   = loc.get("region", "")  if isinstance(loc, dict) else ""
        city    = loc.get("city", "")    if isinstance(loc, dict) else ""
        loc_str = ", ".join(filter(None, [city, state, country]))
        telecommuting = loc.get("telecommuting") if isinstance(loc, dict) else None
        if telecommuting is not None:
            is_remote = bool(telecommuting)
        elif loc_str and "remote" in loc_str.lower():
            is_remote = True
        else:
            is_remote = None
        emp_type = job.get("employment_type", "")
        is_full_time = ("full" in emp_type.lower()) if emp_type else None
        result.append((title, url, {
            "location": loc_str,
            "country": country,
            "state": state,
            "is_remote": is_remote,
            "is_full_time": is_full_time,
        }))
    return result
