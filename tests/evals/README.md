# Skill Evals

These are behavioral tests that verify the SKILL.md produces correct agent behavior.
Unlike the unit tests in `tests/`, these require an actual LLM (Claude CLI or Agent Framework).

## How Evals Work

Each eval provides a prompt, expected loop type detection, expected agent behavior,
and pass/fail criteria. The eval runner fires `claude -p` with the SKILL.md loaded,
captures the output, and checks against expectations.

## Running Evals

```bash
# Run all evals (requires claude CLI)
python tests/evals/run_evals.py

# Run a specific eval
python tests/evals/run_evals.py --eval converge

# Dry run (show prompts without firing LLM)
python tests/evals/run_evals.py --dry-run
```

## Eval Files

| File | Tests |
|------|-------|
| `eval_prompts.json` | Type auto-detection: given a prompt, does the agent pick the right loop type? |
| `eval_converge.md` | Converge loop: does it write tests before fixes? Does it checkpoint? |
| `eval_monitor.md` | Monitor loop: does it exit quickly when nothing new? Does it enrich the doc? |

## Adding Evals

1. Add a test case to `eval_prompts.json` for type detection
2. For behavioral evals, create an `eval_<type>.md` with:
   - Setup: what the test repo should contain
   - Prompt: what to send to the agent
   - Expected: what the agent should do
   - Pass criteria: how to verify

## eval_prompts.json Format

```json
[
  {
    "prompt": "Test the program, find bugs, write tests, fix them",
    "expected_type": "converge",
    "notes": "TDD keywords should trigger converge"
  }
]
```
