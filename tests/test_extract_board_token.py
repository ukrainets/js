"""
Unit tests for extract_board_token() in populate_api_urls.py.

Pure unit tests — no network, no file I/O.
Run with: pytest tests/test_extract_board_token.py -v
"""

import pytest

from populate_api_urls import extract_board_token

# ── Greenhouse ────────────────────────────────────────────────────────────────

def test_standard_greenhouse_url():
    assert extract_board_token("https://job-boards.greenhouse.io/litify/", "greenhouse") == "litify"

def test_standard_url_without_trailing_slash():
    assert extract_board_token("https://job-boards.greenhouse.io/amount", "greenhouse") == "amount"

def test_eu_greenhouse_url():
    assert extract_board_token("https://job-boards.eu.greenhouse.io/bitly/", "greenhouse") == "bitly"

def test_eu_url_without_trailing_slash():
    assert extract_board_token("https://job-boards.eu.greenhouse.io/consumerreports", "greenhouse") == "consumerreports"

def test_url_with_query_string():
    assert extract_board_token("https://job-boards.greenhouse.io/medrio?gh_src=something", "greenhouse") == "medrio"

def test_ashby_url_with_greenhouse_platform_returns_none():
    assert extract_board_token("https://jobs.ashbyhq.com/somecompany", "greenhouse") is None

def test_custom_url_returns_none():
    assert extract_board_token("https://www.databricks.com/company/careers/open-positions", "greenhouse") is None


# ── Ashby ─────────────────────────────────────────────────────────────────────

def test_standard_ashby_url():
    assert extract_board_token("https://jobs.ashbyhq.com/airtable", "ashby") == "airtable"

def test_ashby_url_with_trailing_slash():
    assert extract_board_token("https://jobs.ashbyhq.com/1password/", "ashby") == "1password"

def test_ashby_url_without_trailing_slash():
    assert extract_board_token("https://jobs.ashbyhq.com/netgear", "ashby") == "netgear"

def test_greenhouse_url_with_ashby_platform_returns_none():
    assert extract_board_token("https://job-boards.greenhouse.io/somecompany", "ashby") is None


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_string_returns_none():
    assert extract_board_token("", "greenhouse") is None

def test_malformed_url_returns_none():
    assert extract_board_token("not-a-url", "greenhouse") is None

def test_unknown_platform_returns_none():
    assert extract_board_token("https://job-boards.greenhouse.io/acme", "lever") is None

def test_never_raises_on_garbage_input():
    for bad in [None, 123, "://broken", "   "]:
        try:
            result = extract_board_token(bad, "greenhouse")
            assert result is None
        except Exception as e:
            pytest.fail(f"extract_board_token raised on input {bad!r}: {e}")
