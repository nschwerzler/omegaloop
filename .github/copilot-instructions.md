# OmegaLoop

Autonomous research loop engine for git repositories.

## Git

- **Remote**: `https://github.com/nschwerzler/omegaloop.git`
- **Account**: `nschwerzler` (this is the correct account for this repo)
- **Branch**: `main` (push directly, no feature branches)

## Project Structure

- `orchestrator/daemon.py` — CLI + OS scheduler (cron/launchd/Task Scheduler)
- `orchestrator/engine.py` — GitOps, SessionManager, ResearchLoop, agent backends
- `SKILL.md` — Agent instructions (read by Claude/Copilot during ticks)
- `.claude/commands/omegaloop.md` — Claude CLI slash command
- `.github/copilot/omegaloop.md` — GitHub Copilot instruction
- `references/` — Protocol details, Agent Framework setup
- `scripts/` — Shell helpers (init, commit-win, cleanup, dashboard generator)
- `tests/` — 78 unit tests + 18 type detection evals

## Language

Python 3.11+. No required dependencies for core (pytest for tests, agent-framework optional).

## Testing

```bash
pytest tests/ -v              # 78 unit tests
python tests/evals/run_evals.py  # 18 type detection evals
```
