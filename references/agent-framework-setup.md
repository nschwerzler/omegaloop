# Distributed Orchestrator Setup

The OmegaLoop orchestrator runs multiple research loops concurrently across projects
and machines. It uses Microsoft Agent Framework (Python) for LLM calls and git for
state coordination.

---

## Quick Start

```bash
# Install
pip install agent-framework --pre azure-identity

# Single project
python -m orchestrator.engine --repo ~/repos/winapp-sdk \
  --prompt "Optimize the caching layer" --max 50

# Resume after reboot (picks up ALL incomplete sessions)
python -m orchestrator.engine --repo ~/repos/winapp-sdk --resume

# Multi-project from config file
python -m orchestrator.engine --config loops.json

# Use Claude CLI instead of Azure
python -m orchestrator.engine --repo . --prompt "Fix error handling" --backend claude
```

## Multi-Machine Architecture

The orchestrator is designed so 5+ machines can work on the same repo simultaneously.

### How collision is prevented

Every ID contains a **machine fingerprint** (6-char hash of hostname + MAC):

```
Session ID:  20260322-143052-a3f91b-c4d2
                                ^^^^^^
                                machine ID

Worktree branch: ar/20260322-143052-a3f91b-c4d2
Experiment ID:   exp-007-a3f91b
```

Two machines will NEVER produce the same session ID, branch name, or experiment ID
even if started at the same second with the same prompt.

### How machines coordinate

Git is the coordination layer. No central server needed.

```
Machine A                    Remote (GitHub/ADO)              Machine B
─────────                    ──────────────────               ─────────
create session               
commit AR/ to main  ──push──►  AR/session-A-xxx/
                                                    ◄──pull── sees session A
                                                              creates session B
                               AR/session-B-yyy/   ◄──push──  commit AR/
pull ──────────────►  sees both sessions
```

Each machine periodically pushes its `OmegaLoop/` folder to remote.
Other machines pull-rebase to see the latest wins.

### Additive results

When machine A finds a win, it commits:
```
OL: win-001 in 20260322-143052-a3f91b-c4d2 [a3f91b] - ConcurrentDict fix
```

When machine B finds a win in the SAME session (if both resumed it):
```
OL: win-002 in 20260322-143052-a3f91b-c4d2 [b7e2c0] - Hash precompute
```

The experiment IDs include the machine ID so there's no collision even if both
machines run experiment #7 at the same time (`exp-007-a3f91b` vs `exp-007-b7e2c0`).

## Crash Resilience

### What happens on reboot

1. Machine restarts
2. User runs `python -m orchestrator.engine --resume`
3. Orchestrator scans `OmegaLoop/*/manifest.json` for `status: looping|paused`
4. For each: recreates worktree if deleted, reads experiment count, continues from last checkpoint
5. Every single experiment is checkpointed to disk before the next starts

### What's persisted in git (survives disk loss)

- `manifest.json` — full session state, experiment log, win records
- `wins/` — diffs, summaries, changed files
- `research-prompt.md` — the original prompt

### What's local only (recreated on resume)

- `.git/ol-worktrees/` — the actual worktree checkout (recreated from branch)

## Configuration

### Environment variables

```bash
# For agent-framework backend (Azure AI Foundry)
export AZURE_AI_PROJECT_ENDPOINT="https://your-project.services.ai.azure.com"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4.1"

# For Claude CLI backend
# (just needs `claude` on PATH)

# For Copilot CLI backend
# (just needs `gh copilot` on PATH)
```

### Multi-project config (loops.json)

```json
{
  "backend": "agent-framework",
  "projects": [
    {
      "repo": "/path/to/repo1",
      "prompt": "Research prompt for repo1",
      "max": 50,
      "resume": true
    },
    {
      "repo": "/path/to/repo2",
      "prompt": "Research prompt for repo2",
      "max": 30,
      "resume": true
    }
  ]
}
```

`"resume": true` means: if there's an existing incomplete session for this repo,
resume it instead of creating a new one. This is the recommended setting.

## Agent Framework Workflow (Advanced)

For more complex orchestration (parallel hypothesis testing, specialist agents),
use the Agent Framework workflow engine with checkpointing:

```python
from agent_framework import WorkflowBuilder
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

client = AzureOpenAIResponsesClient(
    project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    deployment_name="gpt-4.1",
    credential=AzureCliCredential(),
)

researcher = client.as_agent(
    name="Researcher",
    instructions="Generate experiment hypotheses. Return JSON with hypothesis and target_files.",
)

coder = client.as_agent(
    name="Coder",
    instructions="Implement the hypothesis as code changes. Return unified diff.",
)

evaluator = client.as_agent(
    name="Evaluator",
    instructions="Evaluate the change. Return JSON with verdict (win/discard) and reasoning.",
)

workflow = SequentialBuilder(participants=[researcher, coder, evaluator]).build()

# Run with checkpointing for crash resilience
from agent_framework import FileCheckpointStorage

storage = FileCheckpointStorage("./OmegaLoop/.checkpoints/")

async for event in workflow.run(
    "Optimize the caching layer in src/cache/",
    checkpoint_storage=storage,
    stream=True,
):
    if event.type == "output":
        print(event.data)
```

The workflow engine saves state after each agent completes, so if the process
crashes mid-pipeline, it resumes from the last completed agent on restart.
