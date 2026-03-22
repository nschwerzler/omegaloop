"""Shared fixtures for OmegaLoop tests."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Add the omegaloop root to path so we can import orchestrator
OMEGALOOP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(OMEGALOOP_ROOT))


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a temporary git repository with one commit."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@omegaloop.dev"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "OmegaLoop Test"],
        cwd=str(repo), capture_output=True, check=True,
    )
    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo), capture_output=True, check=True,
    )
    return repo


@pytest.fixture
def git_ops(tmp_git_repo):
    """GitOps instance for a temp repo."""
    from orchestrator.engine import GitOps
    return GitOps(str(tmp_git_repo))


@pytest.fixture
def session_manager(git_ops):
    """SessionManager instance for a temp repo."""
    from orchestrator.engine import SessionManager
    return SessionManager(git_ops)


@pytest.fixture
def sample_manifest():
    """A complete manifest dict for testing."""
    return json.loads(
        (Path(__file__).parent / "fixtures" / "manifest_v2_full.json").read_text()
    )


@pytest.fixture
def minimal_manifest():
    """A minimal valid manifest dict."""
    return json.loads(
        (Path(__file__).parent / "fixtures" / "manifest_v2_minimal.json").read_text()
    )


@pytest.fixture
def sample_task_config():
    """A sample daemon task config dict."""
    return json.loads(
        (Path(__file__).parent / "fixtures" / "task_config.json").read_text()
    )
