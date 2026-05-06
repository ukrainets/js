"""
Unit tests for extract_ashby_jobs() in crawlers/api_ashby.py.

Pure unit tests — no HTTP, no async, no file I/O.
Run with: pytest tests/test_extract_ashby_jobs.py -v
"""

from crawlers.api_ashby import extract_ashby_jobs


def test_returns_title_and_job_url_for_listed_job():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True}]}
    assert extract_ashby_jobs(data) == [("QA Engineer", "https://jobs.ashbyhq.com/acme/1")]


def test_filters_out_unlisted_jobs():
    data = {"jobs": [
        {"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True},
        {"title": "SDET",        "jobUrl": "https://jobs.ashbyhq.com/acme/2", "isListed": False},
    ]}
    result = extract_ashby_jobs(data)
    assert len(result) == 1
    assert result[0][0] == "QA Engineer"


def test_filters_out_jobs_where_is_listed_is_none():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": None}]}
    assert extract_ashby_jobs(data) == []


def test_filters_out_missing_title():
    data = {"jobs": [{"title": "", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True}]}
    assert extract_ashby_jobs(data) == []


def test_filters_out_missing_job_url():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "", "isListed": True}]}
    assert extract_ashby_jobs(data) == []


def test_filters_out_missing_keys():
    data = {"jobs": [{"title": "QA Engineer", "isListed": True}]}
    assert extract_ashby_jobs(data) == []


def test_empty_jobs_list():
    assert extract_ashby_jobs({"jobs": []}) == []


def test_missing_jobs_key():
    assert extract_ashby_jobs({}) == []


def test_none_jobs_value():
    assert extract_ashby_jobs({"jobs": None}) == []


def test_multiple_listed_jobs():
    data = {"jobs": [
        {"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True},
        {"title": "SDET",        "jobUrl": "https://jobs.ashbyhq.com/acme/2", "isListed": True},
    ]}
    assert extract_ashby_jobs(data) == [
        ("QA Engineer", "https://jobs.ashbyhq.com/acme/1"),
        ("SDET",        "https://jobs.ashbyhq.com/acme/2"),
    ]
