#!/usr/bin/env python3
"""
omegaloop — Durable OmegaLoop scheduler.

Registers research loops with the OS scheduler (cron/launchd/Task Scheduler).
Each tick fires a `claude -p` session that runs one experiment batch, checkpoints,
and exits. The OS scheduler fires the next tick automatically.

Survives reboots. No terminal required. Clone repo on new machine → omegaloop resume → goes.

Usage:
    omegaloop add --repo ~/repos/winapp-sdk --prompt "Optimize caching" --interval 5m
    omegaloop add --repo ~/repos/sbom5000 --prompt "Fix error handling" --interval 10m --max 30
    omegaloop list
    omegaloop logs <task-id>
    omegaloop pause <task-id>
    omegaloop resume [task-id | --all]
    omegaloop remove <task-id>
    omegaloop run-tick <task-id>   # Called by the OS scheduler — not for humans
    omegaloop install               # One-time: ensure daemon infrastructure exists
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OL_HOME = Path(os.environ.get("OL_HOME", Path.home() / ".omegaloop"))
OL_TASKS = OL_HOME / "tasks"
OL_LOGS = OL_HOME / "logs"
OL_BIN = OL_HOME / "bin"
OL_LOCKS = OL_HOME / "locks"
OL_HEARTBEATS = OL_HOME / "heartbeats"

TICK_TIMEOUT_SECONDS = 2400  # 40 min — stale lock threshold (tick timeout is 30min)

MACHINE_ID = hashlib.sha256(
    f"{platform.node()}-{uuid.getnode()}".encode()
).hexdigest()[:6]

SKILL_DIR = Path(__file__).parent.parent  # omegaloop/ skill root

# ---------------------------------------------------------------------------
# Task registry — JSON file per task, lives in ~/.omegaloop/tasks/
# ---------------------------------------------------------------------------

def task_path(task_id: str) -> Path:
    return OL_TASKS / f"{task_id}.json"

def gen_task_id(repo: str, prompt: str) -> str:
    """8-char ID: hash of repo+prompt+machine, human-greppable."""
    raw = f"{repo}-{prompt}-{MACHINE_ID}-{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]

def load_task(task_id: str) -> dict:
    p = task_path(task_id)
    if not p.exists():
        raise FileNotFoundError(f"Task {task_id} not found")
    return json.loads(p.read_text())

def save_task(task: dict):
    task_path(task["id"]).write_text(json.dumps(task, indent=2))

def list_tasks() -> list[dict]:
    tasks = []
    if OL_TASKS.exists():
        for f in sorted(OL_TASKS.glob("*.json")):
            try:
                tasks.append(json.loads(f.read_text()))
            except Exception:
                pass
    return tasks

# ---------------------------------------------------------------------------
# Interval parsing (matches Claude Code's /loop syntax)
# ---------------------------------------------------------------------------

def parse_interval(s: str) -> int:
    """Parse interval string like '5m', '1h', '30s', '2d' → minutes (min 1)."""
    s = s.strip().lower()
    if not s:
        return 1
    try:
        if s.endswith("s"):
            n = int(s[:-1]) if len(s) > 1 else 0
            return max(1, n // 60 + (1 if n % 60 else 0))
        elif s.endswith("m"):
            n = int(s[:-1]) if len(s) > 1 else 0
            return max(1, n)
        elif s.endswith("h"):
            n = int(s[:-1]) if len(s) > 1 else 0
            return max(1, n * 60)
        elif s.endswith("d"):
            n = int(s[:-1]) if len(s) > 1 else 0
            return max(1, n * 1440)
        else:
            return max(1, int(s))
    except ValueError:
        return 1

def interval_to_cron(minutes: int) -> str:
    """Convert interval in minutes to a cron expression."""
    if minutes < 60:
        return f"*/{minutes} * * * *"
    elif minutes < 1440:
        hours = minutes // 60
        return f"0 */{hours} * * *"
    else:
        return f"0 0 */{minutes // 1440} * *"

# ---------------------------------------------------------------------------
# OS scheduler integration
# ---------------------------------------------------------------------------

def get_platform() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "launchd"
    elif s == "linux":
        # Check if WSL
        if "microsoft" in platform.release().lower():
            return "cron"  # WSL uses cron
        return "cron"
    elif s == "windows":
        return "taskscheduler"
    return "cron"

def get_python() -> str:
    """Get the absolute path to the Python interpreter."""
    return sys.executable

def get_daemon_script() -> str:
    """Get the absolute path to this script."""
    return str(Path(__file__).resolve())

# -- Cron (Linux / WSL) --

def cron_remove(task_id: str):
    """Remove the cron entry for this task."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return
    lines = [l for l in result.stdout.strip().split("\n") if f"OL_TASK_{task_id}" not in l]
    new_crontab = "\n".join(l for l in lines if l.strip()) + "\n"
    subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)

# -- Launchd (macOS) --

def launchd_plist_path(task_id: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.omegaloop.{task_id}.plist"

def launchd_install(task: dict):
    task_id = task["id"]
    interval = task["interval_minutes"] * 60  # seconds
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omegaloop.{task_id}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{get_python()}</string>
        <string>{get_daemon_script()}</string>
        <string>run-tick</string>
        <string>{task_id}</string>
    </array>
    <key>StartInterval</key>
    <integer>{interval}</integer>
    <key>StandardOutPath</key>
    <string>{OL_LOGS / task_id}.log</string>
    <key>StandardErrorPath</key>
    <string>{OL_LOGS / task_id}.err.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
    p = launchd_plist_path(task_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(plist)
    subprocess.run(["launchctl", "load", str(p)], check=False)

def launchd_remove(task_id: str):
    p = launchd_plist_path(task_id)
    if p.exists():
        subprocess.run(["launchctl", "unload", str(p)], check=False)
        p.unlink()

# -- Task Scheduler (Windows) --

def taskscheduler_install(task: dict):
    task_id = task["id"]
    interval = task["interval_minutes"]
    cmd = f'"{get_python()}" "{get_daemon_script()}" run-tick {task_id}'
    log_path = str(OL_LOGS / f"{task_id}.log")

    # Create a wrapper bat file
    bat = OL_BIN / f"ar-{task_id}.bat"
    bat.write_text(f'@echo off\n{cmd} >> "{log_path}" 2>&1\n')

    # Register with Task Scheduler
    subprocess.run([
        "schtasks", "/create",
        "/tn", f"OmegaLoop\\{task_id}",
        "/tr", str(bat),
        "/sc", "MINUTE",
        "/mo", str(interval),
        "/f",  # force overwrite
    ], check=False)

def taskscheduler_remove(task_id: str):
    subprocess.run([
        "schtasks", "/delete",
        "/tn", f"OmegaLoop\\{task_id}",
        "/f",
    ], check=False)
    bat = OL_BIN / f"ar-{task_id}.bat"
    if bat.exists():
        bat.unlink()

# -- Dispatcher --

def scheduler_remove(task_id: str):
    plat = get_platform()
    if plat == "cron":
        cron_remove(task_id)
    elif plat == "launchd":
        launchd_remove(task_id)
    elif plat == "taskscheduler":
        taskscheduler_remove(task_id)

# ---------------------------------------------------------------------------
# Tick lock — prevents concurrent ticks on the same task
# ---------------------------------------------------------------------------

def _lock_path(task_id: str) -> Path:
    return OL_LOCKS / f"{task_id}.lock"

def _heartbeat_path(task_id: str) -> Path:
    return OL_HEARTBEATS / f"{task_id}.json"

def acquire_tick_lock(task_id: str) -> bool:
    """Acquire a lock for this task. Returns False if another tick is running."""
    OL_LOCKS.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(task_id)
    if lock.exists():
        try:
            lock_data = json.loads(lock.read_text())
            lock_age = time.time() - lock_data.get("started_at", 0)
            lock_pid = lock_data.get("pid", 0)
            # Check if the process is still alive
            pid_alive = False
            try:
                os.kill(lock_pid, 0)  # signal 0 = check existence
                pid_alive = True
            except (OSError, ProcessLookupError):
                pass
            if pid_alive and lock_age < TICK_TIMEOUT_SECONDS:
                return False  # genuinely running
            # Stale lock — previous tick crashed or timed out
            print(f"  Removing stale lock (age={lock_age:.0f}s, pid={lock_pid}, alive={pid_alive})")
        except (json.JSONDecodeError, ValueError):
            pass  # corrupted lock file, overwrite it
    lock.write_text(json.dumps({
        "pid": os.getpid(),
        "started_at": time.time(),
        "started_iso": datetime.now(timezone.utc).isoformat(),
        "machine_id": MACHINE_ID,
    }))
    return True

def release_tick_lock(task_id: str):
    lock = _lock_path(task_id)
    if lock.exists():
        lock.unlink(missing_ok=True)

def write_heartbeat(task_id: str, phase: str, detail: str = ""):
    """Write a heartbeat file so external tools can detect hangs."""
    OL_HEARTBEATS.mkdir(parents=True, exist_ok=True)
    _heartbeat_path(task_id).write_text(json.dumps({
        "task_id": task_id,
        "pid": os.getpid(),
        "phase": phase,
        "detail": detail,
        "timestamp": time.time(),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "machine_id": MACHINE_ID,
    }))

def clear_heartbeat(task_id: str):
    hb = _heartbeat_path(task_id)
    if hb.exists():
        hb.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# Tick execution — called by the OS scheduler each interval
# ---------------------------------------------------------------------------

def run_tick(task_id: str):
    """Called by cron/launchd/taskscheduler. Runs one experiment batch."""
    task = load_task(task_id)

    if task.get("status") in ("paused", "completed"):
        print(f"[{task_id}] {task['status']}, skipping tick")
        return

    # Acquire lock — skip if another tick is already running
    if not acquire_tick_lock(task_id):
        print(f"[{task_id}] Another tick is already running, skipping")
        return

    repo = task.get("repo")
    if not repo:
        print(f"[{task_id}] ERROR: task config missing 'repo' field, skipping")
        release_tick_lock(task_id)
        return
    session_id = task.get("session_id")
    prompt = task.get("prompt")
    if not prompt:
        print(f"[{task_id}] ERROR: task config missing 'prompt' field, skipping")
        release_tick_lock(task_id)
        return
    max_exps = task.get("max")  # None for monitors
    batch_size = task.get("batch_size", 5)
    backend = task.get("backend", "claude")
    loop_type = task.get("loop_type", "research")

    print(f"[{task_id}] Tick at {datetime.now().isoformat()} type={loop_type}")
    print(f"  repo={repo} session={session_id} batch={batch_size}")

    skill_md = SKILL_DIR / "SKILL.md"

    # --- Build the prompt based on loop type and session state ---

    # Read manifest if session exists
    manifest = None
    if session_id:
        manifest_path = Path(repo) / "OmegaLoop" / session_id / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())

    # Check termination conditions BEFORE running
    if manifest:
        exp_count = manifest.get("experiment_count", 0)
        win_count = manifest.get("win_count", 0)
        status = manifest.get("status", "")

        if status == "completed":
            print(f"  Session completed ({win_count} wins). Auto-removing task.")
            task["status"] = "completed"
            save_task(task)
            scheduler_remove(task_id)
            release_tick_lock(task_id)
            return

        # Max experiments check (not for monitors)
        if max_exps and exp_count >= max_exps:
            print(f"  Max experiments reached ({exp_count}/{max_exps}). Completing.")
            manifest["status"] = "completed"
            manifest_path.write_text(json.dumps(manifest, indent=2))
            task["status"] = "completed"
            save_task(task)
            scheduler_remove(task_id)
            release_tick_lock(task_id)
            return

        # Converge: check done streak
        if loop_type == "converge":
            done_streak = task.get("done_streak", 0)
            target = task.get("done_streak_target", 3)
            if done_streak >= target:
                print(f"  Done condition met {done_streak}/{target} consecutive times. Completing.")
                manifest["status"] = "completed"
                manifest_path.write_text(json.dumps(manifest, indent=2))
                task["status"] = "completed"
                save_task(task)
                scheduler_remove(task_id)
                release_tick_lock(task_id)
                return

    # --- Build the type-specific prompt ---

    context_block = ""
    if manifest:
        context_block = (
            f"Session state: {manifest.get('experiment_count', 0)} experiments done, "
            f"{manifest.get('win_count', 0)} wins.\n"
            f"Recent insights: {json.dumps(manifest.get('insights', [])[-3:])}\n"
        )

    type_instructions = build_type_instructions(task, manifest, context_block)

    if session_id and manifest:
        manifest_path_str = str(Path(repo) / "OmegaLoop" / session_id / "manifest.json")
        exp_num = manifest.get("experiment_count", 0) + 1
        win_num = manifest.get("win_count", 0) + 1
        claude_prompt = (
            f"Do the following research task. Do NOT ask questions, just execute.\n\n"
            f"RESEARCH PROMPT: {prompt}\n"
            f"{context_block}\n"
            f"{type_instructions}\n\n"
            f"Read the manifest at {manifest_path_str} for session state.\n"
            f"Run {batch_size} experiment(s). Write findings to OmegaLoop/{session_id}/wins/win-{win_num:03d}/summary.md\n"
            f"Update manifest: increment experiment_count and win_count.\n"
            f"Commit: git add OmegaLoop/{session_id} && git commit -m 'OL: exp {exp_num}'\n"
        )
    else:
        session_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        new_session_id = f"{session_ts}-{MACHINE_ID}-tick"
        new_session_dir = f"OmegaLoop/{new_session_id}"
        claude_prompt = (
            f"Do the following research task. Do NOT ask questions, just execute.\n\n"
            f"RESEARCH PROMPT: {prompt}\n\n"
            f"{type_instructions}\n\n"
            f"Write your findings as markdown files in {new_session_dir}/wins/win-001/summary.md\n"
            f"Also create {new_session_dir}/manifest.json with:\n"
            f'{{"session_id": "{new_session_id}", "status": "looping", '
            f'"research_prompt": "{prompt[:200]}", "experiment_count": 1, "win_count": 1}}\n\n'
            f"Then commit: git add {new_session_dir} && git commit -m 'OL: {new_session_id} tick'\n"
        )

    # --- Fire the agent ---
    write_heartbeat(task_id, "running", f"Starting {backend} agent")

    # Write prompt to temp file for reliable delivery (avoids arg length limits and newline issues)
    prompt_file = OL_LOGS / f"{task_id}.prompt.md"
    prompt_file.write_text(claude_prompt, encoding="utf-8")

    t0 = time.time()
    try:
        if backend in ("claude", "copilot"):
            # Resolve CLI binary (Windows needs .cmd extension resolved)
            cli_name = "claude" if backend == "claude" else "copilot"
            cli_bin = shutil.which(cli_name)
            if not cli_bin:
                raise FileNotFoundError(f"{cli_name} CLI not found on PATH")

            cli_args = [cli_bin, "-p"]
            if backend == "claude":
                cli_args += ["--dangerously-skip-permissions"]
            cli_args += ["--output-format", "text"]

            # Pass prompt via stdin, capture output to files for reliability
            stdout_file = OL_LOGS / f"{task_id}.stdout.txt"
            stderr_file = OL_LOGS / f"{task_id}.stderr.txt"
            with open(stdout_file, "w", encoding="utf-8") as fout, \
                 open(stderr_file, "w", encoding="utf-8") as ferr:
                result = subprocess.run(
                    cli_args,
                    input=claude_prompt,
                    cwd=repo,
                    stdout=fout, stderr=ferr,
                    text=True,
                    timeout=1800,  # 30 min max per tick
                )
            # Read back output from files
            result.stdout = stdout_file.read_text(encoding="utf-8") if stdout_file.exists() else ""
            result.stderr = stderr_file.read_text(encoding="utf-8") if stderr_file.exists() else ""
        elif backend == "agent-framework":
            result = subprocess.run(
                [
                    get_python(), "-m", "orchestrator.engine",
                    "--repo", repo,
                    "--prompt", prompt,
                    "--max", str(min(batch_size, max_exps or 999)),
                    "--backend", backend,
                ],
                cwd=str(SKILL_DIR),
                capture_output=True, text=True,
                timeout=1800,
            )

        elapsed = time.time() - t0
        exit_code = result.returncode
        stdout_len = len(result.stdout) if result.stdout else 0
        stderr_text = (result.stderr or "").strip()
        print(f"  Completed in {elapsed:.0f}s (exit={exit_code}, stdout={stdout_len} chars)")
        if exit_code != 0:
            print(f"  STDERR: {stderr_text[:500]}")
            task["last_error"] = f"exit={exit_code}: {stderr_text[:200]}"
            task["error_count"] = task.get("error_count", 0) + 1

        # Write to log
        log_file = OL_LOGS / f"{task_id}.log"
        with open(log_file, "a") as f:
            f.write(f"\n--- Tick {datetime.now().isoformat()} (exit={exit_code}, {elapsed:.0f}s, {stdout_len} chars) ---\n")
            f.write(result.stdout[-5000:] if result.stdout else "(no output)")
            if stderr_text:
                f.write(f"\n--- STDERR ---\n{stderr_text[-2000:]}")
            f.write("\n")

        # --- Post-tick: check results for type-specific logic ---

        # Re-read manifest after tick (agent may have updated it)
        if session_id:
            manifest_path = Path(repo) / "OmegaLoop" / session_id / "manifest.json"
            if manifest_path.exists():
                updated_manifest = json.loads(manifest_path.read_text())
                post_tick_check(task, updated_manifest, result.stdout or "")

    except subprocess.TimeoutExpired:
        result = None
        elapsed = time.time() - t0
        print(f"  TIMEOUT after {elapsed:.0f}s")
        task["last_error"] = f"Timeout after {elapsed:.0f}s"
        task["error_count"] = task.get("error_count", 0) + 1
    except FileNotFoundError as e:
        result = None
        print(f"  ERROR: {e}")
        task["last_error"] = str(e)
        task["error_count"] = task.get("error_count", 0) + 1

    # Link to session if first tick AND agent succeeded
    if not session_id and result and result.returncode == 0:
        ol_dir = Path(repo) / "OmegaLoop"
        if ol_dir.exists():
            # Only consider sessions created after this tick started
            candidates = sorted(
                [d for d in ol_dir.iterdir()
                 if d.is_dir() and MACHINE_ID in d.name
                 and d.stat().st_mtime >= t0],
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                task["session_id"] = candidates[0].name
                print(f"  Linked to session: {task['session_id']}")

    # Update task metadata
    task["last_tick"] = datetime.now(timezone.utc).isoformat()
    task["last_tick_duration_s"] = round(time.time() - t0, 1)
    task["tick_count"] = task.get("tick_count", 0) + 1
    save_task(task)

    # Release lock and clear heartbeat
    release_tick_lock(task_id)
    clear_heartbeat(task_id)


def build_type_instructions(task: dict, manifest: dict | None, context: str) -> str:
    """Build loop-type-specific instructions for the Claude prompt."""
    loop_type = task.get("loop_type", "research")
    prompt = task["prompt"]
    batch = task.get("batch_size", 5)
    done_cond = task.get("done_condition")
    target_doc = task.get("target_doc")

    if loop_type == "converge":
        done_text = done_cond or "(infer from the research prompt)"
        return (
            f"LOOP TYPE: converge\n"
            f"GOAL: {prompt}\n"
            f"DONE CONDITION: {done_text}\n\n"
            f"This tick: Run up to {batch} iterations of the converge loop:\n"
            f"  1. Run tests / checks to detect failures\n"
            f"  2. If a failure is found: write a failing test first (TDD), then fix it\n"
            f"  3. Verify the fix passes\n"
            f"  4. If no failures found, record 'pass' in manifest\n"
            f"  5. Checkpoint and exit\n\n"
            f"After each iteration, update manifest.json with:\n"
            f'  "converge_metric": (count of remaining failures)\n'
            f'  "converge_history": (append current count)\n\n'
            f"IMPORTANT: If the done condition appears to be met, note it in the manifest "
            f"but do NOT mark the session as completed. The daemon tracks the done streak "
            f"across ticks and will auto-complete after consecutive passes."
        )

    elif loop_type == "monitor":
        target = target_doc or "(create an appropriate .md file in the session folder)"
        return (
            f"LOOP TYPE: monitor (persistent — never auto-complete)\n"
            f"GOAL: {prompt}\n"
            f"TARGET DOC: {target}\n\n"
            f"This tick:\n"
            f"  1. Check the external source for new data since last tick\n"
            f"  2. If new data found: enrich the target document with findings\n"
            f"  3. If no new data: log 'no changes' and exit quickly\n"
            f"  4. Commit any document updates to the OmegaLoop folder\n"
            f"  5. Checkpoint and exit\n\n"
            f"IMPORTANT: Do not mark the session as completed. This loop runs until "
            f"the user manually stops it. Be efficient — if there's nothing new, "
            f"exit quickly to save tokens."
        )

    elif loop_type == "optimize":
        return (
            f"LOOP TYPE: optimize (measurable metric)\n"
            f"GOAL: {prompt}\n\n"
            f"This tick: Run up to {batch} optimization experiments:\n"
            f"  1. Measure the current metric (baseline or from last win)\n"
            f"  2. Hypothesize an improvement\n"
            f"  3. Implement it in the worktree\n"
            f"  4. Measure again\n"
            f"  5. If improved: WIN — keep the change, record metric delta\n"
            f"  6. If not: DISCARD — revert, try next hypothesis\n"
            f"  7. Checkpoint and exit\n\n"
            f"Track the metric in manifest.json:\n"
            f'  "metric_name": "...",\n'
            f'  "baseline_value": ...,\n'
            f'  "best_value": ...,\n'
            f'  "metric_history": [...]\n'
        )

    else:  # research (default)
        max_exps = task.get("max", 50)
        return (
            f"LOOP TYPE: research\n"
            f"GOAL: {prompt}\n"
            f"MAX: {max_exps} total experiments\n\n"
            f"This tick: Run up to {batch} research experiments:\n"
            f"  1. Hypothesize an approach\n"
            f"  2. Implement in worktree\n"
            f"  3. Evaluate\n"
            f"  4. WIN or DISCARD\n"
            f"  5. Checkpoint and exit\n"
        )


def post_tick_check(task: dict, manifest: dict, output: str):
    """After a tick, check for type-specific state transitions."""
    loop_type = task.get("loop_type", "research")

    if loop_type == "converge":
        # Check if converge metric reached zero / done condition
        metric = manifest.get("converge_metric")
        history = manifest.get("converge_history", [])

        # Simple heuristic: if the last entry in history is 0, increment streak
        if history and history[-1] == 0:
            task["done_streak"] = task.get("done_streak", 0) + 1
            print(f"  Converge: done streak = {task['done_streak']}/{task.get('done_streak_target', 3)}")
        else:
            task["done_streak"] = 0

    elif loop_type == "monitor":
        # Track no-change streaks (informational, not used for termination)
        enrichment_count = manifest.get("enrichment_count", 0)
        if enrichment_count == task.get("_last_enrichment_count", 0):
            task["no_change_streak"] = task.get("no_change_streak", 0) + 1
        else:
            task["no_change_streak"] = 0
            task["_last_enrichment_count"] = enrichment_count

    elif loop_type == "optimize":
        # Nothing extra — the manifest tracks metric_history, daemon checks max_exps
        pass

# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_install():
    """One-time setup: create dirs, verify tools."""
    OL_HOME.mkdir(parents=True, exist_ok=True)
    OL_TASKS.mkdir(parents=True, exist_ok=True)
    OL_LOGS.mkdir(parents=True, exist_ok=True)
    OL_BIN.mkdir(parents=True, exist_ok=True)
    OL_LOCKS.mkdir(parents=True, exist_ok=True)
    OL_HEARTBEATS.mkdir(parents=True, exist_ok=True)
    print(f"AR Home:     {OL_HOME}")
    print(f"Tasks:       {OL_TASKS}")
    print(f"Logs:        {OL_LOGS}")
    print(f"Machine ID:  {MACHINE_ID}")
    print(f"Platform:    {get_platform()}")
    print(f"Python:      {get_python()}")
    print(f"Skill:       {SKILL_DIR}")

    # Check claude CLI
    claude_ok = shutil.which("claude") is not None
    print(f"Claude CLI:  {'OK' if claude_ok else 'NOT FOUND (install claude code)'}")
    print("\nReady. Use 'omegaloop add' to create research loops.")

def cmd_add(args):
    """Add a new research loop."""
    cmd_install()  # ensure dirs

    repo = str(Path(args.repo).resolve())
    prompt = args.prompt
    backend = args.backend
    batch = args.batch

    # Determine loop type
    loop_type = args.type
    if loop_type == "auto":
        loop_type = infer_loop_type(prompt)
        print(f"  Auto-detected loop type: {loop_type}")

    # Set defaults per type
    if args.max is not None:
        max_exps = args.max
    else:
        max_exps = None if loop_type == "monitor" else 50

    # Schedule: --schedule (cron) overrides --interval
    if args.schedule:
        cron_expr = args.schedule
        interval = 0  # not used when cron is explicit
    else:
        interval = parse_interval(args.interval)
        cron_expr = interval_to_cron(interval)

    task_id = gen_task_id(repo, prompt)

    task = {
        "id": task_id,
        "repo": repo,
        "prompt": prompt,
        "loop_type": loop_type,
        "interval_minutes": interval,
        "cron_expr": cron_expr,
        "max": max_exps,
        "batch_size": batch,
        "backend": backend,
        "status": "active",
        "machine_id": MACHINE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_tick": None,
        "tick_count": 0,
        "session_id": None,
        # Type-specific fields
        "done_condition": args.done_condition,
        "done_streak": 0,
        "done_streak_target": 3,
        "target_doc": args.target_doc,
        "no_change_streak": 0,
    }

    save_task(task)
    scheduler_install_cron(task, cron_expr)

    terminates = loop_type != "monitor"
    print(f"\n[OK] Task {task_id} created")
    print(f"  Repo:     {repo}")
    print(f"  Prompt:   {prompt[:70]}")
    print(f"  Type:     {loop_type}")
    print(f"  Schedule: {cron_expr}")
    print(f"  Batch:    {batch} experiments per tick")
    if max_exps:
        print(f"  Max:      {max_exps} total experiments")
    else:
        print(f"  Max:      unlimited (monitor — runs until you stop it)")
    if args.done_condition:
        print(f"  Done:     {args.done_condition}")
    if args.target_doc:
        print(f"  Target:   {args.target_doc}")
    print(f"  Backend:  {backend}")
    print(f"  Stops:    {'when done condition met' if loop_type == 'converge' else 'at max experiments' if terminates else 'NEVER (manual stop only)'}")
    print(f"\n  Loop registered with {get_platform()}. Survives reboots.")
    print(f"  Logs: {OL_LOGS / task_id}.log")


def infer_loop_type(prompt: str) -> str:
    """Guess loop type from the prompt text."""
    p = prompt.lower()
    # Monitor keywords
    if any(k in p for k in ["monitor", "watch", "check for", "if you see", "enrich", "keep enriching", "once a day", "daily"]):
        return "monitor"
    # Converge keywords
    if any(k in p for k in ["until all tests", "tdd", "fix the bug", "fix all", "find and fix",
                             "until green", "target:", "under ", "above "]):
        return "converge"
    # Optimize keywords
    if any(k in p for k in ["improve load time", "improve the load time", "improve the ",
                             "reduce size", "reduce the ", "faster", "optimize",
                             "benchmark", "measure with", "load time"]):
        return "optimize"
    return "research"


def scheduler_install_cron(task: dict, cron_expr: str):
    """Install with the given cron expression (may be from --schedule or --interval)."""
    plat = get_platform()
    # For cron-based platforms, use the expression directly
    if plat == "cron":
        cron_install_expr(task, cron_expr)
    elif plat == "launchd":
        # launchd uses intervals; convert cron to interval if possible
        launchd_install(task)
    elif plat == "taskscheduler":
        taskscheduler_install(task)


def cron_install_expr(task: dict, cron_expr: str):
    """Add a crontab entry with an explicit cron expression."""
    task_id = task["id"]
    cmd = f'{get_python()} {get_daemon_script()} run-tick {task_id}'
    comment = f"# OL_TASK_{task_id}"
    line = f"{cron_expr} {cmd} >> {OL_LOGS / task_id}.log 2>&1 {comment}"

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    lines = [l for l in existing.strip().split("\n") if f"OL_TASK_{task_id}" not in l]
    lines.append(line)
    new_crontab = "\n".join(l for l in lines if l.strip()) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to install cron: {proc.stderr}")

def cmd_list():
    """List all tasks."""
    tasks = list_tasks()
    if not tasks:
        print("No research loops registered. Use 'omegaloop add' to create one.")
        return

    print(f"\n{'ID':>10}  {'Type':>8}  {'Status':>9}  {'Ticks':>5}  {'Schedule':>14}  {'Backend':>8}  {'Repo':<20}  Prompt")
    print("-" * 120)
    for t in tasks:
        status = t.get("status", "?")
        status_tag = {"active": "+", "paused": "~", "completed": "."}.get(status, "?")
        repo = Path(t.get("repo", "?")).name
        prompt = t.get("prompt", "?")[:35]
        ltype = t.get("loop_type", "?")
        cron = t.get("cron_expr", "?")
        sched = cron if len(cron) < 15 else cron[:12] + ".."
        print(f"{t['id']:>10}  {ltype:>8}  {status_tag}{status:>9}  {t.get('tick_count',0):>5}  "
              f"{sched:>14}  {t.get('backend','?'):>8}  "
              f"{repo:<20}  {prompt}")

    print(f"\nMachine: {MACHINE_ID} ({platform.node()})")
    print(f"Platform: {get_platform()}")

    # Summary by type
    types = {}
    for t in tasks:
        lt = t.get("loop_type", "?")
        types.setdefault(lt, {"active": 0, "paused": 0, "completed": 0})
        types[lt][t.get("status", "?")] = types[lt].get(t.get("status", "?"), 0) + 1
    print("\nBy type:")
    for lt, counts in types.items():
        parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
        print(f"  {lt}: {', '.join(parts)}")

def cmd_logs(task_id: str):
    """Show logs for a task."""
    log_file = OL_LOGS / f"{task_id}.log"
    if log_file.exists():
        # Tail last 100 lines
        lines = log_file.read_text().split("\n")
        for line in lines[-100:]:
            print(line)
    else:
        print(f"No logs for {task_id}")

def cmd_pause(task_id: str):
    task = load_task(task_id)
    task["status"] = "paused"
    save_task(task)
    scheduler_remove(task_id)
    print(f"[OK] {task_id} paused. OS scheduler entry removed.")
    print(f"  Use 'omegaloop resume {task_id}' to restart.")

def cmd_resume(task_id: Optional[str], resume_all: bool = False):
    if resume_all:
        tasks = [t for t in list_tasks() if t.get("status") in ("paused", "active")]
        if not tasks:
            print("No tasks to resume.")
            return
        for t in tasks:
            t["status"] = "active"
            save_task(t)
            cron_expr = t.get("cron_expr", interval_to_cron(t.get("interval_minutes", 10)))
            scheduler_install_cron(t, cron_expr)
            print(f"[OK] {t['id']} [{t.get('loop_type','?')}] resumed ({Path(t['repo']).name}: {t['prompt'][:35]})")
        print(f"\n{len(tasks)} task(s) resumed.")
    elif task_id:
        task = load_task(task_id)
        task["status"] = "active"
        save_task(task)
        cron_expr = task.get("cron_expr", interval_to_cron(task.get("interval_minutes", 10)))
        scheduler_install_cron(task, cron_expr)
        print(f"[OK] {task_id} resumed.")
    else:
        print("Specify a task ID or use --all")

def cmd_remove(task_id: str):
    scheduler_remove(task_id)
    p = task_path(task_id)
    if p.exists():
        p.unlink()
    print(f"[OK] {task_id} removed. OS scheduler entry and task config deleted.")
    print(f"  OmegaLoop/ data in the repo is preserved.")

def cmd_status(task_id: Optional[str] = None):
    """Show detailed status for one or all tasks, including lock/heartbeat state."""
    tasks = list_tasks()
    if not tasks:
        print("No research loops registered.")
        return

    if task_id:
        tasks = [t for t in tasks if t["id"] == task_id]
        if not tasks:
            print(f"Task {task_id} not found.")
            return

    for t in tasks:
        tid = t["id"]
        print(f"\n{'='*60}")
        print(f"Task: {tid}")
        print(f"  Repo:      {t.get('repo', '?')}")
        print(f"  Prompt:    {t.get('prompt', '?')[:70]}")
        print(f"  Type:      {t.get('loop_type', '?')}")
        print(f"  Status:    {t.get('status', '?')}")
        print(f"  Backend:   {t.get('backend', '?')}")
        print(f"  Ticks:     {t.get('tick_count', 0)}")
        print(f"  Last tick: {t.get('last_tick', 'never')}")
        if t.get("last_tick_duration_s"):
            print(f"  Duration:  {t['last_tick_duration_s']}s")
        if t.get("last_error"):
            print(f"  Last err:  {t['last_error']}")
        if t.get("error_count"):
            print(f"  Errors:    {t['error_count']}")
        if t.get("session_id"):
            print(f"  Session:   {t['session_id']}")

        # Check lock state
        lock = _lock_path(tid)
        if lock.exists():
            try:
                ld = json.loads(lock.read_text())
                age = time.time() - ld.get("started_at", 0)
                pid = ld.get("pid", 0)
                alive = False
                try:
                    os.kill(pid, 0)
                    alive = True
                except (OSError, ProcessLookupError):
                    pass
                state = "RUNNING" if alive else "STALE"
                print(f"  Lock:      {state} (pid={pid}, age={age:.0f}s)")
            except (json.JSONDecodeError, ValueError):
                print(f"  Lock:      CORRUPTED")
        else:
            print(f"  Lock:      none")

        # Check heartbeat
        hb = _heartbeat_path(tid)
        if hb.exists():
            try:
                hd = json.loads(hb.read_text())
                age = time.time() - hd.get("timestamp", 0)
                print(f"  Heartbeat: {hd.get('phase', '?')} ({age:.0f}s ago) {hd.get('detail', '')}")
            except (json.JSONDecodeError, ValueError):
                print(f"  Heartbeat: CORRUPTED")

        # Read manifest for experiment/win stats
        session_id = t.get("session_id")
        repo = t.get("repo")
        if session_id and repo:
            manifest_path = Path(repo) / "OmegaLoop" / session_id / "manifest.json"
            if manifest_path.exists():
                try:
                    m = json.loads(manifest_path.read_text())
                    print(f"  Exps:      {m.get('experiment_count', 0)}")
                    print(f"  Wins:      {m.get('win_count', 0)}")
                    print(f"  Strategy:  {m.get('current_strategy', '?')}")
                    streak = m.get('consecutive_no_wins', 0)
                    if streak > 0:
                        print(f"  No-win:    {streak} consecutive")
                    if m.get("insights"):
                        print(f"  Insights:  {len(m['insights'])}")
                except (json.JSONDecodeError, ValueError):
                    print(f"  Manifest:  CORRUPTED")

    print(f"\n{'='*60}")
    print(f"Machine: {MACHINE_ID} ({platform.node()})")
    print(f"Platform: {get_platform()}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="omegaloop",
        description="OmegaLoop scheduler — durable, survives reboots",
    )
    sub = parser.add_subparsers(dest="command")

    # install
    sub.add_parser("install", help="One-time setup")

    # add
    p_add = sub.add_parser("add", help="Add a new research loop")
    p_add.add_argument("--repo", required=True, help="Path to git repo")
    p_add.add_argument("--prompt", required=True, help="Research prompt")
    p_add.add_argument("--type", default="auto",
                       choices=["auto", "converge", "monitor", "research", "optimize"],
                       help="Loop type (auto-detected if not set)")
    p_add.add_argument("--interval", default="10m", help="Tick interval (5m, 1h, 1d)")
    p_add.add_argument("--schedule", default=None, help="Cron expression (overrides --interval)")
    p_add.add_argument("--max", type=int, default=None, help="Max experiments (None=unlimited for monitors)")
    p_add.add_argument("--batch", type=int, default=5, help="Experiments per tick")
    p_add.add_argument("--backend", default="claude",
                       choices=["claude", "agent-framework", "copilot"],
                       help="Agent backend")
    p_add.add_argument("--done-condition", default=None,
                       help="For converge: natural language done condition")
    p_add.add_argument("--target-doc", default=None,
                       help="For monitor: document to enrich")

    # list
    sub.add_parser("list", help="List all research loops")

    # logs
    p_logs = sub.add_parser("logs", help="Show logs for a task")
    p_logs.add_argument("task_id")

    # pause
    p_pause = sub.add_parser("pause", help="Pause a research loop")
    p_pause.add_argument("task_id")

    # resume
    p_resume = sub.add_parser("resume", help="Resume a paused loop")
    p_resume.add_argument("task_id", nargs="?")
    p_resume.add_argument("--all", action="store_true", help="Resume all loops")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a research loop entirely")
    p_remove.add_argument("task_id")

    # status
    p_status = sub.add_parser("status", help="Detailed status with lock/heartbeat/manifest info")
    p_status.add_argument("task_id", nargs="?", help="Task ID (all tasks if omitted)")

    # run-tick (internal — called by OS scheduler)
    p_tick = sub.add_parser("run-tick", help=argparse.SUPPRESS)
    p_tick.add_argument("task_id")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        cmd_list()
    elif args.command == "logs":
        cmd_logs(args.task_id)
    elif args.command == "pause":
        cmd_pause(args.task_id)
    elif args.command == "resume":
        cmd_resume(args.task_id, getattr(args, "all", False))
    elif args.command == "remove":
        cmd_remove(args.task_id)
    elif args.command == "status":
        cmd_status(getattr(args, "task_id", None))
    elif args.command == "run-tick":
        run_tick(args.task_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
