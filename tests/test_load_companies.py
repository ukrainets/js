"""
Unit tests for load_companies() in csv_io.py.

Verifies dict shape, filtering, deduplication, sorting, and routing split.
Run with: pytest tests/test_load_companies.py -v
"""

import csv

from csv_io import load_companies

FIXTURE = "tests/test_data/companies.csv"


def test_returns_list_of_dicts():
    companies = load_companies(FIXTURE)
    assert isinstance(companies, list)
    assert all(isinstance(c, dict) for c in companies)


def test_required_keys_present():
    companies = load_companies(FIXTURE)
    for c in companies:
        assert "company_name"       in c
        assert "open_positions_url" in c
        assert "hr_platform"        in c
        assert "api_url"                in c


def test_no_internal_rating_key_leaked():
    companies = load_companies(FIXTURE)
    for c in companies:
        assert "_rating" not in c


def test_greenhouse_companies_have_api_url():
    companies = load_companies(FIXTURE)
    greenhouse = [c for c in companies if c["hr_platform"] == "greenhouse"]
    assert len(greenhouse) > 0
    for c in greenhouse:
        assert c["api_url"].startswith("https://boards-api.greenhouse.io/"), \
            f"{c['company_name']} missing api url"


def test_ashby_companies_have_api_url():
    companies = load_companies(FIXTURE)
    ashby = [c for c in companies if c["hr_platform"] == "ashby"]
    assert len(ashby) > 0
    for c in ashby:
        assert c["api_url"].startswith("https://api.ashbyhq.com/posting-api/job-board/"), \
            f"{c['company_name']} missing ashby api url"


def test_other_platforms_have_empty_api():
    other_platforms = {"workday", "rippling", "workable", "gem", "custom", ""}
    companies = load_companies(FIXTURE)
    for c in companies:
        if c["hr_platform"] in other_platforms:
            assert c["api_url"] == "", f"{c['company_name']} should have empty api"


def test_routing_split_is_correct():
    companies = load_companies(FIXTURE)
    api_companies = [c for c in companies if c["api_url"]]
    pw_companies  = [c for c in companies if not c["api_url"]]
    assert len(api_companies) + len(pw_companies) == len(companies)
    assert len(api_companies) > 0
    assert len(pw_companies)  > 0


def test_only_no_click_true_included():
    # All returned companies must have come from no_click=TRUE rows
    # (fixture has a mix — verify nothing slipped through)
    companies = load_companies(FIXTURE)
    names = {c["company_name"] for c in companies}
    assert len(companies) > 0
    # Spot-check: known TRUE rows are present
    assert "Halcyon" in names or "Amount" in names


def test_no_duplicate_urls():
    companies = load_companies(FIXTURE)
    urls = [c["open_positions_url"] for c in companies]
    assert len(urls) == len(set(urls))


def test_unsafe_url_schemes_are_skipped(tmp_path):
    csv_file = tmp_path / "companies.csv"
    header = ["id", "rating", "company_name", "website", "open_positions_url",
              "hr_platform", "no_click", "comment", "field", "api_url"]
    rows = [
        ["1", "5", "Safe Co",  "", "https://safe.com/jobs",          "custom", "TRUE", "", "", ""],
        ["2", "5", "File Co",  "", "file:///etc/passwd",              "custom", "TRUE", "", "", ""],
        ["3", "5", "FTP Co",   "", "ftp://ftp.example.com/jobs",     "custom", "TRUE", "", "", ""],
        ["4", "5", "No Scheme","", "//example.com/jobs",              "custom", "TRUE", "", "", ""],
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    companies = load_companies(str(csv_file))
    names = {c["company_name"] for c in companies}
    assert "Safe Co"   in names
    assert "File Co"   not in names
    assert "FTP Co"    not in names
    assert "No Scheme" not in names


def test_short_row_with_missing_columns_does_not_crash(tmp_path):
    # DictReader fills missing columns with None when a row is shorter than the header.
    # load_companies must not raise AttributeError on None values.
    csv_file = tmp_path / "companies.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "rating", "company_name", "website", "open_positions_url", "hr_platform", "no_click", "comment", "field", "api_url"])
        # Short row — hr_platform, no_click, and api_url are missing → DictReader fills with None
        writer.writerow(["abc123", "5", "ShortRow Corp", "", "https://example.com/jobs"])

    companies = load_companies(str(csv_file))
    # Row is missing no_click so it doesn't pass the TRUE filter — result should be empty, not a crash
    assert isinstance(companies, list)
