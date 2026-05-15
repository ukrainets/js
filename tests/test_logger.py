"""
Unit tests for logger.py — _cleanup_old_logs() and start_log()/stop_log().

Run with: pytest tests/test_logger.py -v
"""

import os
import re
import time

from logger import _cleanup_old_logs, start_log, stop_log

# ── _cleanup_old_logs() ───────────────────────────────────────────────────────

def test_cleanup_deletes_files_older_than_retention(tmp_path):
    old = tmp_path / "2026.01.01_08-00-00_js_run.md"
    old.write_text("old log")
    old_mtime = time.time() - 31 * 86400
    os.utime(old, (old_mtime, old_mtime))

    _cleanup_old_logs(str(tmp_path), retention_days=30)

    assert not old.exists()


def test_cleanup_keeps_files_within_retention(tmp_path):
    recent = tmp_path / "2026.05.04_09-00-00_js_run.md"
    recent.write_text("recent log")

    _cleanup_old_logs(str(tmp_path), retention_days=30)

    assert recent.exists()


def test_cleanup_does_not_crash_on_missing_directory():
    _cleanup_old_logs("/tmp/nonexistent_js_logs_dir_xyz", retention_days=30)


# ── start_log() / stop_log() ──────────────────────────────────────────────────

def test_start_log_creates_file_with_correct_header(tmp_path):
    config = {"log_dir": str(tmp_path), "log_retention_days": 30}
    try:
        result = start_log(trigger="manual", config=config)
        assert result is True
        log_files = list(tmp_path.glob("*.md"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "**Trigger:** manual" in content
        assert "**Date:**" in content
        assert "**Start time:**" in content
    finally:
        stop_log()


def test_start_log_filename_contains_seconds(tmp_path):
    config = {"log_dir": str(tmp_path), "log_retention_days": 30}
    try:
        start_log(trigger="scheduler", config=config)
        log_files = list(tmp_path.glob("*.md"))
        assert len(log_files) == 1
        assert re.match(r"\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2}_js_run\.md", log_files[0].name)
    finally:
        stop_log()


def test_stop_log_closes_fenced_code_block(tmp_path):
    config = {"log_dir": str(tmp_path), "log_retention_days": 30}
    start_log(trigger="manual", config=config)
    stop_log()

    content = list(tmp_path.glob("*.md"))[0].read_text(encoding="utf-8")
    assert content.endswith("```\n")


def test_log_file_has_restricted_permissions(tmp_path):
    config = {"log_dir": str(tmp_path), "log_retention_days": 30}
    try:
        start_log(trigger="manual", config=config)
        log_files = list(tmp_path.glob("*.md"))
        assert len(log_files) == 1
        assert oct(os.stat(log_files[0]).st_mode)[-3:] == "600"
    finally:
        stop_log()


def test_log_dir_has_restricted_permissions(tmp_path):
    log_dir = tmp_path / "new_logs"
    config = {"log_dir": str(log_dir), "log_retention_days": 30}
    try:
        start_log(trigger="manual", config=config)
        assert oct(os.stat(log_dir).st_mode)[-3:] == "700"
    finally:
        stop_log()


def test_start_log_returns_false_on_error(tmp_path):
    existing_file = tmp_path / "not_a_dir.txt"
    existing_file.write_text("I am a file")
    config = {"log_dir": str(existing_file), "log_retention_days": 30}

    result = start_log(trigger="manual", config=config)
    stop_log()

    assert result is False
