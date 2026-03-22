# OmegaLoop Tests

## Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures (temp repos, manifests)
├── test_machine_id.py           # Machine ID generation, uniqueness, stability
├── test_git_ops.py              # Worktree create/remove/revert/commit
├── test_session_manager.py      # Session CRUD, manifest I/O, discover, resume
├── test_manifest.py             # Schema validation, save/load roundtrip
├── test_daemon.py               # Interval parsing, cron gen, type inference, termination
├── test_distributed.py          # Multi-machine ID collision, additive results
├── evals/                       # Skill evals (agent behavior tests)
│   ├── README.md
│   ├── eval_converge.md         # Expected behavior for converge loops
│   ├── eval_monitor.md          # Expected behavior for monitor loops
│   └── eval_prompts.json        # Test prompts with expected type detection
└── fixtures/
    ├── manifest_v2_full.json    # Complete manifest for testing
    ├── manifest_v2_minimal.json # Minimal valid manifest
    ├── task_config.json         # Sample daemon task config
    └── loops_config.json        # Sample multi-project config
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_machine_id.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=orchestrator --cov-report=term-missing
```

## What the Tests Cover

### Infrastructure tests (unit)
These test the core mechanics — git operations, session management, manifest schema,
daemon logic. They use temporary git repos created in fixtures and don't call any LLMs.

| File | What it tests | LLM needed? |
|------|--------------|-------------|
| `test_machine_id.py` | ID generation, stability, uniqueness | No |
| `test_git_ops.py` | Worktree lifecycle, revert, commit | No |
| `test_session_manager.py` | Session CRUD, discover, checkpoint | No |
| `test_manifest.py` | Schema validation, roundtrip, migration | No |
| `test_daemon.py` | Parsing, cron gen, type detection, termination | No |
| `test_distributed.py` | Multi-machine simulation, no-collision proof | No |

### Skill evals (behavioral)
These test whether the SKILL.md produces correct agent behavior. They require an LLM
(Claude CLI or Agent Framework). See `evals/README.md`.

## Adding Tests

When modifying OmegaLoop infrastructure:
1. Add a test that covers the new behavior
2. Run `pytest tests/ -v` to verify nothing regressed
3. If adding a new loop type, add an eval in `evals/`
