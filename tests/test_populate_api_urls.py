"""
Unit tests for populate_api_urls.run() — focuses on robustness against
malformed CSV rows where DictReader fills missing columns with None.

Run with: pytest tests/test_populate_api_urls.py -v
"""

import csv
from unittest.mock import MagicMock, patch

import httpx

from populate_api_urls import run, validate_url


def write_csv(path, rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


HEADER = ["id", "rating", "company_name", "website", "open_positions_url",
          "hr_platform", "no_click", "comment", "field", "api_url"]


def test_run_does_not_crash_on_short_row(tmp_path):
    # A row with fewer columns than the header causes DictReader to fill
    # missing fields with None. run() must handle this without AttributeError.
    input_csv  = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"

    write_csv(input_csv, [
        HEADER,
        # Full valid Ashby row
        ["id1", "5", "Airtable", "airtable.com", "https://jobs.ashbyhq.com/airtable", "Ashby", "TRUE", "", "", ""],
        # Short row — hr_platform, no_click, comment, field, api_url all missing → None
        ["id2", "5", "ShortRow Corp", "", "https://example.com/jobs"],
    ])

    run(input_path=str(input_csv), output_path=str(output_csv), validate=False)

    with open(output_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    airtable = next(r for r in rows if r["company_name"] == "Airtable")
    assert airtable["api_url"] == "https://api.ashbyhq.com/posting-api/job-board/airtable"

    short_row = next(r for r in rows if r["company_name"] == "ShortRow Corp")
    assert short_row["api_url"] == ""


# ── validate_url() ────────────────────────────────────────────────────────────

def test_validate_url_returns_true_on_https_destination():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.url = "https://example.com/jobs"
    with patch("populate_api_urls.httpx.head", return_value=mock_resp):
        assert validate_url("https://example.com/jobs") is True

def test_validate_url_returns_false_when_redirected_to_http():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.url = "http://example.com/jobs"
    with patch("populate_api_urls.httpx.head", return_value=mock_resp):
        assert validate_url("https://example.com/jobs") is False

def test_validate_url_returns_false_on_4xx():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.url = "https://example.com/jobs"
    with patch("populate_api_urls.httpx.head", return_value=mock_resp):
        assert validate_url("https://example.com/jobs") is False

def test_validate_url_returns_false_on_network_error():
    with patch("populate_api_urls.httpx.head", side_effect=httpx.ConnectError("unreachable")):
        assert validate_url("https://example.com/jobs") is False


# ── run() ─────────────────────────────────────────────────────────────────────

def test_run_does_not_crash_on_none_hr_platform(tmp_path):
    # Explicitly test that a None hr_platform value (missing column) is treated
    # as an unknown platform and silently skipped — not a crash.
    input_csv  = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"

    write_csv(input_csv, [
        HEADER,
        ["id1", "5", "NoPlatform Corp", "", "https://example.com/jobs"],
    ])

    run(input_path=str(input_csv), output_path=str(output_csv), validate=False)

    with open(output_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["api_url"] == ""
