# Skill Protocol

The SKILL.md file is the agent's instruction manual. When the daemon fires `claude -p`,
the prompt tells Claude to read SKILL.md first. This document explains how SKILL.md
drives agent behavior.

## Prompt Construction

The daemon builds a prompt like:

```
You are running OmegaLoop. Read the skill at /path/to/SKILL.md first.

RESUME session {session-id} in repo {repo}.
Manifest at: {manifest-path}.
Current state: {N} experiments done, {M} wins.

LOOP TYPE: converge
GOAL: Test the program. Find bugs, write failing tests, fix them.
DONE CONDITION: all tests pass, no new bugs in 3 consecutive passes.

This tick: Run up to 5 iterations...

Follow the skill protocol exactly. Do NOT ask for permission.
Do the work, checkpoint, exit.
```

## What the Agent Does

1. **Reads SKILL.md** — understands the protocol, loop types, critical rules
2. **Reads manifest.json** — understands current session state
3. **Reads protocol.md** (if needed) — detailed evaluation framework, strategy rotation
4. **Executes experiments** in the worktree per the loop type instructions
5. **Updates manifest.json** — appends experiments, updates counters
6. **Commits wins** to the OmegaLoop/ folder on main branch
7. **Exits** — daemon handles the next tick

## Critical Rules (from SKILL.md)

1. Never modify main branch code directly — all experiments in worktrees
2. Always commit OmegaLoop folder changes to main — wins are research output
3. Never stop to ask permission — loop until interrupted or done
4. Log everything — even failures are valuable data
5. Be bold — try non-obvious approaches
6. Checkpoints are sacred — save state before next experiment
7. OmegaLoop folder is source of truth
8. Monitors never auto-stop — only manual pause/remove
9. Converge loops verify done-ness — meet condition N times before stopping
10. Each tick is self-contained — get context from manifest, do work, checkpoint, exit

## Progressive Disclosure

```
SKILL.md (always loaded, ~500 lines)
  ├── references/protocol.md (on demand, deep details)
  └── references/agent-framework-setup.md (on demand, AF setup)
```
