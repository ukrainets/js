"""
Unit tests for scan_api() in crawlers/api_scanner.py.

Uses a stub extractor to isolate the generic engine from platform logic.
Run with: pytest tests/test_api_scanner.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from crawlers.api_scanner import scan_api

# ── Helpers ───────────────────────────────────────────────────────────────────

def stub_extractor(data: dict) -> list[tuple[str, str]]:
    """Returns whatever jobs list is in data as (title, url) tuples."""
    return [(j["title"], j["url"]) for j in data.get("jobs", [])]


def make_response(status: int, body: dict) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body
    return resp


def make_client(response: MagicMock) -> MagicMock:
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=response)
    return client


def make_semaphore() -> asyncio.Semaphore:
    return asyncio.Semaphore(10)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_found_is_returned():
    body   = {"jobs": [{"title": "QA Engineer", "url": "https://example.com/job/1"}]}
    client = make_client(make_response(200, body))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert len(results) == 1
    assert results[0]["match_title"] == "QA Engineer"
    assert results[0]["company_name"] == "Acme"
    mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_no_title_match_returns_empty():
    body   = {"jobs": [{"title": "Marketing Manager", "url": "https://example.com/job/1"}]}
    client = make_client(make_response(200, body))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_empty_jobs_returns_empty():
    client = make_client(make_response(200, {"jobs": []}))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_non_200_response_returns_empty():
    client = make_client(make_response(404, {}))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_network_error_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_timeout_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_malformed_response_returns_empty():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.side_effect = ValueError("bad json")
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=resp)
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_url_not_written_again():
    body = {"jobs": [{"title": "QA Engineer", "url": "https://example.com/job/1"}]}
    client = make_client(make_response(200, body))
    write_lock = asyncio.Lock()
    known_urls = {"https://example.com/job/1"}

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub",
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_on_match_callback_invoked():
    body = {"jobs": [{"title": "QA Engineer", "url": "https://example.com/job/1"}]}
    client = make_client(make_response(200, body))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()
    callback = MagicMock()

    with patch("crawlers.api_scanner.append_match_row"):
        await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub", on_match=callback,
        )

    callback.assert_called_once_with("Acme", "QA Engineer", "QA Engineer", "https://example.com/job/1")


@pytest.mark.asyncio
async def test_on_match_none_does_not_crash():
    body = {"jobs": [{"title": "QA Engineer", "url": "https://example.com/job/1"}]}
    client = make_client(make_response(200, body))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_scanner.append_match_row"):
        results = await scan_api(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
            extractor=stub_extractor, platform_label="Stub", on_match=None,
        )

    assert len(results) == 1
