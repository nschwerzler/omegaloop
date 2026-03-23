# Python File Summary: orchestrator/ and tests/

## orchestrator/

| File | Purpose |
|------|---------|
| `__init__.py` | Package init that re-exports all public symbols (Orchestrator, ResearchLoop, SessionManager, GitOps, Manifest, etc.) from `engine.py`. |
| `engine.py` | Core engine implementing distributed, crash-resilient research loops with git worktree isolation, session management, manifest persistence, and agent orchestration via Microsoft Agent Framework. |
| `daemon.py` | CLI entry point and OS scheduler integration (cron/launchd/Task Scheduler) that registers durable research loop ticks surviving reboots without a terminal. |

## tests/

| File | Purpose |
|------|---------|
| `conftest.py` | Shared pytest fixtures including temporary git repo creation and path setup for importing the orchestrator package. |
| `test_machine_id.py` | Verifies machine ID generation produces deterministic 6-char hex strings derived from hostname and MAC address. |
| `test_git_ops.py` | Tests GitOps class for worktree lifecycle management, commit operations, and revert functionality. |
| `test_session_manager.py` | Tests SessionManager CRUD operations including session creation, discovery, and checkpoint persistence. |
| `test_manifest.py` | Tests Manifest dataclass serialization (save/load roundtrip) and schema correctness. |
| `test_daemon.py` | Tests daemon utilities: interval parsing, cron expression generation, loop type inference, task ID generation, and post-tick termination logic. |
| `test_distributed.py` | Tests distributed multi-machine operation and collision avoidance using simulated machine IDs. |
| `test_bugs.py` | Regression tests for bugs discovered during integration testing, each written before the fix to confirm the bug. |
| `test_hang_prevention.py` | Tests hang prevention mechanisms including lockfile acquisition, heartbeats, timeouts, and safe JSON parsing. |
| `evals/run_evals.py` | Eval runner that executes type detection evals (pure Python) and behavioral evals (requiring Claude CLI) to test skill behavior. |
