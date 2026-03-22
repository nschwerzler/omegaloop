"""Tests for SessionManager — session CRUD, discover, checkpoint."""

import json
from pathlib import Path

from orchestrator.engine import SessionManager, Manifest, MACHINE_ID, Status


class TestSessionCreate:
    def test_create_session(self, session_manager, tmp_git_repo):
        m = session_manager.create_session("Test optimization", max_experiments=20)

        assert m.session_id is not None
        assert MACHINE_ID in m.session_id
        assert m.research_prompt == "Test optimization"
        assert m.max_experiments == 20
        assert m.status == Status.ANALYZING
        assert m.machine_id == MACHINE_ID
        assert MACHINE_ID in m.machines_involved

    def test_creates_folder_structure(self, session_manager, tmp_git_repo):
        m = session_manager.create_session("Test prompt")
        ol_dir = tmp_git_repo / "OmegaLoop" / m.session_id

        assert ol_dir.exists()
        assert (ol_dir / "manifest.json").exists()
        assert (ol_dir / "research-prompt.md").exists()
        assert (ol_dir / "logs").is_dir()
        assert (ol_dir / "wins").is_dir()
        assert (ol_dir / "checkpoints").is_dir()

    def test_creates_worktree(self, session_manager, git_ops):
        m = session_manager.create_session("Test prompt")
        assert git_ops.worktree_exists(m.session_id)

    def test_manifest_committed_to_git(self, session_manager, git_ops):
        m = session_manager.create_session("Test prompt")
        log = git_ops.run("log", "--oneline", "-1")
        assert "OL: init" in log

    def test_unique_session_ids(self, session_manager):
        """Two sessions created in sequence should have different IDs."""
        m1 = session_manager.create_session("Prompt A")
        m2 = session_manager.create_session("Prompt B")
        assert m1.session_id != m2.session_id


class TestSessionLoad:
    def test_load_session(self, session_manager):
        m = session_manager.create_session("Load test")
        loaded = session_manager.load_session(m.session_id)

        assert loaded is not None
        assert loaded.session_id == m.session_id
        assert loaded.research_prompt == "Load test"

    def test_load_nonexistent(self, session_manager):
        loaded = session_manager.load_session("nonexistent-session-id")
        assert loaded is None


class TestSessionDiscover:
    def test_discover_all(self, session_manager):
        session_manager.create_session("Session 1")
        session_manager.create_session("Session 2")

        sessions = session_manager.discover_sessions()
        assert len(sessions) >= 2

    def test_discover_by_status(self, session_manager, tmp_git_repo):
        m1 = session_manager.create_session("Active session")
        m2 = session_manager.create_session("Completed session")

        # Mark m2 as completed
        ol_dir = tmp_git_repo / "OmegaLoop" / m2.session_id
        m2.status = Status.COMPLETED
        m2.save(ol_dir / "manifest.json")

        resumable = session_manager.discover_resumable()
        session_ids = [m.session_id for m in resumable]
        assert m1.session_id in session_ids
        assert m2.session_id not in session_ids

    def test_discover_empty_repo(self, session_manager):
        sessions = session_manager.discover_sessions()
        assert sessions == []


class TestCheckpoint:
    def test_checkpoint_updates_timestamp(self, session_manager, tmp_git_repo):
        m = session_manager.create_session("Checkpoint test")
        old_checkpoint = m.last_checkpoint

        session_manager.checkpoint(m)
        assert m.last_checkpoint is not None
        assert m.last_checkpoint != old_checkpoint

    def test_checkpoint_commits_to_git(self, session_manager, git_ops):
        m = session_manager.create_session("Checkpoint test")
        m.experiment_count = 5
        session_manager.checkpoint(m)

        log = git_ops.run("log", "--oneline", "-1")
        assert "checkpoint" in log.lower()

    def test_checkpoint_preserves_data(self, session_manager, tmp_git_repo):
        m = session_manager.create_session("Preserve test")
        m.experiment_count = 10
        m.win_count = 3
        m.insights.append("Test insight")
        session_manager.checkpoint(m)

        # Reload and verify
        loaded = session_manager.load_session(m.session_id)
        assert loaded.experiment_count == 10
        assert loaded.win_count == 3
        assert "Test insight" in loaded.insights
