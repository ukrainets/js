"""
Unit tests for derive_candidate_token() and probe_api()
in populate_api_urls.py.

Run with: pytest tests/test_derive_candidate_token.py -v
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from populate_api_urls import derive_candidate_token, probe_api

# ── derive_candidate_token ────────────────────────────────────────────────────

def test_standard_com_domain():
    assert derive_candidate_token("https://www.upwork.com") == "upwork"

def test_www_stripped():
    assert derive_candidate_token("https://www.webflow.com") == "webflow"

def test_no_www():
    assert derive_candidate_token("https://webflow.com") == "webflow"

def test_co_tld():
    assert derive_candidate_token("https://yello.co") == "yello"

def test_short_co_tld():
    assert derive_candidate_token("https://zip.co") == "zip"

def test_compound_sld():
    assert derive_candidate_token("https://www.vendhq.com") == "vendhq"

def test_vibes():
    assert derive_candidate_token("https://www.vibes.com") == "vibes"

def test_no_scheme():
    assert derive_candidate_token("upwork.com") == "upwork"

def test_empty_string_returns_empty():
    assert derive_candidate_token("") == ""

def test_invalid_url_returns_empty():
    assert derive_candidate_token("not-a-url") == ""

def test_never_raises_on_garbage():
    for bad in [None, 123, "://broken"]:
        try:
            result = derive_candidate_token(bad)
            assert result == ""
        except Exception as e:
            pytest.fail(f"derive_candidate_token raised on {bad!r}: {e}")


# ── probe_api ─────────────────────────────────────────────────────────────────

def test_probe_returns_true_on_200_greenhouse():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.url = "https://boards-api.greenhouse.io/v1/boards/upwork/jobs"
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_api("upwork", "greenhouse") is True

def test_probe_returns_false_on_404_greenhouse():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_api("doesnotexist", "greenhouse") is False

def test_probe_returns_true_on_200_ashby():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.url = "https://api.ashbyhq.com/posting-api/job-board/airtable"
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_api("airtable", "ashby") is True

def test_probe_returns_false_on_404_ashby():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_api("doesnotexist", "ashby") is False

def test_probe_returns_false_on_network_error():
    with patch("populate_api_urls.httpx.get", side_effect=httpx.ConnectError("unreachable")):
        assert probe_api("upwork", "greenhouse") is False

def test_probe_returns_false_on_timeout():
    with patch("populate_api_urls.httpx.get", side_effect=httpx.TimeoutException("timed out")):
        assert probe_api("upwork", "greenhouse") is False

def test_probe_uses_correct_greenhouse_url():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    with patch("populate_api_urls.httpx.get", return_value=mock_resp) as mock_get:
        probe_api("webflow", "greenhouse")
    mock_get.assert_called_once_with(
        "https://boards-api.greenhouse.io/v1/boards/webflow/jobs",
        timeout=10.0,
        follow_redirects=True,
    )

def test_probe_uses_correct_ashby_url():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    with patch("populate_api_urls.httpx.get", return_value=mock_resp) as mock_get:
        probe_api("airtable", "ashby")
    mock_get.assert_called_once_with(
        "https://api.ashbyhq.com/posting-api/job-board/airtable",
        timeout=10.0,
        follow_redirects=True,
    )

def test_probe_returns_false_for_unknown_platform():
    assert probe_api("sometoken", "lever") is False

def test_probe_returns_false_when_redirected_to_http():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.url = "http://boards-api.greenhouse.io/v1/boards/upwork/jobs"
    with patch("populate_api_urls.httpx.get", return_value=mock_resp):
        assert probe_api("upwork", "greenhouse") is False
