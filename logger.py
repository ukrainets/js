"""
Scan run logger — mirrors all stdout to a per-run markdown file via a Tee pattern.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

_original_stdout = None
_log_file = None


class _Tee:
    def __init__(self, original, log_file):
        self._original = original
        self._log_file = log_file

    def write(self, data):
        self._original.write(data)
        self._log_file.write(data)

    def flush(self):
        self._original.flush()
        self._log_file.flush()

    def fileno(self):
        return self._original.fileno()


def start_log(trigger: str, config: dict) -> bool:
    global _original_stdout, _log_file
    try:
        log_dir = config.get("log_dir", "logs")
        retention_days = config.get("log_retention_days", 30)

        _cleanup_old_logs(log_dir, retention_days)

        Path(log_dir).mkdir(parents=True, exist_ok=True, mode=0o700)

        now = datetime.now()
        filename = now.strftime("%Y.%m.%d_%H-%M-%S") + "_js_run.md"
        log_path = os.path.join(log_dir, filename)

        _log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        os.chmod(log_path, 0o600)
        _log_file.write("# JS Run Log\n")
        _log_file.write(f"**Date:** {now.strftime('%Y.%m.%d')}\n")
        _log_file.write(f"**Start time:** {now.strftime('%H:%M')}\n")
        _log_file.write(f"**Trigger:** {trigger}\n\n")
        _log_file.write("---\n\n")
        _log_file.write("```\n")

        _original_stdout = sys.stdout
        sys.stdout = _Tee(_original_stdout, _log_file)
        return True
    except Exception as e:
        print(f"⚠️  Logging unavailable: {e}")
        return False


def stop_log() -> None:
    global _original_stdout, _log_file
    if _log_file is None:
        return
    try:
        _log_file.write("```\n")
        _log_file.close()
    except Exception:
        pass
    finally:
        if _original_stdout is not None:
            sys.stdout = _original_stdout
        _original_stdout = None
        _log_file = None


def _cleanup_old_logs(log_dir: str, retention_days: int) -> None:
    log_path = Path(log_dir)
    if not log_path.exists():
        return
    cutoff = time.time() - retention_days * 86400
    for f in log_path.glob("*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except Exception:
            pass
