# OmegaLoop

**Live. Die. Repeat.**

Distributed, crash-resilient, persistent autonomous loops for any git repository.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) and *Edge of Tomorrow* — agents loop relentlessly against a problem, learning each iteration, until they win. Runs across multiple machines on the same repo with no collision.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  OS Scheduler (cron / launchd / Task Scheduler)         │
│  Fires every N minutes, survives reboots                │
└────────────────────────┬────────────────────────────────┘
                         │ run-tick
┌────────────────────────▼────────────────────────────────┐
│  omegaloop daemon                                       │
│  Reads ~/.omegaloop/tasks/<id>.json                     │
│  Reads OmegaLoop/<session>/manifest.json                │
│  Builds prompt with skill context + session state       │
└────────────────────────┬────────────────────────────────┘
                         │ claude -p / agent-framework
┌────────────────────────▼────────────────────────────────┐
│  Claude / Agent Framework                               │
│  Reads SKILL.md → runs N experiments in worktree        │
│  Checkpoints → exits                                    │
└────────────────────────┬────────────────────────────────┘
                         │ git add + commit
┌────────────────────────▼────────────────────────────────┐
│  OmegaLoop/ folder in repo (committed to git)           │
│  manifest.json + wins/ + logs/                          │
│  Pushed to remote → other machines pull + continue      │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### From Claude CLI (skill mode)
```bash
/omegaloop "Make the caching layer faster"
```

### Durable daemon (survives reboots)
```bash
python omegaloop/orchestrator/daemon.py add \
  --repo ~/repos/myproject --prompt "Optimize caching" --interval 10m
python omegaloop/orchestrator/daemon.py list
```

### Multi-machine (same repo, no collision)
```bash
# Machine A                          # Machine B
git clone org/repo && cd repo        git clone org/repo && cd repo
omegaloop add --prompt "Fix X"       omegaloop add --prompt "Fix Y"
# Both work simultaneously, results merge via git
```

## Loop Types

| Type | Terminates? | Example |
|---|---|---|
| `converge` | When done condition met | `"TDD: find bugs, write tests, fix, until green"` |
| `monitor` | Never (manual stop) | `"Watch PR #1234, enrich pr1234.md"` |
| `research` | At max experiments | `"Find a headless browser solution"` |
| `optimize` | At max or plateau | `"Improve DataGrid load time"` |

## License

MIT

*"The Omega controls the loop. The loop controls the outcome."*

## Documentation

Full docs in [`docs/`](docs/README.md):

- [Architecture](docs/architecture.md) — system diagram, components, data flow
- [Design Decisions](docs/design.md) — trade-offs and rationale
- [Loop Types](docs/loop-types.md) — converge, monitor, research, optimize
- [Distributed](docs/distributed.md) — multi-machine, collision avoidance
- [Daemon](docs/daemon.md) — OS scheduler, tick lifecycle
- [Manifest Schema](docs/manifest-schema.md) — JSON schema reference
- [Getting Started](docs/getting-started.md) — installation, first loop
- [Troubleshooting](docs/troubleshooting.md) — common issues, recovery

## Tests

```bash
pip install pytest
pytest tests/ -v              # 78 unit tests
python tests/evals/run_evals.py  # 18 type detection evals
```

See [`tests/README.md`](tests/README.md) for details.
