"""Tests for hang prevention: lockfiles, heartbeats, timeouts, safe JSON parsing."""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.daemon import (
    acquire_tick_lock,
    release_tick_lock,
    write_heartbeat,
    clear_heartbeat,
    cmd_status,
    _lock_path,
    _heartbeat_path,
    OL_LOCKS,
    OL_HEARTBEATS,
    TICK_TIMEOUT_SECONDS,
)
from orchestrator.engine import _safe_parse_agent_json


# ---------------------------------------------------------------------------
# Tick lock tests
# ---------------------------------------------------------------------------

class TestTickLock:
    def test_acquire_returns_true_when_no_lock(self, tmp_path):
        with patch("orchestrator.daemon.OL_LOCKS", tmp_path / "locks"):
            assert acquire_tick_lock("test1") is True

    def test_acquire_returns_false_when_locked_by_self(self, tmp_path):
        locks = tmp_path / "locks"
        with patch("orchestrator.daemon.OL_LOCKS", locks):
            assert acquire_tick_lock("test2") is True
            # Same PID, still running = locked
            assert acquire_tick_lock("test2") is False

    def test_release_removes_lock(self, tmp_path):
        locks = tmp_path / "locks"
        with patch("orchestrator.daemon.OL_LOCKS", locks):
            acquire_tick_lock("test3")
            lock = locks / "test3.lock"
            assert lock.exists()
            release_tick_lock("test3")
            assert not lock.exists()

    def test_stale_lock_from_dead_pid(self, tmp_path):
        locks = tmp_path / "locks"
        locks.mkdir(parents=True)
        lock_file = locks / "test4.lock"
        # Write a lock with a PID that definitely doesn't exist
        lock_file.write_text(json.dumps({
            "pid": 99999999,
            "started_at": time.time() - 100,
            "machine_id": "test",
        }))
        with patch("orchestrator.daemon.OL_LOCKS", locks):
            # Should acquire since PID is dead
            assert acquire_tick_lock("test4") is True

    def test_stale_lock_from_timeout(self, tmp_path):
        locks = tmp_path / "locks"
        locks.mkdir(parents=True)
        lock_file = locks / "test5.lock"
        # Lock from current PID but very old
        lock_file.write_text(json.dumps({
            "pid": os.getpid(),
            "started_at": time.time() - TICK_TIMEOUT_SECONDS - 100,
            "machine_id": "test",
        }))
        with patch("orchestrator.daemon.OL_LOCKS", locks):
            assert acquire_tick_lock("test5") is True

    def test_corrupted_lock_file_allows_acquire(self, tmp_path):
        locks = tmp_path / "locks"
        locks.mkdir(parents=True)
        (locks / "test6.lock").write_text("not json {{{")
        with patch("orchestrator.daemon.OL_LOCKS", locks):
            assert acquire_tick_lock("test6") is True


# ---------------------------------------------------------------------------
# Heartbeat tests
# ---------------------------------------------------------------------------

class TestHeartbeat:
    def test_write_and_read(self, tmp_path):
        with patch("orchestrator.daemon.OL_HEARTBEATS", tmp_path / "hb"):
            write_heartbeat("hb1", "running", "test detail")
            hb = json.loads((tmp_path / "hb" / "hb1.json").read_text())
            assert hb["phase"] == "running"
            assert hb["detail"] == "test detail"
            assert hb["task_id"] == "hb1"
            assert "timestamp" in hb

    def test_clear_removes_file(self, tmp_path):
        hb_dir = tmp_path / "hb"
        with patch("orchestrator.daemon.OL_HEARTBEATS", hb_dir):
            write_heartbeat("hb2", "running")
            assert (hb_dir / "hb2.json").exists()
            clear_heartbeat("hb2")
            assert not (hb_dir / "hb2.json").exists()

    def test_clear_nonexistent_no_error(self, tmp_path):
        with patch("orchestrator.daemon.OL_HEARTBEATS", tmp_path / "hb"):
            clear_heartbeat("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# Safe JSON parsing tests
# ---------------------------------------------------------------------------

class TestSafeParseAgentJson:
    def test_valid_json(self):
        result = _safe_parse_agent_json('{"hypothesis": "test", "result": "win"}')
        assert result["hypothesis"] == "test"
        assert result["result"] == "win"

    def test_json_in_markdown_fences(self):
        text = '```json\n{"hypothesis": "test", "result": "win"}\n```'
        result = _safe_parse_agent_json(text)
        assert result["hypothesis"] == "test"

    def test_json_with_preamble(self):
        text = 'Here is my result:\n{"hypothesis": "test", "result": "discard"}\nDone.'
        result = _safe_parse_agent_json(text)
        assert result["hypothesis"] == "test"

    def test_non_json_returns_error(self):
        result = _safe_parse_agent_json("I don't know what to do")
        assert result["result"] == "error"
        assert "non-JSON" in result["hypothesis"]

    def test_empty_string_returns_error(self):
        result = _safe_parse_agent_json("")
        assert result["result"] == "error"

    def test_partial_json_returns_error(self):
        result = _safe_parse_agent_json('{"hypothesis": "test"')
        assert result["result"] == "error"

    def test_truncates_long_raw_output(self):
        long_text = "x" * 1000
        result = _safe_parse_agent_json(long_text)
        assert len(result["reasoning"]) <= 520  # "Raw output: " prefix + 500 chars


# ---------------------------------------------------------------------------
# Run-tick lock integration
# ---------------------------------------------------------------------------

class TestRunTickLock:
    def test_run_tick_skips_when_locked(self, tmp_path, capsys):
        """run_tick should skip if another tick holds the lock."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        locks_dir = tmp_path / "locks"
        locks_dir.mkdir()

        task = {"id": "locked1", "status": "active", "prompt": "test", "repo": str(tmp_path)}
        (tasks_dir / "locked1.json").write_text(json.dumps(task))

        # Pre-create a lock from current PID (simulating active tick)
        (locks_dir / "locked1.lock").write_text(json.dumps({
            "pid": os.getpid(),
            "started_at": time.time(),
            "machine_id": "test",
        }))

        from orchestrator.daemon import run_tick
        with patch("orchestrator.daemon.OL_TASKS", tasks_dir), \
             patch("orchestrator.daemon.OL_LOGS", logs_dir), \
             patch("orchestrator.daemon.OL_LOCKS", locks_dir):
            run_tick("locked1")

        captured = capsys.readouterr()
        assert "already running" in captured.out
