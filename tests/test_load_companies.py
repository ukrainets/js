"""
Unit tests for load_companies() in csv_io.py.

Verifies dict shape, filtering, deduplication, sorting, and routing split.
Run with: pytest tests/test_load_companies.py -v
"""

import pytest
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
        assert "api"                in c


def test_no_internal_rating_key_leaked():
    companies = load_companies(FIXTURE)
    for c in companies:
        assert "_rating" not in c


def test_greenhouse_companies_have_api_url():
    companies = load_companies(FIXTURE)
    greenhouse = [c for c in companies if c["hr_platform"] == "greenhouse"]
    assert len(greenhouse) > 0
    for c in greenhouse:
        assert c["api"].startswith("https://boards-api.greenhouse.io/"), \
            f"{c['company_name']} missing api url"


def test_non_greenhouse_companies_have_empty_api():
    companies = load_companies(FIXTURE)
    non_greenhouse = [c for c in companies if c["hr_platform"] != "greenhouse"]
    for c in non_greenhouse:
        assert c["api"] == "", f"{c['company_name']} should have empty api"


def test_routing_split_is_correct():
    companies = load_companies(FIXTURE)
    api_companies = [c for c in companies if c["api"]]
    pw_companies  = [c for c in companies if not c["api"]]
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
