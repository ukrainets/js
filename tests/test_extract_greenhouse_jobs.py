"""
Unit tests for extract_greenhouse_jobs() in crawlers/api_greenhouse.py.

Pure unit tests — no HTTP, no async, no file I/O.
Run with: pytest tests/test_extract_greenhouse_jobs.py -v
"""

from crawlers.api_greenhouse import extract_greenhouse_jobs


def test_returns_title_and_absolute_url():
    data = {"jobs": [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]}
    assert extract_greenhouse_jobs(data) == [("QA Engineer", "https://example.com/job/1")]


def test_multiple_jobs():
    data = {"jobs": [
        {"title": "QA Engineer",   "absolute_url": "https://example.com/job/1"},
        {"title": "SDET",          "absolute_url": "https://example.com/job/2"},
    ]}
    assert extract_greenhouse_jobs(data) == [
        ("QA Engineer", "https://example.com/job/1"),
        ("SDET",        "https://example.com/job/2"),
    ]


def test_filters_out_missing_title():
    data = {"jobs": [{"title": "", "absolute_url": "https://example.com/job/1"}]}
    assert extract_greenhouse_jobs(data) == []


def test_filters_out_missing_url():
    data = {"jobs": [{"title": "QA Engineer", "absolute_url": ""}]}
    assert extract_greenhouse_jobs(data) == []


def test_filters_out_missing_keys():
    data = {"jobs": [{"title": "QA Engineer"}]}
    assert extract_greenhouse_jobs(data) == []


def test_empty_jobs_list():
    assert extract_greenhouse_jobs({"jobs": []}) == []


def test_missing_jobs_key():
    assert extract_greenhouse_jobs({}) == []


def test_none_jobs_value():
    assert extract_greenhouse_jobs({"jobs": None}) == []
