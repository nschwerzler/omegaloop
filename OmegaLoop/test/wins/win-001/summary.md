# OmegaLoop Python File Summary

## orchestrator/

| File | Purpose |
|------|---------|
| `__init__.py` | Package init that re-exports core classes (Orchestrator, ResearchLoop, SessionManager, GitOps, Manifest) from engine. |
| `daemon.py` | CLI entry point and OS scheduler integration (cron/launchd/Task Scheduler) that registers, pauses, resumes, and removes research loop tasks. |
| `engine.py` | Core engine providing GitOps (worktrees, commits), SessionManager (session CRUD, checkpointing), ResearchLoop execution, Manifest state, and machine identity for distributed crash-resilient research loops. |

## tests/

| File | Purpose |
|------|---------|
| `conftest.py` | Shared pytest fixtures including a temporary git repository factory used across all test modules. |
| `test_machine_id.py` | Tests that machine ID generation produces stable, unique 6-char hex identifiers. |
| `test_git_ops.py` | Tests for GitOps worktree lifecycle, commit, revert, and branch operations. |
| `test_session_manager.py` | Tests for SessionManager session creation, discovery, and checkpoint persistence. |
| `test_manifest.py` | Tests for Manifest dataclass save/load roundtrip and JSON schema correctness. |
| `test_daemon.py` | Tests for daemon interval parsing, cron expression generation, loop type inference, and termination logic. |
| `test_distributed.py` | Tests for distributed multi-machine collision avoidance using simulated machine IDs. |
| `test_bugs.py` | Regression tests for bugs discovered during integration testing, written before fixes to confirm each bug. |
| `test_hang_prevention.py` | Tests for hang prevention mechanisms including lockfiles, heartbeats, timeouts, and safe JSON parsing. |
| `evals/run_evals.py` | Eval runner that executes type-detection evals (pure Python) and optional behavioral evals (requiring claude CLI). |
