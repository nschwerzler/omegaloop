---
name: omegaloop
description: >
  Autonomous research loop for any git repository. Use this skill whenever the user says
  /omegaloop, "omegaloop", "research loop", "omega loop", "autonomous experiments",
  or asks to autonomously improve code, find optimizations, generate design docs, or run
  iterative experiments on their codebase. This skill auto-detects the git repo and branch,
  creates isolated worktrees for experiments, tracks wins in an OmegaLoop folder, and
  provides The OmegaLoop dashboard for diagnostics. Works with Claude CLI, Copilot CLI, or any
  agent that can read files, edit files, and use git. Supports Microsoft Agent Framework
  for multi-agent orchestration. Trigger aggressively — if the user wants autonomous
  iterative improvement of anything in a repo, this is the skill.
---

# OmegaLoop — Live. Die. Repeat.

An autonomous research loop for any git repository. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) but generalized: instead of training neural nets on a GPU, this uses LLM agents as the "compute" — powered by your Copilot subscription, Claude CLI, or Azure AI Foundry tokens.

## Quick Reference

```
/omegaloop "Make feature X faster"
/omegaloop "Create a design.md that solves the caching problem in src/cache/"
/omegaloop "Find and fix all error handling gaps in the API layer"
```

## How It Works

1. **Detect** — Auto-detect git repo root, current branch, remote
2. **Initialize** — Create `OmegaLoop/{session-id}/` with manifest and research prompt
3. **Isolate** — Create a git worktree for experimentation (never touch main branch)
4. **Loop** — Agent reads code → proposes change → applies → evaluates → keep or discard
5. **Win** — When improvement found, store artifacts and commit to OmegaLoop folder on main branch
6. **Resume** — If interrupted, pick up from last checkpoint
7. **Dashboard** — The OmegaLoop HTML shows all sessions, experiments, wins

---

## Step 1: Read the Protocol

Before doing ANYTHING else, read the full research protocol:

```bash
cat "$(dirname "$0")/references/protocol.md"
```

This contains the complete loop logic, evaluation criteria, and decision framework.

## Step 2: Detect Environment

Run these checks immediately:

```bash
# Must be in a git repo
git rev-parse --show-toplevel 2>/dev/null || echo "ERROR: Not in a git repo"

# Get repo root, current branch, remote
REPO_ROOT=$(git rev-parse --show-toplevel)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "no-remote")

echo "Repo: $REPO_ROOT"
echo "Branch: $CURRENT_BRANCH"
echo "Remote: $REMOTE_URL"
```

## Step 3: Initialize Session

Parse the user's research prompt. Generate a session ID and create the OmegaLoop folder:

```bash
# Machine ID — unique per machine, stable across reboots
MACHINE_ID=$(python3 -c "import hashlib,platform,uuid; print(hashlib.sha256(f'{platform.node()}-{uuid.getnode()}'.encode()).hexdigest()[:6])")

# Session ID includes machine ID to prevent collision across machines
SESSION_ID=$(date +%Y%m%d-%H%M%S)-${MACHINE_ID}-$(echo "$RESEARCH_PROMPT" | md5sum | cut -c1-4)
AR_DIR="$REPO_ROOT/OmegaLoop/$SESSION_ID"

mkdir -p "$AR_DIR"/{logs,wins,checkpoints}
```

Create the **manifest.json** — this is the session's brain:

```json
{
  "schema_version": "2.0",
  "session_id": "SESSION_ID",
  "created_at": "ISO-8601",
  "research_prompt": "the user's original prompt",
  "repo_root": "/absolute/path",
  "base_branch": "main",
  "worktree_branch": "ar/SESSION_ID",
  "worktree_path": "/absolute/path/.git/ol-worktrees/SESSION_ID",
  "status": "initializing",
  "machine_id": "a3f91b",
  "machines_involved": ["a3f91b"],
  "experiment_count": 0,
  "win_count": 0,
  "last_checkpoint": null,
  "evaluation_criteria": {},
  "experiments": []
}
```

Create the **research-prompt.md** — human-readable version of the goal:

```markdown
# OmegaLoop Session: SESSION_ID

## Research Prompt
> [the user's exact prompt]

## Scope
- Repository: [repo name]
- Branch: [base branch]
- Started: [timestamp]

## Evaluation Criteria
[filled in during analysis phase — see protocol.md]
```

**Commit the initialization:**
```bash
cd "$REPO_ROOT"
git add "OmegaLoop/$SESSION_ID/manifest.json" "OmegaLoop/$SESSION_ID/research-prompt.md"
git commit -m "OL: Initialize session $SESSION_ID"
```

## Step 4: Create Worktree

Experiments happen in an isolated git worktree. Main branch stays clean.

```bash
WORKTREE_PATH="$REPO_ROOT/.git/ol-worktrees/$SESSION_ID"
WORKTREE_BRANCH="ar/$SESSION_ID"

# Create branch and worktree
git branch "$WORKTREE_BRANCH" "$CURRENT_BRANCH"
git worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH"

echo "Worktree ready at: $WORKTREE_PATH"
```

**All code changes happen in the worktree. NEVER modify files on the main branch directly.**

## Step 5: Analysis Phase (Pre-Loop)

Before looping, understand the codebase. In the worktree:

1. **Inventory** — List all relevant files, understand the structure
2. **Scope** — Identify which files/modules relate to the research prompt
3. **Baseline** — Establish what "current state" looks like (run tests, measure performance, read existing code)
4. **Criteria** — Define what "better" means for THIS prompt:
   - Code quality improvement? → diff review, lint scores
   - Performance? → benchmark before/after
   - Design doc? → completeness, correctness, actionability
   - Bug fixes? → test pass rate, coverage
   - Feature improvement? → functional correctness

Update `manifest.json` with evaluation criteria and save a baseline snapshot:

```bash
# Save baseline snapshot
cp "$WORKTREE_PATH/[relevant files]" "$AR_DIR/checkpoints/baseline/"
```

## Step 6: The Research Loop

**LOOP FOREVER** (until the user interrupts or max experiments reached):

```
┌─────────────────────────────────────────────────┐
│  1. HYPOTHESIZE — Form an idea for improvement  │
│  2. IMPLEMENT  — Make the change in worktree    │
│  3. EVALUATE   — Run tests/checks/analysis      │
│  4. DECIDE     — Win or discard?                 │
│  5. RECORD     — Log everything                  │
│  6. CHECKPOINT — Save state for resume           │
│  7. REPEAT                                       │
└─────────────────────────────────────────────────┘
```

### Per-Experiment Protocol

**1. HYPOTHESIZE** — Based on research prompt + what you've learned so far, form a specific hypothesis:
   - What change will you make?
   - Why do you think it will help?
   - What's the expected outcome?

**2. IMPLEMENT** — In the worktree:
   ```bash
   cd "$WORKTREE_PATH"
   # Make your changes to the code
   ```

**3. EVALUATE** — Run the evaluation criteria you defined:
   ```bash
   # Examples:
   # Tests: dotnet test / npm test / pytest
   # Build: dotnet build / npm run build
   # Lint: dotnet format --verify-no-changes
   # Custom: whatever makes sense for this research
   ```

**4. DECIDE** — Compare against baseline or previous best:
   - **WIN**: Result is better → advance the worktree branch, store artifacts
   - **DISCARD**: Result is same or worse → `git checkout -- .` in worktree

**5. RECORD** — Log the experiment in manifest.json:
   ```json
   {
     "experiment_id": "exp-001-a3f91b",
     "timestamp": "ISO-8601",
     "machine_id": "a3f91b",
     "hypothesis": "description",
     "changes": ["file1.cs", "file2.cs"],
     "result": "win|discard|error",
     "metrics": {},
     "reasoning": "why it worked or didn't",
     "diff_summary": "brief description of changes"
   }
   ```

**6. CHECKPOINT** — Save state so the loop can resume:
   ```bash
   # Update manifest
   cp manifest.json "$AR_DIR/manifest.json"

   # If WIN, store win artifacts
   if [ "$RESULT" = "win" ]; then
     WIN_DIR="$AR_DIR/wins/win-$(printf '%03d' $WIN_COUNT)"
     mkdir -p "$WIN_DIR"

     # Store the winning changes
     cd "$WORKTREE_PATH"
     git diff HEAD~1 > "$WIN_DIR/changes.diff"
     git log -1 --format="%H %s" > "$WIN_DIR/commit.txt"
     cp [changed files] "$WIN_DIR/"

     # Write win summary
     cat > "$WIN_DIR/summary.md" << EOF
   # Win $WIN_COUNT: [brief title]
   ## Hypothesis
   [what you tried]
   ## Result
   [what happened]
   ## Changes
   [list of files changed]
   ## Metrics
   [before/after comparison]
   EOF

     # Commit to main branch OmegaLoop folder
     cd "$REPO_ROOT"
     git add "OmegaLoop/$SESSION_ID/"
     git commit -m "OL: Win #$WIN_COUNT - [brief description]"
   fi
   ```

### Loop Control

- **Max experiments**: Default 50. Override with `/omegaloop --max 100 "prompt"`
- **Max wins**: No limit. Keep finding improvements.
- **Error recovery**: If an experiment crashes, log the error, revert worktree, continue
- **Stuck detection**: If 10 consecutive experiments produce no wins, try a different strategy
- **Graceful stop**: User can Ctrl+C. Session is resumable from last checkpoint.

## Step 7: Resume a Session

To resume an interrupted session:

```bash
# Find existing sessions
ls "$REPO_ROOT/OmegaLoop/"

# Read the manifest to get state
cat "$REPO_ROOT/OmegaLoop/$SESSION_ID/manifest.json"
```

The manifest contains everything needed to resume:
- Which worktree to use (recreate if deleted)
- Which experiment we're on
- What the evaluation criteria are
- What wins we've found so far

## Step 8: The OmegaLoop Dashboard

After any session activity, regenerate the The OmegaLoop:

```bash
# Read the template and generate
python3 "$(dirname "$0")/scripts/generate-omegaloop.py" "$REPO_ROOT/OmegaLoop"
```

This creates `OmegaLoop/omegaloop.html` — a self-contained HTML dashboard showing:
- All sessions with status
- Experiment timeline
- Win/loss ratio
- Per-session drill-down with diffs and metrics
- Live-updating if file-watched

The OmegaLoop reads all `manifest.json` files from session folders. No server needed — just open the HTML file.

---

## Durable Scheduling (omegaloop)

For fire-and-forget research loops that survive reboots and run unattended,
use the daemon. It registers with your OS scheduler (cron / launchd / Task Scheduler),
fires `claude -p` sessions on an interval, and each session runs a batch of experiments.

```bash
# Add a research loop — starts immediately, survives reboots
python omegaloop/orchestrator/daemon.py add \
  --repo ~/repos/winapp-sdk \
  --prompt "Optimize the caching layer" \
  --interval 10m \
  --batch 5 \
  --max 50

# Add more loops for other projects
python omegaloop/orchestrator/daemon.py add \
  --repo ~/repos/sbom5000 \
  --prompt "Fix error handling gaps" \
  --interval 15m

# See what's running
python omegaloop/orchestrator/daemon.py list

# Check logs
python omegaloop/orchestrator/daemon.py logs <task-id>

# Pause / resume / remove
python omegaloop/orchestrator/daemon.py pause <task-id>
python omegaloop/orchestrator/daemon.py resume --all
python omegaloop/orchestrator/daemon.py remove <task-id>
```

### How it works

Each tick (default every 10 minutes):
1. OS scheduler fires `omegaloop run-tick <task-id>`
2. Daemon reads `~/.omegaloop/tasks/<task-id>.json` for config
3. Reads `OmegaLoop/{session}/manifest.json` for current state
4. Fires `claude -p` with skill + context + "run N experiments, checkpoint, exit"
5. Claude runs experiments in worktree, checkpoints, exits
6. Next tick picks up where it left off

### Reboot behavior
- **Cron (Linux/WSL)**: crontab entry persists across reboots
- **Launchd (macOS)**: plist in ~/Library/LaunchAgents auto-loads on login
- **Task Scheduler (Windows)**: registered task survives reboots

### Clone to new machine
```bash
git clone git@github.com:org/repo.git && cd repo
python omegaloop/orchestrator/daemon.py add \
  --repo . --prompt "Same research" --interval 10m
# OR resume from the OmegaLoop folder that was already pushed:
# Daemon auto-detects existing session via manifest.json
```

---

## Distributed Orchestrator (Python + MS Agent Framework)

For multi-project, multi-machine research — read the orchestrator docs:

```bash
cat "$(dirname "$0")/references/agent-framework-setup.md"
```

Or run the orchestrator directly:

```bash
# Install Agent Framework
pip install agent-framework --pre azure-identity

# Single project
python -m orchestrator.engine --repo . --prompt "Make caching faster" --max 50

# Resume ALL incomplete sessions after reboot
python -m orchestrator.engine --resume

# Multi-project config
python -m orchestrator.engine --config loops.json

# Use Claude CLI instead of Azure
python -m orchestrator.engine --backend claude
```

The orchestrator:
- Runs N projects concurrently (async threads)
- Machine-scoped IDs prevent collision across 5+ machines on same repo
- Checkpoints every experiment — survives reboots
- Uses git push/pull as coordination layer — no central server
- Supports backends: `agent-framework`, `claude` CLI, `copilot` CLI

---

## File Structure Reference

```
YourRepo/
├── OmegaLoop/                          # All OmegaLoop data lives here (committed)
│   ├── omegaloop.html                        # Dashboard (regenerated)
│   ├── .gitignore                         # Ignore temp files
│   ├── 20260322-143052-a3f91b-c4d2/       # Session folder (machine ID in name)
│   │   ├── manifest.json                  # Session brain — experiment log
│   │   ├── research-prompt.md             # Human-readable prompt
│   │   ├── logs/                          # Raw experiment logs
│   │   ├── wins/                          # Winning artifacts
│   │   │   └── win-001/
│   │   │       ├── summary.md
│   │   │       ├── changes.diff
│   │   │       └── commit-hash.txt
│   │   └── checkpoints/                   # Resume data
│   ├── 20260322-160000-b7e2c0-f1a3/       # Session from DIFFERENT machine
│   └── ...
├── .git/
│   └── ol-worktrees/                      # Worktrees (local only, recreated)
│       ├── 20260322-143052-a3f91b-c4d2/
│       └── 20260322-160000-b7e2c0-f1a3/
└── [rest of your repo]
```

## Loop Types

Every OmegaLoop session has a **loop type** that controls termination, evaluation,
tick behavior, and output format. Set the type in the prompt or let the agent infer it.

---

### Type: `converge`
**Pattern**: Work toward a goal. Stop when it's achieved.

```bash
# TDD bug hunting — find bugs, write tests, fix, repeat until green
omegaloop add --repo . --type converge --interval 10m \
  --prompt "Test the program. If you find a bug, create a failing test (TDD), then fix the bug. Repeat until all tests pass with no new bugs found in 3 consecutive passes."

# Performance target — stop when target is hit
omegaloop add --repo . --type converge --interval 10m \
  --prompt "Improve load time of the Dashboard feature. Target: under 200ms. Current: 850ms."
```

**Tick behavior**: Each tick runs tests / benchmarks, identifies a failure, writes a fix,
verifies, checkpoints. If the done condition is met for N consecutive ticks, the loop
auto-completes.

**Done condition** (set in prompt or auto-inferred):
- "all tests pass with no new bugs found in 3 consecutive passes"
- "load time under 200ms"
- "zero lint warnings"
- "coverage above 80%"

**Output**: `wins/` folder contains each fix with its test. `manifest.json` tracks
the convergence metric over time.

**Manifest extras**:
```json
{
  "loop_type": "converge",
  "done_condition": "all tests pass, no new bugs in 3 consecutive passes",
  "done_streak": 0,
  "done_streak_target": 3,
  "converge_metric": "test_failures",
  "converge_history": [12, 8, 5, 3, 1, 0, 0, 0]
}
```

---

### Type: `monitor`
**Pattern**: Watch for external changes. React and enrich. Runs forever until stopped.

```bash
# PR monitor — watch for comments/failures, enrich a doc
omegaloop add --repo . --type monitor --interval 30m \
  --prompt "Monitor PR #1234. If you see a new comment or build failure, suggest a fix in OmegaLoop/{session}/pr1234.md. Keep enriching the doc as you find more or better solutions."

# Chat/data monitor — watch for new info, enrich a project doc
omegaloop add --repo . --type monitor --interval 1d --schedule "0 9 * * 1-5" \
  --prompt "Check our team's recent ADO work items and chat threads for updates about Project Cosmos. Enrich docs/cosmos-status.md with latest findings."

# Dependency monitor — watch for new versions
omegaloop add --repo . --type monitor --interval 6h \
  --prompt "Check if any NuGet dependencies have new versions with security fixes. If found, update the dependency and run tests. Record findings in OmegaLoop/{session}/dep-updates.md."
```

**Tick behavior**: Each tick checks the external source, diffs against last known state,
and if there's new data, enriches the target document. If nothing new, logs "no changes"
and exits quickly.

**Termination**: NEVER auto-completes. Runs until you `omegaloop pause` or `remove` it.
No `--max` limit. The `--schedule` flag accepts full cron expressions for precise timing.

**Output**: Instead of `wins/`, monitors produce **enrichments** — timestamped additions
to a living document. The document accumulates knowledge over time.

**Manifest extras**:
```json
{
  "loop_type": "monitor",
  "target_doc": "pr1234.md",
  "last_external_state_hash": "a3f91b",
  "enrichment_count": 14,
  "no_change_streak": 0,
  "never_auto_complete": true
}
```

---

### Type: `research`
**Pattern**: Classic omegaloop. Explore, experiment, keep wins. Finite.

```bash
# Open-ended discovery
omegaloop add --repo . --type research --interval 10m --max 50 \
  --prompt "I need a headless browser solution that agents can work with, supports SSO websites, limits context given to the agent but has all content, and doesn't require a visible browser. Research options, prototype the top 3, evaluate. Produce solution.md."

# Design exploration
omegaloop add --repo . --type research --interval 15m --max 30 \
  --prompt "Create a design.md that solves the distributed locking problem in our worker service. Explore Redis, etcd, and ZooKeeper approaches."
```

**Tick behavior**: Hypothesize → implement → evaluate → keep/discard. Classic loop.

**Termination**: Stops at `--max` experiments OR when the agent determines the research
goal is fully addressed (produces a final deliverable).

**Output**: `wins/` with diffs and summaries. Final deliverable (design.md, solution.md)
is a win artifact.

---

### Type: `optimize`
**Pattern**: Measurable metric. Iterate until diminishing returns or target hit.

```bash
# Performance optimization with metric
omegaloop add --repo . --type optimize --interval 10m --max 100 \
  --prompt "Improve load time of the DataGrid feature. Measure with: dotnet run --project bench/. Metric: avg_ms in output. Lower is better."

# Binary size optimization
omegaloop add --repo . --type optimize --interval 15m --max 40 \
  --prompt "Reduce the published binary size. Measure with: dotnet publish -c Release && du -sh bin/Release/net10.0/publish/. Lower is better."
```

**Tick behavior**: Like `research` but with a quantitative eval. Each experiment measures
the metric before and after. Keeps changes that improve the metric.

**Termination**: Stops at `--max` OR when 15+ consecutive experiments produce no improvement
(diminishing returns detected).

**Manifest extras**:
```json
{
  "loop_type": "optimize",
  "metric_name": "avg_ms",
  "metric_command": "dotnet run --project bench/",
  "metric_direction": "lower",
  "baseline_value": 850,
  "best_value": 340,
  "metric_history": [850, 720, 720, 680, 510, 510, 340]
}
```

---

## Choosing the Right Loop Type

| You want to... | Type | Terminates? | Typical interval |
|---|---|---|---|
| Fix all bugs / hit a target | `converge` | Yes, when done condition met | 5-15m |
| Watch something and react | `monitor` | No, manual stop only | 30m - 1d |
| Explore and discover | `research` | Yes, at max experiments | 10-15m |
| Improve a measurable metric | `optimize` | Yes, at max or plateau | 5-10m |

If unsure, describe your goal and the agent will pick the right type.

---

## Scheduling Control

The daemon supports both intervals and full cron expressions:

```bash
# Every 10 minutes
omegaloop add --interval 10m ...

# Every 6 hours
omegaloop add --interval 6h ...

# Once a day at 9am weekdays
omegaloop add --schedule "0 9 * * 1-5" ...

# Twice a day at 9am and 5pm
omegaloop add --schedule "0 9,17 * * *" ...

# Every Monday at 8am
omegaloop add --schedule "0 8 * * 1" ...

# Once a day (shorthand)
omegaloop add --interval 1d ...
```

`--schedule` takes raw cron (5-field) and overrides `--interval`.
`--interval` is syntactic sugar that converts to cron internally.

---

## Critical Rules

1. **Never modify main branch code directly** — all experiments in worktrees
2. **Always commit OmegaLoop folder changes to main** — wins are your research output
3. **Never stop to ask permission** — loop forever until interrupted or done
4. **Log everything** — even failures are valuable data
5. **Be bold** — try non-obvious approaches, that's the point of autonomous research
6. **Checkpoints are sacred** — always save state before moving to next experiment
7. **The OmegaLoop folder is the source of truth** — everything needed to understand and resume lives there
8. **Monitors never auto-stop** — only manual pause/remove
9. **Converge loops verify done-ness** — meet the condition N times in a row before stopping
10. **Each tick is self-contained** — get context from manifest, do work, checkpoint, exit cleanly
