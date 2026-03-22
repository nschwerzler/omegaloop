"""Tests for GitOps — worktree lifecycle, commit, revert."""

import subprocess
from pathlib import Path

from orchestrator.engine import GitOps


class TestGitOpsBasic:
    def test_repo_name(self, git_ops, tmp_git_repo):
        assert git_ops.repo_name == tmp_git_repo.name

    def test_current_branch(self, git_ops):
        # Git init creates 'main' or 'master' depending on config
        branch = git_ops.current_branch
        assert branch in ("main", "master")

    def test_is_clean(self, git_ops, tmp_git_repo):
        assert git_ops.is_clean()
        (tmp_git_repo / "dirty.txt").write_text("dirty")
        assert not git_ops.is_clean()

    def test_short_hash(self, git_ops):
        h = git_ops.short_hash()
        assert len(h) == 7
        assert all(c in "0123456789abcdef" for c in h)


class TestWorktrees:
    def test_create_worktree(self, git_ops, tmp_git_repo):
        session_id = "20260322-test-a3f91b-0001"
        wt_path = git_ops.create_worktree(session_id, git_ops.current_branch)

        assert wt_path.exists()
        assert (wt_path / "README.md").exists()
        assert wt_path == git_ops.worktree_dir() / session_id

    def test_worktree_exists(self, git_ops):
        session_id = "20260322-test-a3f91b-0002"
        assert not git_ops.worktree_exists(session_id)

        git_ops.create_worktree(session_id, git_ops.current_branch)
        assert git_ops.worktree_exists(session_id)

    def test_create_worktree_idempotent(self, git_ops):
        """Creating same worktree twice should not error."""
        session_id = "20260322-test-a3f91b-0003"
        wt1 = git_ops.create_worktree(session_id, git_ops.current_branch)
        wt2 = git_ops.create_worktree(session_id, git_ops.current_branch)
        assert wt1 == wt2

    def test_remove_worktree(self, git_ops):
        session_id = "20260322-test-a3f91b-0004"
        git_ops.create_worktree(session_id, git_ops.current_branch)
        assert git_ops.worktree_exists(session_id)

        git_ops.remove_worktree(session_id)
        assert not git_ops.worktree_exists(session_id)

    def test_revert_worktree(self, git_ops):
        session_id = "20260322-test-a3f91b-0005"
        wt_path = git_ops.create_worktree(session_id, git_ops.current_branch)

        # Make a dirty change
        (wt_path / "experiment.txt").write_text("experiment data")
        (wt_path / "README.md").write_text("modified!")

        # Revert should clean everything
        git_ops.revert_worktree(wt_path)
        assert not (wt_path / "experiment.txt").exists()
        assert (wt_path / "README.md").read_text() == "# Test Repo\n"

    def test_commit_worktree(self, git_ops):
        session_id = "20260322-test-a3f91b-0006"
        wt_path = git_ops.create_worktree(session_id, git_ops.current_branch)

        (wt_path / "new_file.txt").write_text("new content")
        commit_hash = git_ops.commit_worktree(wt_path, "Test commit")
        assert len(commit_hash) == 7

    def test_diff_files(self, git_ops):
        session_id = "20260322-test-a3f91b-0007"
        wt_path = git_ops.create_worktree(session_id, git_ops.current_branch)

        (wt_path / "README.md").write_text("changed!")
        files = git_ops.diff_files(wt_path)
        assert "README.md" in files

    def test_multiple_worktrees_isolated(self, git_ops):
        """Changes in one worktree should not affect another."""
        wt_a = git_ops.create_worktree("session-a-000001", git_ops.current_branch)
        wt_b = git_ops.create_worktree("session-b-000002", git_ops.current_branch)

        (wt_a / "file_a.txt").write_text("only in A")
        assert not (wt_b / "file_a.txt").exists()


class TestOlFolderCommit:
    def test_commit_ol_folder(self, git_ops, tmp_git_repo):
        session_id = "20260322-test-a3f91b-0010"
        ol_dir = tmp_git_repo / "OmegaLoop" / session_id
        ol_dir.mkdir(parents=True)
        (ol_dir / "manifest.json").write_text('{"test": true}')

        git_ops.commit_ol_folder(session_id, "OL: test commit")

        # Verify it's committed
        log = git_ops.run("log", "--oneline", "-1")
        assert "OL: test commit" in log
