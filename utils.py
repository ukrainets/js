"""
Shared utility helpers.
"""

import re


def find_matches(links: list[tuple[str, str]], titles: list[str]) -> list[tuple[str, str, str]]:
    """
    Return (original_title, scraped_text, href) triples where a title appears
    as a complete word sequence anywhere in the link text (case-insensitive,
    brackets stripped).

    Both sides are normalized via normalize_text() before comparison.
    Word-boundary regex ensures "QA Lead" won't match "Squad Leader".
    Deduplicates by href — first matching title per URL wins.
    Regex patterns are pre-compiled once and reused across all links.
    """
    patterns = [
        (t, re.compile(r'\b' + re.escape(normalize_text(t)) + r'\b', re.IGNORECASE))
        for t in titles
        if normalize_text(t)
    ]

    seen, matches = set(), []
    for line, href in links:
        if href in seen:
            continue
        normalized_line = normalize_text(line)
        for original_title, pattern in patterns:
            if pattern.search(normalized_line):
                matches.append((original_title, line, href))
                seen.add(href)
                break
    return matches


def normalize_text(text: str) -> str:
    """
    Strip bracket groups and normalize whitespace for title matching.
    Preserves dots, commas, hyphens, and ampersands (appear in real titles).

    normalize_text("Automation Engineer (Mid level SDET)") → "automation engineer"
    normalize_text("QA Engineer [Automation]")             → "qa engineer"
    normalize_text("  Sr.  QA   Engineer  ")               → "sr. qa engineer"
    normalize_text("(Remote)")                             → ""
    """
    text = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()


def apply_filters(jobs: list[tuple], filters: dict) -> list[tuple]:
    """
    Filter (title, url, meta) triples using the 'filters' config section.

    Pass-through rules (all fields):
    - countries / states / city: if the job has no location data, it passes through.
    - remote_only: if is_remote is None (platform doesn't expose it), passes through.
    - full_time_only: if is_full_time is None (platform doesn't expose it), passes through.

    remote_only + city together use OR logic: a job passes if it is remote OR in the city.
    A job is only excluded when both conditions are definitively false (known not-remote AND
    location data exists but city doesn't match).
    """
    if not filters or not filters.get("enabled", True):
        return jobs
    countries      = [c.lower() for c in (filters.get("countries") or [])]
    states         = [s.lower() for s in (filters.get("states")    or [])]
    city           = (filters.get("city") or "").lower().strip()
    remote_only    = filters.get("remote_only",    False)
    full_time_only = filters.get("full_time_only", False)

    if not countries and not states and not city and not remote_only and not full_time_only:
        return jobs

    result = []
    for item in jobs:
        title, url, meta = item
        loc          = meta.get("location", "").lower()
        country      = meta.get("country",  "").lower()
        state        = meta.get("state",    "").lower()
        is_remote    = meta.get("is_remote")
        is_full_time = meta.get("is_full_time")

        if countries and (country or loc):
            if not any(c in country or c in loc for c in countries):
                continue

        if states and (state or loc):
            if not any(s in state or s in loc for s in states):
                continue

        if remote_only and city:
            # OR mode: exclude only when known not-remote AND city confirmed absent
            not_remote  = (is_remote is False)
            not_in_city = bool(loc) and (city not in loc)
            if not_remote and not_in_city:
                continue
        elif remote_only:
            if is_remote is False:
                continue
        elif city:
            if loc and city not in loc:
                continue

        if full_time_only and is_full_time is False:
            continue

        result.append(item)
    return result


def format_duration(seconds: float) -> str:
    """Format elapsed seconds as 'Xh. Ymin. Zsec.' omitting leading zero units."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}h. {m}min. {s}sec."
    if m:
        return f"{m}min. {s}sec."
    return f"{s}sec."
