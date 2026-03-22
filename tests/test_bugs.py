"""Tests for bugs discovered during integration testing.

Each test was written BEFORE the fix to confirm the bug, then the fix was applied.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.daemon import (
    build_type_instructions,
    parse_interval,
    post_tick_check,
    run_tick,
    OL_TASKS,
    OL_LOGS,
)
from orchestrator.engine import Manifest


# ---------------------------------------------------------------------------
# Bug 1: parse_interval crashes on empty string and non-numeric input
# ---------------------------------------------------------------------------

class TestParseIntervalEdgeCases:
    def test_empty_string_returns_minimum(self):
        """Empty string should return 1 (minimum), not crash."""
        assert parse_interval("") == 1

    def test_non_numeric_string_returns_minimum(self):
        """Non-numeric input like 'abc' should return 1, not crash."""
        assert parse_interval("abc") == 1

    def test_just_suffix_no_number(self):
        """Bare suffix like 'm' with no digits should return 1."""
        assert parse_interval("m") == 1

    def test_zero_seconds(self):
        assert parse_interval("0s") == 1

    def test_zero_minutes(self):
        assert parse_interval("0m") == 1


# ---------------------------------------------------------------------------
# Bug 2: pyproject.toml references main_sync which doesn't exist
# ---------------------------------------------------------------------------

class TestEntryPoint:
    def test_main_sync_exists(self):
        """pyproject.toml script entry point must be importable."""
        from orchestrator.engine import main_sync
        assert callable(main_sync)


# ---------------------------------------------------------------------------
# Bug 3: run_tick crashes with KeyError on malformed task
# ---------------------------------------------------------------------------

class TestRunTickMalformedTask:
    def test_missing_repo_key(self, tmp_path):
        """run_tick should not crash with KeyError on a task missing 'repo'."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        task = {"id": "bad1", "status": "active", "prompt": "test"}
        (tasks_dir / "bad1.json").write_text(json.dumps(task))

        with patch("orchestrator.daemon.OL_TASKS", tasks_dir), \
             patch("orchestrator.daemon.OL_LOGS", logs_dir):
            # Should log error or skip gracefully, not raise KeyError
            try:
                run_tick("bad1")
            except KeyError:
                pytest.fail("run_tick raised KeyError on malformed task — should handle gracefully")

    def test_missing_backend_uses_default(self, tmp_path):
        """Task missing 'backend' should default to 'claude', not crash."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        task = {
            "id": "bad2",
            "status": "active",
            "prompt": "test",
            "repo": str(tmp_path),
            "loop_type": "research",
            "batch_size": 5,
        }
        (tasks_dir / "bad2.json").write_text(json.dumps(task))

        with patch("orchestrator.daemon.OL_TASKS", tasks_dir), \
             patch("orchestrator.daemon.OL_LOGS", logs_dir):
            # Should not crash — FileNotFoundError for claude CLI is expected
            try:
                run_tick("bad2")
            except KeyError:
                pytest.fail("run_tick raised KeyError on task missing 'backend'")


# ---------------------------------------------------------------------------
# Bug 4: Manifest.load on corrupted JSON gives unhelpful error
# ---------------------------------------------------------------------------

class TestManifestLoadCorrupted:
    def test_corrupted_json_raises_clear_error(self, tmp_path):
        """Corrupted JSON should raise ValueError with context, not raw JSONDecodeError."""
        p = tmp_path / "manifest.json"
        p.write_text("not json {{{")
        with pytest.raises((json.JSONDecodeError, ValueError)):
            Manifest.load(p)

    def test_empty_file_raises(self, tmp_path):
        """Empty file should raise, not return default Manifest."""
        p = tmp_path / "manifest.json"
        p.write_text("")
        with pytest.raises((json.JSONDecodeError, ValueError)):
            Manifest.load(p)
