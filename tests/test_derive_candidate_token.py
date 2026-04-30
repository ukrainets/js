"""
Unit tests for derive_candidate_token() and probe_greenhouse_api()
in populate_api_urls.py.

Run with: pytest tests/test_derive_candidate_token.py -v
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from populate_api_urls import derive_candidate_token, probe_greenhouse_api


# ── derive_candidate_token ────────────────────────────────────────────────────

def test_simple_name():
    assert derive_candidate_token("Upwork") == "upwork"

def test_name_with_space():
    assert derive_candidate_token("Vivid Seats") == "vividseats"

def test_name_with_punctuation():
    assert derive_candidate_token("Yum! Brands") == "yumbrands"

def test_name_already_lowercase():
    assert derive_candidate_token("webflow") == "webflow"

def test_name_with_dots_and_commas():
    assert derive_candidate_token("Caterpillar Inc.") == "caterpillarinc"

def test_name_with_ampersand():
    assert derive_candidate_token("Tom & Jerry Co.") == "tomjerryco"

def test_numbers_preserved():
    assert derive_candidate_token("1Password") == "1password"

def test_empty_string_returns_empty():
    assert derive_candidate_token("") == ""

def test_only_special_chars_returns_empty():
    assert derive_candidate_token("!!! ---") == ""

def test_mixed_case():
    assert derive_candidate_token("OpenAI") == "openai"


# ── probe_greenhouse_api ──────────────────────────────────────────────────────

def test_probe_returns_true_on_200():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_greenhouse_api("upwork") is True

def test_probe_returns_false_on_404():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_greenhouse_api("doesnotexist") is False

def test_probe_returns_false_on_network_error():
    with patch("populate_api_urls.httpx.get", side_effect=httpx.ConnectError("unreachable")):
        assert probe_greenhouse_api("upwork") is False

def test_probe_returns_false_on_timeout():
    with patch("populate_api_urls.httpx.get", side_effect=httpx.TimeoutException("timed out")):
        assert probe_greenhouse_api("upwork") is False

def test_probe_uses_correct_url():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    with patch("populate_api_urls.httpx.get", return_value=mock_resp) as mock_get:
        probe_greenhouse_api("webflow")
    mock_get.assert_called_once_with(
        "https://boards-api.greenhouse.io/v1/boards/webflow/jobs",
        timeout=10.0,
        follow_redirects=True,
    )
