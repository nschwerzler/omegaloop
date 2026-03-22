# Architecture

## System Overview

OmegaLoop is a three-layer system: a **daemon** that schedules ticks via the OS, an
**orchestrator** that manages sessions and git state, and **agents** (Claude CLI,
Agent Framework, Copilot) that do the actual research work.

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: OS Scheduler (Durable)                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │  cron    │ │ launchd  │ │ Task     │  Survives reboots.      │
│  │ (Linux)  │ │ (macOS)  │ │ Sched    │  Fires run-tick at      │
│  │          │ │          │ │ (Win)    │  configured interval.   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘                        │
│       └─────────────┼───────────┘                               │
│                     ▼                                            │
│  LAYER 2: Daemon + Orchestrator (Python)                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  daemon.py                                              │    │
│  │  - Reads task config from ~/.omegaloop/tasks/<id>.json  │    │
│  │  - Reads manifest from OmegaLoop/<session>/manifest.json│    │
│  │  - Checks termination conditions per loop type          │    │
│  │  - Builds type-specific prompt                          │    │
│  │  - Fires agent subprocess                               │    │
│  │  - Post-tick state checks (converge streak, etc)        │    │
│  └───────────────────────┬─────────────────────────────────┘    │
│  ┌───────────────────────▼─────────────────────────────────┐    │
│  │  engine.py                                              │    │
│  │  - GitOps: worktree create/revert/commit, push/pull     │    │
│  │  - SessionManager: create/load/discover/checkpoint      │    │
│  │  - ResearchLoop: experiment cycle per session           │    │
│  │  - Orchestrator: concurrent session runner, signals     │    │
│  └───────────────────────┬─────────────────────────────────┘    │
│                          ▼                                       │
│  LAYER 3: Agent Backends (LLM Compute)                          │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐               │
│  │ claude -p   │ │ Agent Fwk    │ │ gh copilot │               │
│  │ (Claude CLI)│ │ (Azure/AOAI) │ │ (Copilot)  │               │
│  └─────────────┘ └──────────────┘ └────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

## Data Model

```
~/.omegaloop/                    # Daemon state (per-machine)
├── tasks/
│   ├── a1b2c3d4.json            # Task config (one per loop)
│   └── e5f6g7h8.json
├── logs/
│   ├── a1b2c3d4.log            # Tick output logs
│   └── e5f6g7h8.log
└── bin/                         # Windows .bat wrappers

YourRepo/                        # Research state (in git, shared)
├── OmegaLoop/
│   ├── omegaloop.html           # Dashboard
│   ├── .gitignore
│   ├── {session-id}/
│   │   ├── manifest.json        # Session brain
│   │   ├── research-prompt.md   # Human-readable goal
│   │   ├── logs/                # Per-experiment logs
│   │   ├── wins/                # Winning artifacts
│   │   │   └── win-001/
│   │   │       ├── summary.md
│   │   │       ├── changes.diff
│   │   │       └── commit-hash.txt
│   │   └── checkpoints/
│   └── {another-session}/
├── .git/
│   └── ol-worktrees/            # LOCAL ONLY — not committed
│       └── {session-id}/        # Isolated checkout for experiments
└── [rest of repo]
```

## Component Responsibilities

### daemon.py
- Registers/unregisters OS scheduler entries
- Reads task config, decides whether to fire
- Checks termination conditions BEFORE firing agent
- Builds loop-type-specific prompts for the agent
- Fires `claude -p` or orchestrator subprocess
- Post-tick state checks (converge streak, monitor no-change)
- Links first tick to session ID after creation

### engine.py
- `GitOps`: all git/worktree operations, push/pull
- `SessionManager`: CRUD for sessions, manifest I/O, win storage
- `ResearchLoop`: single-session experiment cycle (used by orchestrator mode)
- `Orchestrator`: concurrent multi-session runner with signal handling
- `Manifest` dataclass: session state schema
- Agent backends: `AgentFrameworkBackend`, `ClaudeCliBackend`, `CopilotCliBackend`

### SKILL.md
- Agent instructions — read by Claude/Copilot when running a tick
- Defines the research protocol, loop types, evaluation framework
- References `references/protocol.md` for deep details
- References `references/agent-framework-setup.md` for AF setup

### generate-hub.py
- Reads all `manifest.json` files from `OmegaLoop/` subfolders
- Produces a self-contained HTML dashboard
- No server needed — static file

## Tick Lifecycle

```
OS Scheduler fires
    │
    ▼
daemon.py run-tick <task-id>
    │
    ├── Load task config from ~/.omegaloop/tasks/<id>.json
    ├── Load manifest from OmegaLoop/<session>/manifest.json (if exists)
    ├── Check termination: completed? max reached? converge done?
    │   └── If done → remove from OS scheduler, exit
    ├── Build prompt (type-specific: converge/monitor/research/optimize)
    ├── Fire agent: claude -p "<prompt>" --dangerously-skip-permissions
    │   │
    │   └── Agent reads SKILL.md → runs experiments in worktree
    │       ├── Hypothesize → Implement → Evaluate → Keep/Discard
    │       ├── Writes wins to OmegaLoop/<session>/wins/
    │       ├── Updates manifest.json
    │       ├── Commits OmegaLoop/ changes to main branch
    │       └── Exits
    │
    ├── Post-tick: re-read manifest, check type-specific state
    │   ├── converge: increment/reset done_streak
    │   ├── monitor: track no_change_streak
    │   └── optimize: (manifest tracks metric_history)
    ├── Link to session ID if first tick
    ├── Update task metadata (last_tick, tick_count)
    └── Exit (OS scheduler fires again at next interval)
```

## Isolation Model

Experiments NEVER touch the main branch directly:

1. Session init creates branch `ol/{session-id}` from current HEAD
2. Worktree checked out at `.git/ol-worktrees/{session-id}`
3. All code changes happen in the worktree
4. If experiment is a WIN: commit in worktree, copy artifacts to `OmegaLoop/` on main
5. If experiment is a DISCARD: `git checkout -- .` in worktree
6. `OmegaLoop/` folder (manifests, wins, logs) is committed to main branch
7. Worktree is local-only — deleted on cleanup, recreated on resume
