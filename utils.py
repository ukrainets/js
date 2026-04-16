"""
Shared utility helpers.
"""

import re


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
