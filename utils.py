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
