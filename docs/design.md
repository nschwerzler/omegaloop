# Design Decisions

This document explains the "why" behind OmegaLoop's major design choices.

## D1: Git as the Coordination Layer

**Decision**: Use git push/pull to coordinate between machines. No central server.

**Rationale**: Every developer already has git. No infra to deploy, no ports to open,
no auth to configure. The OmegaLoop/ folder is committed to the repo, pushed to remote,
and other machines pull it. Merge conflicts on manifest.json are unlikely because each
machine writes to its own session folder (machine ID in the session ID).

**Trade-off**: No real-time coordination. Machine A won't see Machine B's latest win
until the next git pull. This is acceptable because research loops are independent —
they don't need sub-second coordination.

**Alternatives considered**:
- Redis/SQLite shared DB → requires infra, doesn't survive git clone
- File locking → doesn't work across machines
- HTTP API → requires running a server process

## D2: Machine-Scoped IDs

**Decision**: Every session ID, experiment ID, and worktree branch includes a 6-char
hash of hostname + MAC address.

**Format**: `{timestamp}-{machine_id}-{prompt_hash}`
**Example**: `20260322-143052-a3f91b-c4d2`

**Rationale**: Five machines can work on the same repo simultaneously. Without machine
scoping, two machines starting at the same second with the same prompt would collide on
branch names, session folders, and experiment IDs.

**How machine ID is generated**:
```python
hashlib.sha256(f"{platform.node()}-{uuid.getnode()}".encode()).hexdigest()[:6]
```
- `platform.node()` = hostname (stable across reboots)
- `uuid.getnode()` = MAC address (stable across reboots, unique per NIC)
- SHA256 → 6 chars = 16^6 = 16.7M possible IDs (collision probability negligible)

**Trade-off**: Session IDs are longer (26 chars vs 19 without machine ID). Acceptable
for readability since they're rarely typed by hand.

## D3: Tick-Based Execution (Not Long-Running)

**Decision**: Each "tick" fires a fresh `claude -p` process, runs a batch of experiments,
checkpoints, and exits. The OS scheduler fires the next tick.

**Rationale**:
1. **Crash resilience**: If the process crashes mid-tick, the OS scheduler fires again.
   At most one tick's worth of work is lost.
2. **No context bloat**: Each tick gets a clean context window. After 100 experiments
   in a long-running process, the context would be enormous. Tick-based means each tick
   only loads the manifest (state) + SKILL.md (instructions).
3. **Resource friendly**: No persistent process consuming memory between ticks.
4. **Reboot survival**: OS scheduler entries persist. Reboot → ticks resume automatically.

**Trade-off**: Overhead per tick (process startup, skill reading, manifest parsing).
With Claude CLI this is ~5-10 seconds per tick. Acceptable for 10-minute intervals.

**Alternatives considered**:
- Long-running daemon with asyncio → dies on reboot, context bloat
- tmux/screen session → fragile, doesn't survive reboot on all platforms
- systemd service → Linux-only, complex setup

## D4: Four Loop Types

**Decision**: Distinct loop types (converge, monitor, research, optimize) with
per-type termination logic and prompt templates.

**Rationale**: "Research everything the same way" doesn't match real usage:
- TDD bug fixing needs "keep going until tests pass" (converge)
- PR monitoring needs "run forever, react to changes" (monitor)
- Design exploration needs "try N things" (research)
- Performance tuning needs "measure, compare, keep winners" (optimize)

Each type has different:
- **Termination**: converge=done streak, monitor=never, research=max, optimize=plateau
- **Prompt framing**: what the agent should do each tick
- **State tracking**: what extra fields in the manifest

**Trade-off**: More complexity in daemon.py's prompt builder. But the user just says
`--type converge` and the rest is handled.

**Auto-detection**: If `--type auto`, the daemon infers from prompt keywords.
"monitor", "watch", "if you see" → monitor. "TDD", "until tests pass" → converge. etc.

## D5: OmegaLoop/ Folder in the Repo

**Decision**: All session data lives in `OmegaLoop/` at the repo root, committed to git.

**Rationale**:
- Survives disk loss (it's in git)
- Visible to other machines (via push/pull)
- Part of the project history (wins are real deliverables)
- Self-contained (clone the repo → you have all the research history)

**What goes in OmegaLoop/**:
- `manifest.json` — session state
- `research-prompt.md` — human-readable goal
- `wins/` — diffs, summaries, changed files from winning experiments
- `logs/` — experiment output logs
- `omegaloop.html` — dashboard (regenerated)

**What does NOT go in git**:
- Worktrees (`.git/ol-worktrees/`) — local only, recreated on resume
- Daemon task configs (`~/.omegaloop/`) — per-machine

## D6: Worktree Isolation

**Decision**: Every session gets its own git worktree. Experiments happen there, never
on the main branch.

**Rationale**: Main branch stays clean. If an experiment breaks the build, it only
breaks in the worktree. Discarding is a simple `git checkout -- .` + `git clean -fd`.

**Worktree naming**: `.git/ol-worktrees/{session-id}` — inside .git so it's never
committed. Recreated from the `ol/{session-id}` branch on resume.

## D7: Manifest as Single Source of Truth

**Decision**: `manifest.json` contains everything needed to resume a session.

**Rationale**: If the worktree is deleted, the machine reboots, or you clone on a new
machine, the manifest has: session ID, base branch, worktree branch, experiment count,
win count, evaluation criteria, full experiment log, and all insights.

Resume = read manifest → recreate worktree from branch → continue from experiment N+1.

**Schema versioned**: `schema_version: "2.0"` allows future migration.

## D8: OS-Native Scheduling

**Decision**: Use cron (Linux), launchd (macOS), Task Scheduler (Windows) directly.
No custom daemon process.

**Rationale**: These schedulers are battle-tested, survive reboots, and require zero
ongoing process management. A forgotten OmegaLoop task is just a cron entry — easy to
find, easy to remove, uses no resources when not firing.

**Platform detection**: `platform.system()` → route to the right installer.

## D9: Agent-Agnostic Backend

**Decision**: The daemon doesn't care which LLM runs the experiments. It supports
Claude CLI, Microsoft Agent Framework, and GitHub Copilot as interchangeable backends.

**Rationale**: Users have different subscriptions. Some have unlimited Copilot tokens,
some have Azure credits, some have Claude Max. The research protocol is the same
regardless of which model executes it.

**Implementation**: `--backend claude|agent-framework|copilot` selects the subprocess
command. The prompt and SKILL.md are identical across backends.

## D10: Additive Multi-Machine Results

**Decision**: When multiple machines work on the same session, their results are
additive. Experiment IDs include machine ID, so there's no collision.

**Example**: Machine A produces `exp-007-a3f91b`, Machine B produces `exp-007-b7e2c0`.
Both are valid experiments in the same session. The manifest's `machines_involved`
array tracks which machines contributed.

**Merge strategy**: Each machine commits its own wins to the `OmegaLoop/` folder.
Git merge works cleanly because each machine writes to different files (machine ID
in win folder names). On the rare occasion of a manifest.json conflict, the machine
that pulls latest gets a merge conflict — resolved by taking the higher experiment
count (since experiments are append-only).
