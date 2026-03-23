# Python File Summary: orchestrator/ and tests/

## orchestrator/

| File | Purpose |
|------|---------|
| `orchestrator/__init__.py` | Package init that re-exports all public symbols (Orchestrator, ResearchLoop, SessionManager, GitOps, Manifest, MACHINE_ID, etc.) from engine.py. |
| `orchestrator/engine.py` | Core engine containing machine ID generation, data classes (Manifest, Experiment, WinRecord), GitOps (worktree/branch operations), SessionManager (session CRUD, discovery, checkpointing), ResearchLoop (experiment cycle), Orchestrator (multi-project coordinator with signal handling), and three agent backends (AgentFramework, Claude CLI, Copilot CLI). |
| `orchestrator/daemon.py` | CLI daemon providing OS-level scheduling (cron/launchd/Task Scheduler), interval parsing, loop type inference (monitor/converge/optimize/research), tick execution with lockfiles and heartbeats, and post-tick convergence/monitoring checks. |

## tests/

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared pytest fixtures providing a temporary git repo, GitOps instance, SessionManager instance, and sample manifest data from JSON fixture files. |
| `tests/test_machine_id.py` | Tests that machine ID generation produces stable, unique, 6-character hex strings derived from hostname and MAC address. |
| `tests/test_git_ops.py` | Tests for GitOps class covering repo basics (name, branch, clean status), worktree lifecycle (create, remove, revert, commit, diff), isolation between worktrees, and OmegaLoop folder commits. |
| `tests/test_session_manager.py` | Tests for SessionManager covering session creation (folder structure, worktree, git commit), loading, discovery by status, and checkpoint persistence. |
| `tests/test_manifest.py` | Tests for Manifest dataclass save/load roundtrip, timestamp updates, forward-compatibility with unknown fields, fixture loading, and experiment append-only accumulation. |
| `tests/test_daemon.py` | Tests for daemon functions including interval parsing (minutes/hours/days/seconds), cron expression generation, loop type inference from prompt keywords, task ID generation, and post-tick convergence/monitor streak logic. |
| `tests/test_distributed.py` | Tests for distributed multi-machine operation verifying collision avoidance across machine IDs, session IDs, experiment IDs, and worktree branches, plus cross-machine session discovery and resume. |
| `tests/test_bugs.py` | Regression tests for discovered bugs: parse_interval edge cases (empty/non-numeric input), main_sync entry point existence, run_tick graceful handling of malformed tasks, and Manifest.load behavior on corrupted JSON. |
| `tests/test_hang_prevention.py` | Tests for hang prevention mechanisms including tick lockfile acquisition/release/stale detection, heartbeat write/read/clear, safe JSON parsing of agent output (fences, preamble, partial), and run_tick lock integration (skip when locked, release on early termination). |
| `tests/evals/run_evals.py` | Eval runner that tests loop type inference accuracy against a JSON file of labeled prompts, with support for behavioral evals (requires Claude CLI) and dry-run mode. |
