"""Tests for daemon — parsing, scheduling, type detection, termination logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.daemon import (
    parse_interval,
    interval_to_cron,
    infer_loop_type,
    gen_task_id,
    post_tick_check,
)


class TestParseInterval:
    def test_minutes(self):
        assert parse_interval("10m") == 10
        assert parse_interval("1m") == 1
        assert parse_interval("60m") == 60

    def test_hours(self):
        assert parse_interval("1h") == 60
        assert parse_interval("6h") == 360
        assert parse_interval("24h") == 1440

    def test_days(self):
        assert parse_interval("1d") == 1440
        assert parse_interval("2d") == 2880

    def test_seconds_rounds_up(self):
        assert parse_interval("30s") == 1  # rounds up to 1 minute
        assert parse_interval("90s") == 2  # 90s = 1.5min → 2
        assert parse_interval("120s") == 2

    def test_bare_number_is_minutes(self):
        assert parse_interval("15") == 15

    def test_minimum_is_1(self):
        assert parse_interval("0m") == 1
        assert parse_interval("0s") == 1

    def test_whitespace_stripped(self):
        assert parse_interval("  10m  ") == 10

    def test_case_insensitive(self):
        assert parse_interval("10M") == 10
        assert parse_interval("1H") == 60


class TestIntervalToCron:
    def test_minutes(self):
        assert interval_to_cron(5) == "*/5 * * * *"
        assert interval_to_cron(10) == "*/10 * * * *"
        assert interval_to_cron(30) == "*/30 * * * *"

    def test_hours(self):
        assert interval_to_cron(60) == "0 */1 * * *"
        assert interval_to_cron(120) == "0 */2 * * *"
        assert interval_to_cron(360) == "0 */6 * * *"

    def test_days(self):
        assert interval_to_cron(1440) == "0 0 */1 * *"


class TestInferLoopType:
    def test_monitor_keywords(self):
        assert infer_loop_type("Monitor PR #1234 for new comments") == "monitor"
        assert infer_loop_type("Watch for build failures") == "monitor"
        assert infer_loop_type("Check for updates and enrich the doc") == "monitor"
        assert infer_loop_type("If you see a new comment, update the doc") == "monitor"
        assert infer_loop_type("Once a day, check the status") == "monitor"

    def test_converge_keywords(self):
        assert infer_loop_type("Test, find bugs, TDD fix, until all tests pass") == "converge"
        assert infer_loop_type("Fix the bug and write a test") == "converge"
        assert infer_loop_type("Target: under 200ms response time") == "converge"
        assert infer_loop_type("Keep going until green") == "converge"

    def test_optimize_keywords(self):
        assert infer_loop_type("Improve load time of the dashboard") == "optimize"
        assert infer_loop_type("Make the API faster") == "optimize"
        assert infer_loop_type("Optimize memory usage") == "optimize"
        assert infer_loop_type("Benchmark and reduce latency") == "optimize"

    def test_research_default(self):
        assert infer_loop_type("Find a headless browser solution") == "research"
        assert infer_loop_type("Create a design.md for the auth system") == "research"
        assert infer_loop_type("Explore approaches to real-time notifications") == "research"

    def test_case_insensitive(self):
        assert infer_loop_type("MONITOR the PR") == "monitor"
        assert infer_loop_type("OPTIMIZE the cache") == "optimize"


class TestGenTaskId:
    def test_returns_8_chars(self):
        tid = gen_task_id("/repo", "prompt")
        assert len(tid) == 8

    def test_hex_string(self):
        tid = gen_task_id("/repo", "prompt")
        assert all(c in "0123456789abcdef" for c in tid)

    def test_different_inputs_differ(self):
        t1 = gen_task_id("/repo1", "prompt1")
        t2 = gen_task_id("/repo2", "prompt2")
        assert t1 != t2


class TestPostTickCheck:
    def test_converge_increments_streak(self):
        task = {"loop_type": "converge", "done_streak": 0, "done_streak_target": 3}
        manifest = {"converge_history": [5, 3, 1, 0]}
        post_tick_check(task, manifest, "")
        assert task["done_streak"] == 1

    def test_converge_resets_streak_on_failure(self):
        task = {"loop_type": "converge", "done_streak": 2, "done_streak_target": 3}
        manifest = {"converge_history": [5, 3, 1, 2]}  # not zero
        post_tick_check(task, manifest, "")
        assert task["done_streak"] == 0

    def test_converge_empty_history_no_crash(self):
        task = {"loop_type": "converge", "done_streak": 0, "done_streak_target": 3}
        manifest = {"converge_history": []}
        post_tick_check(task, manifest, "")
        assert task["done_streak"] == 0

    def test_monitor_tracks_no_change(self):
        task = {"loop_type": "monitor", "no_change_streak": 0, "_last_enrichment_count": 5}
        manifest = {"enrichment_count": 5}  # no change
        post_tick_check(task, manifest, "")
        assert task["no_change_streak"] == 1

    def test_monitor_resets_on_enrichment(self):
        task = {"loop_type": "monitor", "no_change_streak": 3, "_last_enrichment_count": 5}
        manifest = {"enrichment_count": 6}  # new enrichment
        post_tick_check(task, manifest, "")
        assert task["no_change_streak"] == 0

    def test_optimize_noop(self):
        task = {"loop_type": "optimize"}
        manifest = {}
        post_tick_check(task, manifest, "")  # should not crash

    def test_research_noop(self):
        task = {"loop_type": "research"}
        manifest = {}
        post_tick_check(task, manifest, "")  # should not crash
