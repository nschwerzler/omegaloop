---
applyTo: "**"
description: >
  Autonomous research loop for any git repository. Use this skill whenever the user says
  /omegaloop, "omegaloop", "research loop", "omega loop", "autonomous experiments",
  or asks to autonomously improve code, find optimizations, generate design docs, or run
  iterative experiments on their codebase.
tools:
  - bash
  - readFile
  - writeFile
  - editFile
  - findFiles
  - searchFiles
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
cat references/protocol.md
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
1. HYPOTHESIZE — Form an idea for improvement
2. IMPLEMENT  — Make the change in worktree
3. EVALUATE   — Run tests/checks/analysis
4. DECIDE     — Win or discard?
5. RECORD     — Log everything
6. CHECKPOINT — Save state for resume
7. REPEAT
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

After any session activity, regenerate the dashboard:

```bash
python3 scripts/generate-hub.py "$REPO_ROOT/OmegaLoop"
```

This creates `OmegaLoop/omegaloop.html` — a self-contained HTML dashboard showing:
- All sessions with status
- Experiment timeline
- Win/loss ratio
- Per-session drill-down with diffs and metrics

---

## Loop Types

### Type: `converge`
**Pattern**: Work toward a goal. Stop when it's achieved.

**Tick behavior**: Each tick runs tests/benchmarks, identifies a failure, writes a fix,
verifies, checkpoints. If the done condition is met for N consecutive ticks, the loop
auto-completes.

### Type: `monitor`
**Pattern**: Watch for external changes. React and enrich. Runs forever until stopped.

**Tick behavior**: Each tick checks the external source, diffs against last known state,
and if there's new data, enriches the target document.

### Type: `research`
**Pattern**: Classic omegaloop. Explore, experiment, keep wins. Finite.

**Tick behavior**: Hypothesize → implement → evaluate → keep/discard.

### Type: `optimize`
**Pattern**: Measurable metric. Iterate until diminishing returns or target hit.

**Tick behavior**: Like `research` but with a quantitative eval. Each experiment measures
the metric before and after.

| You want to... | Type | Terminates? | Typical interval |
|---|---|---|---|
| Fix all bugs / hit a target | `converge` | Yes, when done condition met | 5-15m |
| Watch something and react | `monitor` | No, manual stop only | 30m - 1d |
| Explore and discover | `research` | Yes, at max experiments | 10-15m |
| Improve a measurable metric | `optimize` | Yes, at max or plateau | 5-10m |

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
