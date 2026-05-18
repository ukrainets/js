"""
Unit tests for extract_ashby_jobs() in crawlers/api_ashby.py.

Pure unit tests — no HTTP, no async, no file I/O.
Run with: pytest tests/test_extract_ashby_jobs.py -v
"""

from crawlers.api_ashby import extract_ashby_jobs


def titles_and_urls(result):
    return [(t, u) for t, u, _ in result]


def test_returns_title_and_job_url_for_listed_job():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True}]}
    assert titles_and_urls(extract_ashby_jobs(data)) == [("QA Engineer", "https://jobs.ashbyhq.com/acme/1")]


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
    assert titles_and_urls(extract_ashby_jobs(data)) == [
        ("QA Engineer", "https://jobs.ashbyhq.com/acme/1"),
        ("SDET",        "https://jobs.ashbyhq.com/acme/2"),
    ]


def test_meta_employment_type_full_time():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                      "isListed": True, "employmentType": "FullTime"}]}
    _, _, meta = extract_ashby_jobs(data)[0]
    assert meta["is_full_time"] is True


def test_meta_employment_type_part_time():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                      "isListed": True, "employmentType": "PartTime"}]}
    _, _, meta = extract_ashby_jobs(data)[0]
    assert meta["is_full_time"] is False


def test_meta_is_remote_explicit():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                      "isListed": True, "isRemote": True}]}
    _, _, meta = extract_ashby_jobs(data)[0]
    assert meta["is_remote"] is True


def test_meta_is_remote_inferred_from_location():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                      "isListed": True, "locationName": "Remote - US"}]}
    _, _, meta = extract_ashby_jobs(data)[0]
    assert meta["is_remote"] is True


def test_meta_unknown_fields_are_none():
    data = {"jobs": [{"title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                      "isListed": True}]}
    _, _, meta = extract_ashby_jobs(data)[0]
    assert meta["is_remote"] is None
    assert meta["is_full_time"] is None
    assert meta["location"] == ""
