"""
Shared utility helpers.
"""


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
