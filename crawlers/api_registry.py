"""
API platform registry — single source of truth for supported ATS integrations.

To add a new platform: import its extractor, add one entry to API_EXTRACTORS.
"""

from crawlers.api_ashby import extract_ashby_jobs
from crawlers.api_greenhouse import extract_greenhouse_jobs

# Maps lowercase hr_platform value → (extractor callable, console label)
API_EXTRACTORS: dict[str, tuple] = {
    "greenhouse": (extract_greenhouse_jobs, "Greenhouse"),
    "ashby":      (extract_ashby_jobs,      "Ashby"),
}
