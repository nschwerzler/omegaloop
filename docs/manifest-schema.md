# Manifest Schema Reference

The `manifest.json` file is the single source of truth for a session. It contains
everything needed to resume a session on any machine.

## Location

```
OmegaLoop/{session-id}/manifest.json
```

## Schema v2.0

```jsonc
{
  // -- Identity --
  "schema_version": "2.0",
  "session_id": "20260322-143052-a3f91b-c4d2",  // {timestamp}-{machine}-{prompt_hash}
  "created_at": "2026-03-22T14:30:52Z",          // ISO-8601
  "updated_at": "2026-03-22T16:45:12Z",          // updated on every checkpoint

  // -- Research Goal --
  "research_prompt": "Optimize the caching layer in src/cache/",

  // -- Repository Context --
  "repo_root": "/home/nick/repos/winapp-sdk",
  "repo_name": "winapp-sdk",
  "base_branch": "main",
  "worktree_branch": "ol/20260322-143052-a3f91b-c4d2",
  "worktree_path": "/home/nick/repos/winapp-sdk/.git/ol-worktrees/20260322-143052-a3f91b-c4d2",

  // -- Session State --
  "status": "looping",              // initializing | analyzing | looping | paused | completed | error
  "machine_id": "a3f91b",           // machine that created the session
  "machines_involved": ["a3f91b", "b7e2c0"],  // all machines that contributed
  "experiment_count": 25,
  "win_count": 4,
  "max_experiments": 50,             // null for monitors
  "last_checkpoint": "2026-03-22T16:45:12Z",

  // -- Strategy --
  "current_strategy": "structural",  // low-hanging | structural | creative | adversarial | synthesis
  "consecutive_no_wins": 3,          // reset to 0 on each win

  // -- Loop Type Extras (varies by type) --
  "loop_type": "optimize",           // converge | monitor | research | optimize
  // converge:
  "done_condition": "all tests pass",
  "done_streak": 0,
  "done_streak_target": 3,
  "converge_metric": "test_failures",
  "converge_history": [12, 8, 5, 3, 1, 0],
  // monitor:
  "target_doc": "pr1234.md",
  "enrichment_count": 14,
  "no_change_streak": 0,
  "never_auto_complete": true,
  // optimize:
  "metric_name": "avg_ms",
  "metric_command": "dotnet run --project bench/",
  "metric_direction": "lower",       // lower | higher
  "baseline_value": 850,
  "best_value": 340,
  "metric_history": [850, 720, 680, 510, 340],

  // -- Evaluation --
  "evaluation_criteria": {
    "type": "optimization",          // optimization | quality | design | bugfix | exploration
    "metrics": ["avg_latency_ms", "cache_hit_rate"],
    "win_condition": "Measurably faster without breaking tests",
    "baseline": {"avg_latency_ms": 45.2, "cache_hit_rate": 72.3}
  },

  // -- Experiment Log (append-only) --
  "experiments": [
    {
      "experiment_id": "exp-001-a3f91b",
      "timestamp": "2026-03-22T14:35:00Z",
      "machine_id": "a3f91b",
      "strategy": "low-hanging",
      "hypothesis": "Replace Dictionary with ConcurrentDictionary",
      "changes": ["src/cache/CacheStore.cs"],
      "result": "win",              // win | discard | error
      "metrics": {"avg_latency_ms": 43.8},
      "reasoning": "Eliminated lock contention on read path",
      "diff_summary": "Swapped Dictionary for ConcurrentDictionary",
      "error": null,                 // error message if result=error
      "duration_seconds": 180
    }
  ],

  // -- Win Records --
  "wins": [
    {
      "win_id": "win-001",
      "experiment_id": "exp-001-a3f91b",
      "title": "ConcurrentDictionary eliminates lock contention",
      "commit_hash": "a1b2c3d",
      "machine_id": "a3f91b",
      "artifacts_path": "wins/win-001",
      "metrics_delta": {"avg_latency_ms": -1.4}
    }
  ],

  // -- Accumulated Insights --
  "insights": [
    "Lock contention was the biggest bottleneck",
    "Hash computation costs add up on hot paths"
  ]
}
```

## Status Lifecycle

```
initializing → analyzing → looping → completed
                             ↕
                           paused
                             ↕
                           error
```

## Notes

- `experiments` array is append-only. Never remove entries.
- `experiment_id` includes machine ID — globally unique across all machines.
- `machines_involved` is updated each time a new machine contributes.
- `insights` is a running list of learnings — agents read the last N to inform strategy.
- `last_checkpoint` is updated every time the manifest is saved.
