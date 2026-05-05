"""
Configuration — constants and config file loader.
"""

import json
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE        = "config.json"
PAGE_TIMEOUT       = 30_000   # ms — first navigation attempt
PAGE_TIMEOUT_RETRY = 60_000   # ms — single retry after timeout
PAGE_SETTLE_MS     = 2_000    # ms — wait after domcontentloaded for JS to render
API_CONCURRENCY    = 20       # max concurrent Greenhouse API requests

CONFIG_DEFAULTS = {
    "concurrency":        5,
    "companies_file":     "data/companies.csv",
    "titles_file":        "data/sqa_titles.csv",
    "output_file":        "data/match.csv",
    "schedule_times":     ["08:08", "13:13", "18:18"],
    "log_dir":              "logs",
    "log_retention_days":   30,
    "logging_enabled":      True,
    "notifications_enabled": True,
}


def load_config() -> dict:
    """
    Load config.json and merge with defaults.
    Any key missing from the file falls back to CONFIG_DEFAULTS.
    """
    path = Path(CONFIG_FILE)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return {**CONFIG_DEFAULTS, **json.load(f)}
    return dict(CONFIG_DEFAULTS)
