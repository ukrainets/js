"""
Unit tests for scan_greenhouse() in crawlers/api_greenhouse.py.

Uses unittest.mock to avoid real HTTP calls.
Run with: pytest tests/test_scan_greenhouse.py -v
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from crawlers.api_greenhouse import scan_greenhouse


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_response(status: int, jobs: list[dict]) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = {"jobs": jobs}
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
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert len(results) == 1
    assert results[0]["match_title"] == "QA Engineer"
    assert results[0]["company_name"] == "Acme"
    mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_no_title_match_returns_empty():
    jobs = [{"title": "Marketing Manager", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_empty_jobs_list_returns_empty():
    client = make_client(make_response(200, []))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_non_200_response_returns_empty():
    client = make_client(make_response(404, []))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_network_error_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_timeout_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_url_not_written_again():
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    write_lock = asyncio.Lock()
    known_urls = {"https://example.com/job/1"}  # already seen

    with patch("crawlers.api_greenhouse.append_match_row") as mock_write:
        results = await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls,
        )

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_on_match_callback_invoked():
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    write_lock = asyncio.Lock()
    known_urls: set[str] = set()
    callback = MagicMock()

    with patch("crawlers.api_greenhouse.append_match_row"):
        await scan_greenhouse(
            client, make_semaphore(), "Acme", "https://api.example.com/jobs",
            ["QA Engineer"], "data/match.csv", write_lock, known_urls, on_match=callback,
        )

    callback.assert_called_once_with("Acme", "QA Engineer", "QA Engineer", "https://example.com/job/1")
