"""
Unit tests for extract_board_token() in populate_api_urls.py.

Pure unit tests — no network, no file I/O.
Run with: pytest tests/test_extract_board_token.py -v
"""

import pytest
from populate_api_urls import extract_board_token


def test_standard_greenhouse_url():
    assert extract_board_token("https://job-boards.greenhouse.io/litify/") == "litify"

def test_standard_url_without_trailing_slash():
    assert extract_board_token("https://job-boards.greenhouse.io/amount") == "amount"

def test_eu_greenhouse_url():
    assert extract_board_token("https://job-boards.eu.greenhouse.io/bitly/") == "bitly"

def test_eu_url_without_trailing_slash():
    assert extract_board_token("https://job-boards.eu.greenhouse.io/consumerreports") == "consumerreports"

def test_custom_url_returns_none():
    assert extract_board_token("https://www.databricks.com/company/careers/open-positions") is None

def test_non_greenhouse_ats_returns_none():
    assert extract_board_token("https://jobs.ashbyhq.com/somecompany") is None

def test_empty_string_returns_none():
    assert extract_board_token("") is None

def test_malformed_url_returns_none():
    assert extract_board_token("not-a-url") is None

def test_url_with_query_string():
    # Query string is separate from path — token should still be extracted cleanly
    assert extract_board_token("https://job-boards.greenhouse.io/medrio?gh_src=something") == "medrio"

def test_never_raises_on_garbage_input():
    # Should return None, never raise
    for bad in [None, 123, "://broken", "   "]:
        try:
            result = extract_board_token(bad)
            assert result is None
        except Exception as e:
            pytest.fail(f"extract_board_token raised on input {bad!r}: {e}")
