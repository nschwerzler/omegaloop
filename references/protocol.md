# OmegaLoop Protocol Reference

This document contains the complete research loop protocol. The SKILL.md provides the overview;
this file has the deep implementation details.

---

## Table of Contents

1. [Session Lifecycle](#session-lifecycle)
2. [Evaluation Framework](#evaluation-framework)
3. [Experiment Decision Tree](#experiment-decision-tree)
4. [Strategy Rotation](#strategy-rotation)
5. [Error Recovery](#error-recovery)
6. [Multi-Session Coordination](#multi-session-coordination)
7. [Git Worktree Operations](#git-worktree-operations)
8. [Manifest Schema](#manifest-schema)

---

## Session Lifecycle

```
CREATED → ANALYZING → LOOPING → PAUSED → COMPLETED
                        ↑          ↓
                        └──────────┘  (resume)
```

### State Transitions

- **CREATED**: manifest.json exists, worktree not yet created
- **ANALYZING**: Pre-loop analysis phase — reading code, establishing baseline
- **LOOPING**: Active experiment loop running
- **PAUSED**: Interrupted (Ctrl+C, error, max reached) — resumable
- **COMPLETED**: User marked done, or research goal achieved

### Initialization Checklist

Before starting the loop, verify ALL of these:

```bash
# 1. Git repo is clean (no uncommitted changes on main)
[ -z "$(git status --porcelain)" ] || echo "WARNING: Uncommitted changes"

# 2. AR directory exists and is committed
[ -d "$AR_DIR" ] || mkdir -p "$AR_DIR"/{logs,wins,checkpoints}

# 3. Worktree exists and is on the right branch
git worktree list | grep "$SESSION_ID" || {
  git branch "ar/$SESSION_ID" "$CURRENT_BRANCH" 2>/dev/null
  git worktree add "$WORKTREE_PATH" "ar/$SESSION_ID"
}

# 4. Manifest is valid JSON
python3 -c "import json; json.load(open('$AR_DIR/manifest.json'))" 2>/dev/null

# 5. Baseline checkpoint exists
[ -d "$AR_DIR/checkpoints/baseline" ] || echo "Need baseline"
```

---

## Evaluation Framework

The evaluation framework is prompt-dependent. Here are evaluation templates for common research types.

### Code Optimization Research

**Metrics**: execution time, memory usage, throughput
**Method**:
```bash
# Before (baseline)
time dotnet run --project benchmark/ > baseline-perf.txt

# After (experiment)
time dotnet run --project benchmark/ > experiment-perf.txt

# Compare
diff baseline-perf.txt experiment-perf.txt
```
**Win condition**: Measurably faster/smaller without breaking tests

### Code Quality Research

**Metrics**: test pass rate, lint warnings, code complexity
**Method**:
```bash
# Tests
dotnet test --logger "console;verbosity=normal" 2>&1 | tee test-results.txt
TEST_PASS=$(grep -c "Passed" test-results.txt)
TEST_FAIL=$(grep -c "Failed" test-results.txt)

# Lint
dotnet format --verify-no-changes 2>&1 | tee lint-results.txt
LINT_WARNINGS=$(wc -l < lint-results.txt)
```
**Win condition**: More tests pass, fewer warnings, no regressions

### Design Document Research

**Metrics**: completeness score (self-evaluated), actionability, correctness
**Method**: Agent evaluates its own output against a rubric:
1. Does it address the core problem? (0-10)
2. Are all failure modes covered? (0-10)
3. Is it implementable by a developer? (0-10)
4. Are trade-offs explicitly stated? (0-10)
5. Does it reference actual code/architecture? (0-10)
**Win condition**: Score improves over previous best

### Bug Hunting Research

**Metrics**: bugs found, bugs fixed, test coverage delta
**Method**:
```bash
# Run tests, capture failures
dotnet test 2>&1 | tee test-output.txt

# Count error handling patterns
grep -rn "catch\s*{" --include="*.cs" | wc -l  # empty catches
grep -rn "TODO\|FIXME\|HACK" --include="*.cs" | wc -l  # known issues
```
**Win condition**: Bug fixed, test added, coverage increased

### Feature Exploration Research

**Metrics**: feasibility score, complexity, performance characteristics
**Method**: Each approach gets a structured evaluation:
```json
{
  "approach": "description",
  "pros": [],
  "cons": [],
  "complexity": "low|medium|high",
  "estimated_effort": "days",
  "performance_characteristics": {},
  "recommendation": "text"
}
```
**Win condition**: Each completed approach analysis is a win (stored as artifact)

---

## Experiment Decision Tree

After each experiment, follow this decision tree:

```
Did the experiment run without errors?
├─ NO → Is it a recoverable error (typo, import, syntax)?
│       ├─ YES → Fix and retry (max 3 retries per experiment)
│       └─ NO → Log as ERROR, revert, move on
└─ YES → Did it improve on the baseline/previous best?
         ├─ YES → WIN! Store artifacts, advance branch, commit to AR
         ├─ NEUTRAL → Log insight, discard changes, move on
         └─ NO (worse) → Log why it's worse, discard, move on
```

### Discard Protocol

When discarding a failed experiment:

```bash
cd "$WORKTREE_PATH"
git checkout -- .          # Revert all changes
git clean -fd              # Remove untracked files
```

### Win Protocol

When storing a win:

```bash
WIN_NUM=$(printf '%03d' $WIN_COUNT)
WIN_DIR="$AR_DIR/wins/win-$WIN_NUM"
mkdir -p "$WIN_DIR"

# In worktree: commit the winning changes
cd "$WORKTREE_PATH"
git add -A
git commit -m "AR-$SESSION_ID: Experiment $EXP_NUM - [description]"

# Store artifacts
git diff HEAD~1 > "$WIN_DIR/changes.diff"
git show --stat HEAD > "$WIN_DIR/commit-info.txt"
git log -1 --format='%H' > "$WIN_DIR/commit-hash.txt"

# Copy changed files
for f in $(git diff --name-only HEAD~1); do
  mkdir -p "$WIN_DIR/files/$(dirname $f)"
  cp "$WORKTREE_PATH/$f" "$WIN_DIR/files/$f"
done

# Write summary
cat > "$WIN_DIR/summary.md" << 'SUMMARY'
# Win $WIN_NUM: [title]

## Experiment $EXP_NUM
**Timestamp**: [ISO-8601]
**Hypothesis**: [what was tried]

## Changes
[list of files and what changed]

## Metrics
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| [metric] | [val] | [val] | [+/-] |

## Reasoning
[why this worked]

## Implications
[what this means for future experiments]
SUMMARY

# Commit to main branch OmegaLoop folder
cd "$REPO_ROOT"
git add "OmegaLoop/$SESSION_ID/"
git commit -m "OL: Win #$WIN_NUM in $SESSION_ID - [brief]"
```

---

## Strategy Rotation

To avoid getting stuck, the agent rotates strategies. If the current strategy
hasn't produced a win in N experiments, switch to the next:

### Strategy Stack

1. **Low-hanging fruit** (experiments 1-5): Obvious improvements, quick fixes, simple optimizations
2. **Structural** (experiments 6-15): Refactoring, design pattern improvements, architectural changes
3. **Creative** (experiments 16-25): Non-obvious approaches, lateral thinking, unconventional solutions
4. **Adversarial** (experiments 26-35): Try to break things to find weaknesses, then fix them
5. **Synthesis** (experiments 36+): Combine insights from all previous experiments

### Stuck Detection

If **10 consecutive experiments** produce no wins:

1. Review all previous experiments and wins
2. Identify what patterns worked vs. didn't
3. Reformulate the hypothesis space
4. Try a completely different angle
5. If still stuck after 20 no-wins, write a summary of what was learned and pause

---

## Error Recovery

### Recoverable Errors

| Error | Recovery |
|-------|----------|
| Syntax error in change | Fix the syntax, retry |
| Build failure | Read error, adjust change |
| Test timeout | Reduce scope of change |
| Git conflict | Reset worktree, re-apply |

### Fatal Errors (Require Pause)

| Error | Action |
|-------|--------|
| Worktree corrupted | Delete and recreate worktree |
| Disk full | Alert user, pause |
| Git repo corrupted | Alert user, pause |
| Agent token limit | Save checkpoint, pause |

### Recovery from Interrupted Session

```bash
# 1. Read manifest
MANIFEST=$(cat "$AR_DIR/manifest.json")
STATUS=$(echo "$MANIFEST" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")

# 2. If status is LOOPING or PAUSED, resume
if [ "$STATUS" = "looping" ] || [ "$STATUS" = "paused" ]; then
  # Restore worktree if needed
  WORKTREE_PATH=$(echo "$MANIFEST" | python3 -c "import json,sys; print(json.load(sys.stdin)['worktree_path'])")
  if [ ! -d "$WORKTREE_PATH" ]; then
    BRANCH=$(echo "$MANIFEST" | python3 -c "import json,sys; print(json.load(sys.stdin)['worktree_branch'])")
    git worktree add "$WORKTREE_PATH" "$BRANCH"
  fi

  # Get experiment count and continue
  EXP_COUNT=$(echo "$MANIFEST" | python3 -c "import json,sys; print(json.load(sys.stdin)['experiment_count'])")
  echo "Resuming from experiment $((EXP_COUNT + 1))"
fi
```

---

## Multi-Session Coordination

Multiple AR sessions can run in the same repo. Each is fully isolated:

- Separate worktree branches (ar/SESSION_ID_1, ar/SESSION_ID_2)
- Separate OmegaLoop folders (OmegaLoop/SESSION_ID_1/, OmegaLoop/SESSION_ID_2/)
- Wins from one session can inform another

To list all sessions:
```bash
for d in "$REPO_ROOT/OmegaLoop"/*/; do
  [ -f "$d/manifest.json" ] && {
    SESSION=$(basename "$d")
    STATUS=$(python3 -c "import json; print(json.load(open('$d/manifest.json'))['status'])")
    WINS=$(python3 -c "import json; print(json.load(open('$d/manifest.json'))['win_count'])")
    echo "$SESSION: status=$STATUS wins=$WINS"
  }
done
```

---

## Git Worktree Operations

### Create Worktree
```bash
git branch "ar/$SESSION_ID" "$BASE_BRANCH" 2>/dev/null || true
git worktree add "$REPO_ROOT/.git/ol-worktrees/$SESSION_ID" "ar/$SESSION_ID"
```

### List Worktrees
```bash
git worktree list
```

### Remove Worktree (cleanup after session)
```bash
git worktree remove "$REPO_ROOT/.git/ol-worktrees/$SESSION_ID" --force
git branch -D "ar/$SESSION_ID"
```

### Sync Worktree with Main (get latest changes)
```bash
cd "$WORKTREE_PATH"
git merge "$BASE_BRANCH" --no-edit
```

---

## Manifest Schema

Complete JSON schema for `manifest.json`:

```json
{
  "schema_version": "1.0",
  "session_id": "string — unique session identifier",
  "created_at": "string — ISO-8601 timestamp",
  "updated_at": "string — ISO-8601 timestamp",
  "research_prompt": "string — the user's original prompt",
  "repo_root": "string — absolute path to repo root",
  "repo_name": "string — name of the repository",
  "base_branch": "string — branch session was started from",
  "worktree_branch": "string — ar/SESSION_ID",
  "worktree_path": "string — absolute path to worktree",
  "status": "string — initializing|analyzing|looping|paused|completed",
  "experiment_count": "number — total experiments run",
  "win_count": "number — total wins",
  "max_experiments": "number — max experiments before stopping (default 50)",
  "last_checkpoint": "string|null — ISO-8601 of last checkpoint",
  "current_strategy": "string — low-hanging|structural|creative|adversarial|synthesis",
  "consecutive_no_wins": "number — counter for stuck detection",
  "evaluation_criteria": {
    "type": "string — optimization|quality|design|bugfix|exploration",
    "metrics": ["array of metric names"],
    "win_condition": "string — description of what constitutes a win",
    "baseline": {}
  },
  "experiments": [
    {
      "experiment_id": "string — exp-001",
      "timestamp": "string — ISO-8601",
      "strategy": "string — which strategy was active",
      "hypothesis": "string — what was tried and why",
      "changes": ["array of file paths changed"],
      "result": "string — win|discard|error",
      "metrics": {},
      "reasoning": "string — why it worked or didn't",
      "diff_summary": "string — brief description of code changes",
      "error": "string|null — error message if result=error",
      "duration_seconds": "number — how long the experiment took"
    }
  ],
  "wins": [
    {
      "win_id": "string — win-001",
      "experiment_id": "string — which experiment produced this",
      "title": "string — brief description",
      "commit_hash": "string — git commit in worktree",
      "artifacts_path": "string — relative path to win folder",
      "metrics_delta": {}
    }
  ],
  "insights": [
    "string — accumulated learnings from experiments"
  ]
}
```
