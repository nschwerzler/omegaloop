# Troubleshooting

## Common Issues

### "claude: command not found"
Claude CLI is not installed or not on PATH.
```bash
# Check
which claude
# Install: https://docs.anthropic.com/claude-code
```

### Loop not firing after reboot
Check that the OS scheduler entry exists:
```bash
# Linux/WSL
crontab -l | grep OL_TASK

# macOS
ls ~/Library/LaunchAgents/com.omegaloop.*

# Windows
schtasks /query /tn "OmegaLoop\*"
```

If missing, resume:
```bash
python omegaloop/orchestrator/daemon.py resume --all
```

### Worktree disappeared after reboot
Normal. Worktrees are local-only. The daemon recreates them on the next tick
from the `ol/{session-id}` branch.

### Git merge conflict on manifest.json
When two machines push conflicting manifest updates:
```bash
cd /your/repo
git pull --rebase
# If conflict: take the manifest with higher experiment_count
# The experiments array is append-only, so manual merge is straightforward
git add OmegaLoop/
git rebase --continue
```

### "No resumable sessions found"
The OmegaLoop/ folder doesn't have any sessions with status `looping` or `paused`.
Check:
```bash
ls OmegaLoop/*/manifest.json
cat OmegaLoop/*/manifest.json | python3 -c "
import json,sys
for line in sys.stdin:
    try:
        m = json.loads(line)
        print(f\"{m['session_id']}: {m['status']}\")
    except: pass
"
```

### Experiments producing no wins
After 10+ consecutive no-wins, the agent rotates strategy automatically.
If still stuck after 20+, it pauses. Check the insights in the manifest:
```bash
cat OmegaLoop/{session}/manifest.json | python3 -c "
import json,sys; m=json.load(sys.stdin)
print(f'Experiments: {m[\"experiment_count\"]}')
print(f'Wins: {m[\"win_count\"]}')
print(f'Strategy: {m[\"current_strategy\"]}')
print(f'No-win streak: {m[\"consecutive_no_wins\"]}')
for i in m.get('insights',[]): print(f'  - {i}')
"
```

### Tick timeout (30 minutes)
The daemon kills the agent subprocess after 30 minutes. This usually means the
agent is stuck in a long build or test cycle. Consider:
- Reducing `--batch` size (fewer experiments per tick)
- Adding timeouts to your test commands
- Using a faster model

## Recovery Procedures

### Corrupt manifest
```bash
# The manifest is committed to git, so check history
cd /your/repo
git log --oneline OmegaLoop/{session}/manifest.json
git checkout HEAD~1 -- OmegaLoop/{session}/manifest.json
```

### Remove all OmegaLoop state (nuclear option)
```bash
# Remove all worktrees
python omegaloop/scripts/ol-cleanup.sh worktrees

# Remove all daemon tasks
for f in ~/.omegaloop/tasks/*.json; do
  id=$(basename "$f" .json)
  python omegaloop/orchestrator/daemon.py remove "$id"
done

# Optionally remove OmegaLoop/ folder from repo
rm -rf OmegaLoop/
git add -A && git commit -m "Remove OmegaLoop data"
```
