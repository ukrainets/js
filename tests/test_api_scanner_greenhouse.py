"""
Integration tests for scan_api() wired with the Greenhouse extractor.

Verifies the full Greenhouse path end-to-end using the generic scanner.
Run with: pytest tests/test_api_scanner_greenhouse.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from crawlers.api_scanner import scan_api
from crawlers.api_greenhouse import extract_greenhouse_jobs


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


def run_scan(client, jobs_payload, titles, known_urls=None, on_match=None):
    """Convenience wrapper that runs scan_api with the Greenhouse extractor."""
    return scan_api(
        client, make_semaphore(), "Acme", "https://api.example.com/jobs",
        titles, "data/match.csv", asyncio.Lock(), known_urls or set(),
        extractor=extract_greenhouse_jobs, platform_label="Greenhouse",
        on_match=on_match,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_found_is_returned():
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, jobs, ["QA Engineer"])

    assert len(results) == 1
    assert results[0]["match_title"] == "QA Engineer"
    assert results[0]["company_name"] == "Acme"
    mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_no_title_match_returns_empty():
    jobs = [{"title": "Marketing Manager", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, jobs, ["QA Engineer"])

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_empty_jobs_list_returns_empty():
    client = make_client(make_response(200, []))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, [], ["QA Engineer"])

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_non_200_response_returns_empty():
    client = make_client(make_response(404, []))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, [], ["QA Engineer"])

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_network_error_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.ConnectError("unreachable"))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, [], ["QA Engineer"])

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_timeout_returns_empty():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, [], ["QA Engineer"])

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_url_not_written_again():
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    known_urls = {"https://example.com/job/1"}

    with patch("crawlers.api_scanner.append_match_row") as mock_write:
        results = await run_scan(client, jobs, ["QA Engineer"], known_urls=known_urls)

    assert results == []
    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_on_match_callback_invoked():
    jobs = [{"title": "QA Engineer", "absolute_url": "https://example.com/job/1"}]
    client = make_client(make_response(200, jobs))
    callback = MagicMock()

    with patch("crawlers.api_scanner.append_match_row"):
        await run_scan(client, jobs, ["QA Engineer"], on_match=callback)

    callback.assert_called_once_with("Acme", "QA Engineer", "QA Engineer", "https://example.com/job/1")
