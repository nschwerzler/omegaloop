# Daemon

The daemon (`orchestrator/daemon.py`) registers research loops with the OS scheduler
so they survive reboots and run without a terminal.

## Commands

```bash
omegaloop install                     # one-time setup: create ~/.omegaloop/
omegaloop add --repo . --prompt "..." # create a new loop
omegaloop list                        # show all loops
omegaloop logs <task-id>              # tail logs for a task
omegaloop pause <task-id>             # stop OS scheduler, keep config
omegaloop resume <task-id>            # re-register with OS scheduler
omegaloop resume --all                # resume all paused/active loops
omegaloop remove <task-id>            # delete from scheduler + config
omegaloop run-tick <task-id>          # INTERNAL: called by OS scheduler
```

## Task Config

Stored at `~/.omegaloop/tasks/{task-id}.json`:

```json
{
  "id": "a1b2c3d4",
  "repo": "/home/nick/repos/winapp-sdk",
  "prompt": "Optimize caching",
  "loop_type": "optimize",
  "interval_minutes": 10,
  "cron_expr": "*/10 * * * *",
  "max": 50,
  "batch_size": 5,
  "backend": "claude",
  "status": "active",
  "machine_id": "a3f91b",
  "created_at": "2026-03-22T14:30:52Z",
  "last_tick": "2026-03-22T15:40:00Z",
  "tick_count": 7,
  "session_id": "20260322-143052-a3f91b-c4d2",
  "done_condition": null,
  "done_streak": 0,
  "done_streak_target": 3,
  "target_doc": null,
  "no_change_streak": 0
}
```

## Platform Support

| Platform | Scheduler | Persistence | Install |
|----------|-----------|-------------|---------|
| Linux / WSL | crontab | Survives reboot | Crontab entry |
| macOS | launchd | Survives reboot, runs on login | Plist in ~/Library/LaunchAgents/ |
| Windows | Task Scheduler | Survives reboot | schtasks command + .bat wrapper |

## Scheduling

Both interval and cron syntaxes are supported:

```bash
--interval 10m                # every 10 minutes → */10 * * * *
--interval 1h                 # every hour → 0 * * * *
--interval 6h                 # every 6 hours → 0 */6 * * *
--interval 1d                 # daily → 0 0 * * *
--schedule "0 9 * * 1-5"     # weekdays at 9am (raw cron)
--schedule "0 9,17 * * *"    # twice daily
--schedule "0 8 * * 1"       # Mondays at 8am
```

`--schedule` overrides `--interval` and is passed directly to the OS scheduler.

## Termination Logic

Before each tick, the daemon checks termination conditions:

| Loop Type | Auto-Completes When |
|-----------|-------------------|
| converge | `done_streak >= done_streak_target` |
| monitor | NEVER (manual stop only) |
| research | `experiment_count >= max` |
| optimize | `experiment_count >= max` |

When auto-completing, the daemon:
1. Sets manifest status to `completed`
2. Removes the OS scheduler entry
3. Sets task status to `completed`
