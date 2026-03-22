# Getting Started

## Prerequisites

- Python 3.11+
- Git
- One of: `claude` CLI, Azure AI Foundry subscription, GitHub Copilot

## Install

```bash
# Clone or copy the omegaloop/ skill folder into your project or skills directory
git clone https://github.com/yourname/omegaloop.git

# For Agent Framework backend (optional)
pip install agent-framework --pre azure-identity
```

## Your First Loop

### Option A: Durable daemon (recommended)

```bash
cd ~/repos/your-project

# Add a research loop — starts running automatically
python omegaloop/orchestrator/daemon.py add \
  --repo . \
  --prompt "Test the program. Find bugs, write failing tests, fix them." \
  --type converge \
  --interval 10m

# Check it's registered
python omegaloop/orchestrator/daemon.py list

# Watch the logs
python omegaloop/orchestrator/daemon.py logs <task-id>
```

Close your terminal. Reboot. The loop keeps running.

### Option B: Claude CLI skill mode

```bash
cd ~/repos/your-project

# If omegaloop is in your skills directory:
/omegaloop "Make the caching layer faster"

# Or point Claude at the skill:
claude -p "Read omegaloop/SKILL.md and then run:
/omegaloop 'Find and fix error handling gaps in src/api/'"
```

### Option C: Python orchestrator (long-running process)

```bash
cd ~/repos/your-project
python -m orchestrator.engine \
  --repo . \
  --prompt "Create a design.md for the auth system" \
  --max 20
```

## Common Patterns

### TDD Bug Hunting
```bash
python omegaloop/orchestrator/daemon.py add --repo . --type converge \
  --prompt "Test everything. Find bugs, write failing tests first (TDD), fix them." \
  --done-condition "all tests pass, no new bugs in 3 passes"
```

### PR Monitor
```bash
python omegaloop/orchestrator/daemon.py add --repo . --type monitor \
  --interval 30m \
  --prompt "Monitor PR #1234. Suggest fixes for comments/failures in pr1234.md." \
  --target-doc "pr1234.md"
```

### Performance Optimization
```bash
python omegaloop/orchestrator/daemon.py add --repo . --type optimize \
  --prompt "Improve DataGrid load time. Measure with: npm run bench" \
  --max 100
```

### Research (headless browser solution)
```bash
python omegaloop/orchestrator/daemon.py add --repo . --type research \
  --prompt "Find a headless browser for SSO sites that limits agent context. Produce solution.md." \
  --max 30
```

### Daily enrichment
```bash
python omegaloop/orchestrator/daemon.py add --repo . --type monitor \
  --schedule "0 9 * * 1-5" \
  --prompt "Check team updates about Project Cosmos. Enrich docs/cosmos-status.md."
```

## What Happens in Your Repo

After a few ticks, you'll see:

```
your-project/
├── OmegaLoop/
│   ├── 20260322-143052-a3f91b-c4d2/
│   │   ├── manifest.json
│   │   ├── research-prompt.md
│   │   ├── wins/
│   │   │   ├── win-001/summary.md
│   │   │   └── win-002/summary.md
│   │   └── logs/
│   └── omegaloop.html              # Dashboard (after running generate-hub.py)
```

## Managing Loops

```bash
# List all loops
python omegaloop/orchestrator/daemon.py list

# Pause a loop (keeps config, removes from scheduler)
python omegaloop/orchestrator/daemon.py pause abc12345

# Resume
python omegaloop/orchestrator/daemon.py resume abc12345

# Remove entirely
python omegaloop/orchestrator/daemon.py remove abc12345

# Resume all loops (e.g., after cloning on new machine)
python omegaloop/orchestrator/daemon.py resume --all
```
