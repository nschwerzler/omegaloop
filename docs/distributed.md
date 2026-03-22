# Distributed Multi-Machine Operation

OmegaLoop is designed for 5+ machines to work on the same repo simultaneously.

## How Collision Is Prevented

Every ID contains a **machine fingerprint** — a 6-char hash of hostname + MAC address:

```
Session ID:     20260322-143052-a3f91b-c4d2
                                ^^^^^^ machine ID

Worktree branch: ol/20260322-143052-a3f91b-c4d2
Experiment ID:   exp-007-a3f91b
Win folder:      wins/win-001-a3f91b/
```

Two machines will NEVER produce the same session ID, branch name, experiment ID, or
win folder — even if started at the same second with the same prompt.

## Machine Identity

```python
MACHINE_ID = hashlib.sha256(f"{platform.node()}-{uuid.getnode()}".encode()).hexdigest()[:6]
```

| Property | Source | Stable? |
|----------|--------|---------|
| hostname | `platform.node()` | Yes, across reboots |
| MAC address | `uuid.getnode()` | Yes, per NIC |
| Combined hash | SHA256 → 6 chars | 16.7M possible values |

## Coordination via Git

```
Machine A                    Remote (GitHub/ADO)              Machine B
─────────                    ──────────────────               ─────────
create session A
commit OmegaLoop/ ──push──►  OmegaLoop/session-A/
                                                    ◄──pull── sees session A
                                                              create session B
                              OmegaLoop/session-B/ ◄──push──  commit OmegaLoop/
pull ──────────────►  sees both sessions
```

The orchestrator calls `git pull --rebase --autostash` before starting a tick and
`git push` every 5 experiments. This keeps machines loosely synchronized.

## Same Session, Multiple Machines

When Machine B resumes a session that Machine A created:

1. `omegaloop --resume` scans `OmegaLoop/*/manifest.json`
2. Finds session `20260322-143052-a3f91b-c4d2` with status `looping`
3. Reads `experiment_count: 25, win_count: 3`
4. Creates worktree from branch `ol/20260322-143052-a3f91b-c4d2` locally
5. Continues from experiment 26, but IDs are `exp-026-b7e2c0` (Machine B's ID)

Machine A may still be running the same session. Both machines produce valid experiments.
The manifest's `machines_involved` array tracks all contributors.

## Merge Safety

Each machine writes to non-overlapping paths:
- Session folders already contain machine ID
- Experiment IDs contain machine ID
- Win folders: `win-001-a3f91b` vs `win-001-b7e2c0`

The only shared file is `manifest.json`. In practice, manifest conflicts are rare because
each machine appends to the `experiments` array. If a conflict does occur on pull:
- Take the manifest with the higher `experiment_count`
- Merge the `experiments` arrays (they're append-only, IDs are unique)

## Setup on a New Machine

```bash
# Clone the repo (OmegaLoop/ folder comes with it)
git clone git@github.com:org/repo.git
cd repo

# Option 1: Resume existing sessions
python omegaloop/orchestrator/daemon.py resume --all

# Option 2: Start a new loop (won't collide with existing)
python omegaloop/orchestrator/daemon.py add \
  --repo . --prompt "Optimize caching" --interval 10m
```

## Network Requirements

- Machines need `git push/pull` access to the remote
- No direct machine-to-machine communication needed
- Works over VPN, SSH tunnels, or any git transport
- Tolerant of intermittent connectivity (git pull/push failures are logged but don't crash)
