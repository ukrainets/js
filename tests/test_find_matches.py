"""
Unit tests for normalize_text() and find_matches().

Pure unit tests — no Playwright, no network, no file I/O.
Run with: pytest tests/test_find_matches.py -v
"""

import pytest
from utils import normalize_text
from utils import find_matches


# ── normalize_text() ──────────────────────────────────────────────────────────

def test_normalize_strips_parentheses():
    assert normalize_text("Automation Engineer (Mid level SDET)") == "automation engineer"

def test_normalize_strips_square_brackets():
    assert normalize_text("QA Engineer [Automation]") == "qa engineer"

def test_normalize_strips_curly_braces():
    assert normalize_text("Test Engineer {Contract}") == "test engineer"

def test_normalize_strips_multiple_bracket_groups():
    assert normalize_text("Engineer (Senior) [Remote]") == "engineer"

def test_normalize_collapses_whitespace():
    assert normalize_text("  Sr.  QA   Engineer  ") == "sr. qa engineer"

def test_normalize_preserves_dots():
    assert normalize_text("Sr. QA Engineer") == "sr. qa engineer"

def test_normalize_preserves_commas():
    assert normalize_text("Software Engineer, SDET") == "software engineer, sdet"

def test_normalize_preserves_ampersand():
    assert normalize_text("QA & Automation Engineer") == "qa & automation engineer"

def test_normalize_preserves_hyphen():
    assert normalize_text("Full-Stack QA Engineer") == "full-stack qa engineer"

def test_normalize_empty_string():
    assert normalize_text("") == ""

def test_normalize_only_brackets():
    assert normalize_text("(Remote)") == ""

def test_normalize_nested_brackets():
    # Outer bracket pair is stripped; inner content may leave residue —
    # the outer strip removes "(Level (II))" as a group stopping at first ")"
    # then the remaining text is cleaned up. What matters is the base title survives.
    result = normalize_text("Engineer (Level (II))")
    assert "engineer" in result


# ── find_matches() ────────────────────────────────────────────────────────────

def test_medrio_bug_parenthetical_qualifier():
    """Regression: the bug that prompted this fix."""
    links  = [("Automation Engineer (Mid level SDET)", "https://example.com/job/1")]
    titles = ["Automation Engineer", "SDET"]
    result = find_matches(links, titles)
    assert len(result) == 1
    assert result[0][0] == "Automation Engineer"
    assert result[0][1] == "Automation Engineer (Mid level SDET)"   # scraped text preserved
    assert result[0][2] == "https://example.com/job/1"

def test_exact_match_still_works():
    links  = [("QA Engineer", "/job/1")]
    titles = ["QA Engineer"]
    assert find_matches(links, titles) == [("QA Engineer", "QA Engineer", "/job/1")]

def test_title_found_inside_longer_text():
    links  = [("Cloud Test Automation Engineer", "/job/1")]
    titles = ["Automation Engineer"]
    result = find_matches(links, titles)
    assert result == [("Automation Engineer", "Cloud Test Automation Engineer", "/job/1")]

def test_parenthetical_stripped_before_match():
    links  = [("SDET (Senior Level)", "/job/1")]
    titles = ["SDET"]
    assert find_matches(links, titles) == [("SDET", "SDET (Senior Level)", "/job/1")]

def test_case_insensitive():
    links  = [("qa automation engineer", "/job/1")]
    titles = ["QA Automation Engineer"]
    result = find_matches(links, titles)
    assert len(result) == 1
    assert result[0][0] == "QA Automation Engineer"
    assert result[0][1] == "qa automation engineer"                  # scraped text as-is
    assert result[0][2] == "/job/1"

def test_no_partial_word_match():
    """Word-boundary guard: "QA Lead" must not match inside "Squad Leader"."""
    links  = [("Squad Leader", "/job/1")]
    titles = ["QA Lead"]
    assert find_matches(links, titles) == []

def test_no_match_returns_empty():
    links  = [("Marketing Manager", "/job/1")]
    titles = ["QA Engineer"]
    assert find_matches(links, titles) == []

def test_dedup_by_url():
    """Two links with the same URL — only one match returned."""
    links  = [
        ("QA Engineer", "/job/1"),
        ("Senior QA Engineer", "/job/1"),
    ]
    titles = ["QA Engineer", "Senior QA Engineer"]
    result = find_matches(links, titles)
    assert len(result) == 1
    assert result[0][2] == "/job/1"

def test_multiple_links_multiple_matches():
    links  = [("QA Engineer", "/job/1"), ("SDET", "/job/2")]
    titles = ["QA Engineer", "SDET"]
    result = find_matches(links, titles)
    assert len(result) == 2
    urls = {r[2] for r in result}
    assert urls == {"/job/1", "/job/2"}

def test_empty_links():
    assert find_matches([], ["QA Engineer"]) == []

def test_empty_titles():
    assert find_matches([("QA Engineer", "/job/1")], []) == []

def test_real_world_comma_in_title():
    """Comma is preserved on both sides — exact comma title must match."""
    links  = [("Software Engineer, SDET", "/job/1")]
    titles = ["Software Engineer, SDET"]
    assert find_matches(links, titles) == [("Software Engineer, SDET", "Software Engineer, SDET", "/job/1")]
