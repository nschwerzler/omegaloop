# Loop Types

OmegaLoop supports four loop types. Each has distinct termination logic, prompt
framing, and manifest state.

## converge

**Purpose**: Work toward a specific done condition. Stop when achieved.

**Examples**:
```bash
omegaloop add --type converge --interval 10m \
  --prompt "Test the program. Find bugs, write failing tests (TDD), fix them."
  --done-condition "all tests pass with no new bugs in 3 consecutive passes"

omegaloop add --type converge --interval 10m \
  --prompt "Improve load time of Dashboard. Target: under 200ms."
  --done-condition "load time under 200ms"
```

**Tick behavior**:
1. Run tests / checks to detect failures
2. If failure found: write a failing test first (TDD), then fix it
3. Verify the fix passes
4. If no failures found: record "pass"
5. Checkpoint and exit

**Termination**: The daemon tracks a `done_streak`. Each tick where the done condition
appears met increments the streak. When `done_streak >= done_streak_target` (default 3),
the session auto-completes. This prevents false positives where tests pass once but a
deeper issue remains.

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

## monitor

**Purpose**: Watch for external changes. React and enrich. Runs forever.

**Examples**:
```bash
omegaloop add --type monitor --interval 30m \
  --prompt "Monitor PR #1234. If new comments or build failures, suggest fixes in pr1234.md." \
  --target-doc "pr1234.md"

omegaloop add --type monitor --schedule "0 9 * * 1-5" \
  --prompt "Check team ADO work items for Project Cosmos updates. Enrich cosmos-status.md."

omegaloop add --type monitor --interval 6h \
  --prompt "Check NuGet dependencies for security updates. Record in dep-updates.md."
```

**Tick behavior**:
1. Check the external source for new data since last tick
2. If new data found: enrich the target document with findings
3. If nothing new: log "no changes", exit quickly (save tokens)
4. Commit document updates to OmegaLoop folder
5. Checkpoint and exit

**Termination**: NEVER auto-completes. Only `omegaloop pause` or `omegaloop remove`.
No `--max` limit applies. The `--schedule` flag accepts full cron for "weekdays at 9am".

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

**Efficiency**: Monitors should exit fast when there's nothing new. The prompt
instructs the agent: "If nothing new, log 'no changes' and exit quickly to save tokens."

---

## research

**Purpose**: Open-ended exploration. Hypothesize, implement, evaluate. Finite.

**Examples**:
```bash
omegaloop add --type research --interval 15m --max 30 \
  --prompt "Find a headless browser solution that supports SSO, limits agent context. Produce solution.md."

omegaloop add --type research --interval 10m --max 50 \
  --prompt "Create a design.md for the distributed locking problem in the worker service."
```

**Tick behavior**:
1. Hypothesize an approach based on prompt + prior insights
2. Implement in worktree
3. Evaluate against criteria
4. WIN (keep) or DISCARD (revert)
5. Checkpoint and exit

**Termination**: Stops at `--max` experiments (default 50) OR when the agent determines
the research goal is fully addressed and produces a final deliverable.

**Strategy rotation**: If 10 consecutive experiments produce no wins, rotate strategy:
low-hanging → structural → creative → adversarial → synthesis.

---

## optimize

**Purpose**: Improve a measurable metric. Iterate until target or diminishing returns.

**Examples**:
```bash
omegaloop add --type optimize --interval 10m --max 100 \
  --prompt "Improve load time of DataGrid. Measure with: dotnet run --project bench/. Metric: avg_ms. Lower is better."

omegaloop add --type optimize --interval 15m --max 40 \
  --prompt "Reduce published binary size. Measure with: du -sh bin/Release/publish/. Lower is better."
```

**Tick behavior**:
1. Measure current metric (baseline or from last win)
2. Hypothesize an improvement
3. Implement in worktree
4. Measure again
5. If improved: WIN — keep change, record metric delta
6. If not: DISCARD — revert, try next hypothesis
7. Checkpoint and exit

**Termination**: Stops at `--max` OR when 15+ consecutive experiments produce no
improvement (diminishing returns / plateau detected).

**Manifest extras**:
```json
{
  "loop_type": "optimize",
  "metric_name": "avg_ms",
  "metric_command": "dotnet run --project bench/",
  "metric_direction": "lower",
  "baseline_value": 850,
  "best_value": 340,
  "metric_history": [850, 720, 680, 510, 340]
}
```

---

## Auto-Detection

If `--type` is not specified (or `--type auto`), the daemon infers from prompt keywords:

| Keywords | Detected Type |
|----------|--------------|
| "monitor", "watch", "check for", "if you see", "enrich", "once a day" | `monitor` |
| "until all tests", "TDD", "fix the bug", "until green", "target:", "under " | `converge` |
| "improve load time", "reduce size", "faster", "optimize", "benchmark" | `optimize` |
| (everything else) | `research` |
