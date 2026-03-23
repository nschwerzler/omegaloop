"""
OmegaLoop Orchestrator — distributed, crash-resilient, multi-project research loop engine.

Uses Microsoft Agent Framework (Python) for agent orchestration.
Uses git worktrees for isolation, git commits for state persistence.
Machine-scoped IDs prevent collision across 5+ machines on the same repo.

Usage:
    python -m orchestrator.engine --repo /path/to/repo --prompt "Make caching faster"
    python -m orchestrator.engine --resume          # resume all incomplete sessions
    python -m orchestrator.engine --config loops.json  # run multiple projects from config
"""

import asyncio
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Machine identity — globally unique, stable across reboots, short enough for branch names
# ---------------------------------------------------------------------------

def get_machine_id() -> str:
    """Generate a stable 6-char machine identifier.
    Uses hostname + MAC address hash for uniqueness across machines.
    Stable across reboots. Different machines = different IDs."""
    raw = f"{platform.node()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:6]

MACHINE_ID = get_machine_id()

# ---------------------------------------------------------------------------
# Session ID format: {YYYYMMDD-HHMMSS}-{machine_id}-{prompt_hash}
# Branch format:     ar/{session_id}
# Worktree path:     {repo}/.git/ol-worktrees/{session_id}
# OmegaLoop folder:         {repo}/OmegaLoop/{session_id}/
# ---------------------------------------------------------------------------

class Status(str, Enum):
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    LOOPING = "looping"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class ExperimentResult(str, Enum):
    WIN = "win"
    DISCARD = "discard"
    ERROR = "error"

@dataclass
class Experiment:
    experiment_id: str
    timestamp: str
    machine_id: str
    strategy: str
    hypothesis: str
    changes: list[str]
    result: str  # win|discard|error
    metrics: dict = field(default_factory=dict)
    reasoning: str = ""
    diff_summary: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0

@dataclass
class WinRecord:
    win_id: str
    experiment_id: str
    title: str
    commit_hash: str
    machine_id: str
    artifacts_path: str
    metrics_delta: dict = field(default_factory=dict)

@dataclass
class Manifest:
    schema_version: str = "2.0"
    session_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    research_prompt: str = ""
    repo_root: str = ""
    repo_name: str = ""
    base_branch: str = ""
    worktree_branch: str = ""
    worktree_path: str = ""
    status: str = Status.INITIALIZING
    machine_id: str = ""
    machines_involved: list[str] = field(default_factory=list)
    experiment_count: int = 0
    win_count: int = 0
    max_experiments: int = 50
    last_checkpoint: Optional[str] = None
    current_strategy: str = "low-hanging"
    consecutive_no_wins: int = 0
    evaluation_criteria: dict = field(default_factory=dict)
    experiments: list[dict] = field(default_factory=list)
    wins: list[dict] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)

    def save(self, path: Path):
        self.updated_at = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(asdict(self), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        data = json.loads(path.read_text())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Git operations — all worktree/branch operations isolated here
# ---------------------------------------------------------------------------

class GitOps:
    def __init__(self, repo_root: str):
        self.root = Path(repo_root)

    def run(self, *args, cwd: Optional[Path] = None, check=True) -> str:
        r = subprocess.run(
            ["git"] + list(args),
            cwd=str(cwd or self.root),
            capture_output=True, text=True, timeout=60,
        )
        if check and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
        return r.stdout.strip()

    @property
    def repo_name(self) -> str:
        return self.root.name

    @property
    def current_branch(self) -> str:
        return self.run("rev-parse", "--abbrev-ref", "HEAD")

    def is_clean(self) -> bool:
        return self.run("status", "--porcelain") == ""

    def short_hash(self, ref="HEAD", cwd=None) -> str:
        return self.run("rev-parse", "--short=7", ref, cwd=cwd)

    # -- Worktree operations (machine-scoped to prevent collision) --

    def worktree_dir(self) -> Path:
        return self.root / ".git" / "ol-worktrees"

    def create_worktree(self, session_id: str, base_branch: str) -> Path:
        wt_path = self.worktree_dir() / session_id
        branch = f"ar/{session_id}"

        if wt_path.exists():
            return wt_path

        wt_path.parent.mkdir(parents=True, exist_ok=True)

        # Create branch from base if it doesn't exist
        try:
            self.run("branch", branch, base_branch)
        except RuntimeError:
            pass  # branch already exists (another machine created it)

        self.run("worktree", "add", str(wt_path), branch)
        return wt_path

    def remove_worktree(self, session_id: str):
        wt_path = self.worktree_dir() / session_id
        if wt_path.exists():
            self.run("worktree", "remove", str(wt_path), "--force", check=False)
        self.run("branch", "-D", f"ar/{session_id}", check=False)

    def worktree_exists(self, session_id: str) -> bool:
        return (self.worktree_dir() / session_id).exists()

    def revert_worktree(self, wt_path: Path):
        self.run("checkout", "--", ".", cwd=wt_path)
        self.run("clean", "-fd", cwd=wt_path)

    def commit_worktree(self, wt_path: Path, msg: str) -> str:
        self.run("add", "-A", cwd=wt_path)
        try:
            self.run("commit", "-m", msg, cwd=wt_path)
        except RuntimeError:
            pass  # nothing to commit
        return self.short_hash(cwd=wt_path)

    def diff_stat(self, wt_path: Path) -> str:
        return self.run("diff", "--stat", "HEAD", cwd=wt_path, check=False)

    def diff_files(self, wt_path: Path) -> list[str]:
        out = self.run("diff", "--name-only", "HEAD", cwd=wt_path, check=False)
        return [f for f in out.split("\n") if f.strip()]

    def diff_patch(self, wt_path: Path, ref="HEAD~1") -> str:
        return self.run("diff", ref, cwd=wt_path, check=False)

    # -- OmegaLoop folder commits to main branch --

    def commit_ol_folder(self, session_id: str, msg: str):
        """Commit OmegaLoop folder changes to the main branch.
        Uses a lock-free approach: stage only AR files, commit, pull-rebase if needed."""
        ol_path = f"OmegaLoop/{session_id}/"
        self.run("add", ol_path)
        try:
            self.run("commit", "-m", msg)
        except RuntimeError:
            pass

    def pull_rebase(self):
        """Pull latest from remote with rebase to merge other machines' work."""
        try:
            self.run("pull", "--rebase", "--autostash", check=False)
        except RuntimeError:
            pass

    def push(self):
        """Push to remote so other machines can see our results."""
        try:
            self.run("push", check=False)
        except RuntimeError:
            pass


# ---------------------------------------------------------------------------
# Session manager — creates, loads, discovers sessions
# ---------------------------------------------------------------------------

class SessionManager:
    def __init__(self, git: GitOps):
        self.git = git
        self.ol_root = git.root / "OmegaLoop"

    def create_session(self, prompt: str, max_experiments: int = 50) -> Manifest:
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:4]
        session_id = f"{timestamp}-{MACHINE_ID}-{prompt_hash}"

        ol_dir = self.ol_root / session_id
        ol_dir.mkdir(parents=True, exist_ok=True)
        (ol_dir / "logs").mkdir(exist_ok=True)
        (ol_dir / "wins").mkdir(exist_ok=True)
        (ol_dir / "checkpoints").mkdir(exist_ok=True)

        base_branch = self.git.current_branch
        wt_path = self.git.create_worktree(session_id, base_branch)

        manifest = Manifest(
            session_id=session_id,
            created_at=now.isoformat(),
            research_prompt=prompt,
            repo_root=str(self.git.root),
            repo_name=self.git.repo_name,
            base_branch=base_branch,
            worktree_branch=f"ar/{session_id}",
            worktree_path=str(wt_path),
            status=Status.ANALYZING,
            machine_id=MACHINE_ID,
            machines_involved=[MACHINE_ID],
            max_experiments=max_experiments,
        )

        manifest.save(ol_dir / "manifest.json")

        # Write research-prompt.md
        (ol_dir / "research-prompt.md").write_text(
            f"# OmegaLoop: {session_id}\n\n"
            f"> {prompt}\n\n"
            f"- Repo: {self.git.repo_name}\n"
            f"- Branch: {base_branch}\n"
            f"- Machine: {MACHINE_ID}\n"
            f"- Started: {now.isoformat()}\n"
            f"- Max: {max_experiments}\n"
        )

        # Commit init
        self.git.commit_ol_folder(session_id, f"OL: init {session_id}")
        return manifest

    def load_session(self, session_id: str) -> Optional[Manifest]:
        mpath = self.ol_root / session_id / "manifest.json"
        if mpath.exists():
            return Manifest.load(mpath)
        return None

    def discover_sessions(self, status_filter: Optional[list[str]] = None) -> list[Manifest]:
        """Find all sessions in this repo. Used on startup to resume."""
        sessions = []
        if not self.ol_root.exists():
            return sessions
        for d in sorted(self.ol_root.iterdir()):
            mpath = d / "manifest.json"
            if d.is_dir() and mpath.exists():
                try:
                    m = Manifest.load(mpath)
                    if status_filter is None or m.status in status_filter:
                        sessions.append(m)
                except Exception:
                    continue
        return sessions

    def discover_resumable(self) -> list[Manifest]:
        """Find sessions that should be resumed (looping or paused, not completed)."""
        return self.discover_sessions(
            status_filter=[Status.LOOPING, Status.PAUSED, Status.ANALYZING]
        )

    def store_win(self, manifest: Manifest, exp: Experiment, title: str) -> WinRecord:
        """Store a win: copy artifacts, write summary, commit to OmegaLoop folder."""
        win_num = manifest.win_count + 1
        win_id = f"win-{win_num:03d}"
        ol_dir = self.ol_root / manifest.session_id
        win_dir = ol_dir / "wins" / win_id
        win_dir.mkdir(parents=True, exist_ok=True)

        wt = Path(manifest.worktree_path)

        # Capture diff
        try:
            diff = self.git.diff_patch(wt)
            (win_dir / "changes.diff").write_text(diff[:100_000])
        except Exception:
            (win_dir / "changes.diff").write_text("(diff unavailable)")

        # Commit hash
        commit_hash = self.git.short_hash(cwd=wt)
        (win_dir / "commit-hash.txt").write_text(commit_hash)

        # Summary
        (win_dir / "summary.md").write_text(
            f"# {win_id}: {title}\n\n"
            f"**Session**: {manifest.session_id}\n"
            f"**Machine**: {MACHINE_ID}\n"
            f"**Experiment**: {exp.experiment_id}\n"
            f"**Timestamp**: {exp.timestamp}\n\n"
            f"## Hypothesis\n{exp.hypothesis}\n\n"
            f"## Changes\n{chr(10).join('- ' + f for f in exp.changes)}\n\n"
            f"## Metrics\n```json\n{json.dumps(exp.metrics, indent=2)}\n```\n\n"
            f"## Reasoning\n{exp.reasoning}\n"
        )

        record = WinRecord(
            win_id=win_id,
            experiment_id=exp.experiment_id,
            title=title,
            commit_hash=commit_hash,
            machine_id=MACHINE_ID,
            artifacts_path=f"wins/{win_id}",
            metrics_delta=exp.metrics,
        )

        # Update manifest
        manifest.win_count = win_num
        manifest.consecutive_no_wins = 0
        manifest.wins.append(asdict(record))
        manifest.save(ol_dir / "manifest.json")

        # Commit to main branch
        self.git.commit_ol_folder(
            manifest.session_id,
            f"OL: {win_id} in {manifest.session_id} [{MACHINE_ID}] - {title}"
        )
        return record

    def checkpoint(self, manifest: Manifest):
        """Save current state — survives reboots."""
        manifest.last_checkpoint = datetime.now(timezone.utc).isoformat()
        ol_dir = self.ol_root / manifest.session_id
        manifest.save(ol_dir / "manifest.json")

        # Also commit so it survives machine loss
        self.git.commit_ol_folder(
            manifest.session_id,
            f"OL: checkpoint {manifest.session_id} exp={manifest.experiment_count} [{MACHINE_ID}]"
        )


# ---------------------------------------------------------------------------
# Research Loop — the core experiment cycle
# ---------------------------------------------------------------------------

class ResearchLoop:
    """Runs the omegaloop loop for a single session.
    Designed to be run in a thread per project."""

    def __init__(self, git: GitOps, session_mgr: SessionManager, manifest: Manifest,
                 agent_runner=None):
        self.git = git
        self.sm = session_mgr
        self.manifest = manifest
        self.agent = agent_runner  # injected — AgentFramework agent or CLI shim
        self._stop = False

    def stop(self):
        self._stop = True

    async def run(self):
        m = self.manifest
        ol_dir = self.sm.ol_root / m.session_id
        wt = Path(m.worktree_path)

        # Ensure worktree exists (resume after reboot)
        if not wt.exists():
            self.git.create_worktree(m.session_id, m.base_branch)

        # Track this machine
        if MACHINE_ID not in m.machines_involved:
            m.machines_involved.append(MACHINE_ID)

        # Pull latest from remote (merge other machines' work)
        self.git.pull_rebase()

        # Reload manifest in case another machine updated it
        fresh = self.sm.load_session(m.session_id)
        if fresh and fresh.experiment_count > m.experiment_count:
            m.experiment_count = fresh.experiment_count
            m.win_count = fresh.win_count
            m.experiments = fresh.experiments
            m.wins = fresh.wins
            m.insights = fresh.insights

        m.status = Status.LOOPING
        m.save(ol_dir / "manifest.json")

        start_exp = m.experiment_count + 1
        print(f"[{m.session_id}] Starting from experiment {start_exp}, {m.win_count} wins so far")

        for exp_num in range(start_exp, m.max_experiments + 1):
            if self._stop:
                m.status = Status.PAUSED
                self.sm.checkpoint(m)
                print(f"[{m.session_id}] Paused at experiment {exp_num}")
                return

            exp_id = f"exp-{exp_num:03d}-{MACHINE_ID}"
            print(f"[{m.session_id}] Experiment {exp_id}")

            t0 = time.time()
            try:
                exp = await self._run_one_experiment(m, exp_id, wt)
            except Exception as e:
                exp = Experiment(
                    experiment_id=exp_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    machine_id=MACHINE_ID,
                    strategy=m.current_strategy,
                    hypothesis="(crashed)",
                    changes=[],
                    result=ExperimentResult.ERROR,
                    error=str(e),
                    duration_seconds=time.time() - t0,
                )
                self.git.revert_worktree(wt)
                print(f"  ERROR: {e}")

            exp.duration_seconds = time.time() - t0
            m.experiments.append(asdict(exp))
            m.experiment_count = exp_num

            if exp.result == ExperimentResult.WIN:
                title = exp.hypothesis[:60]
                self.sm.store_win(m, exp, title)
                print(f"  WIN #{m.win_count}: {title}")
            elif exp.result == ExperimentResult.DISCARD:
                m.consecutive_no_wins += 1
                self.git.revert_worktree(wt)
                print(f"  DISCARD ({m.consecutive_no_wins} consecutive)")
            else:
                m.consecutive_no_wins += 1
                print(f"  ERROR ({m.consecutive_no_wins} consecutive)")

            # Strategy rotation on stuck
            if m.consecutive_no_wins >= 10:
                strategies = ["low-hanging", "structural", "creative", "adversarial", "synthesis"]
                idx = strategies.index(m.current_strategy) if m.current_strategy in strategies else 0
                m.current_strategy = strategies[(idx + 1) % len(strategies)]
                m.consecutive_no_wins = 0
                m.insights.append(f"Rotated strategy to {m.current_strategy} at exp {exp_num}")
                print(f"  Strategy → {m.current_strategy}")

            # Checkpoint every experiment
            self.sm.checkpoint(m)

            # Push periodically so other machines see our progress
            if exp_num % 5 == 0:
                self.git.push()

        m.status = Status.COMPLETED
        self.sm.checkpoint(m)
        self.git.push()
        print(f"[{m.session_id}] Completed. {m.win_count} wins from {m.experiment_count} experiments.")

    async def _run_one_experiment(self, m: Manifest, exp_id: str, wt: Path) -> Experiment:
        """Run a single experiment using the agent. Override this for different agent backends."""
        if self.agent is None:
            raise RuntimeError("No agent configured. Set agent_runner.")

        # Build context for the agent
        context = {
            "research_prompt": m.research_prompt,
            "repo_name": m.repo_name,
            "strategy": m.current_strategy,
            "experiment_number": m.experiment_count + 1,
            "wins_so_far": m.win_count,
            "recent_experiments": m.experiments[-5:],
            "insights": m.insights[-10:],
            "worktree_path": str(wt),
        }

        result = await self.agent.run_experiment(context)
        return Experiment(
            experiment_id=exp_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            machine_id=MACHINE_ID,
            strategy=m.current_strategy,
            hypothesis=result.get("hypothesis", ""),
            changes=result.get("changes", []),
            result=result.get("result", ExperimentResult.DISCARD),
            metrics=result.get("metrics", {}),
            reasoning=result.get("reasoning", ""),
            diff_summary=result.get("diff_summary", ""),
        )


# ---------------------------------------------------------------------------
# Multi-project orchestrator — runs N loops concurrently, handles signals
# ---------------------------------------------------------------------------

class Orchestrator:
    """Top-level coordinator. Runs multiple research loops in parallel threads.
    Handles SIGINT/SIGTERM for graceful shutdown + checkpoint."""

    def __init__(self):
        self.loops: list[ResearchLoop] = []
        self._shutdown = False

    def _handle_signal(self, sig, frame):
        print(f"\n[Orchestrator] Signal {sig} received. Stopping all loops gracefully...")
        self._shutdown = True
        for loop in self.loops:
            loop.stop()

    async def run_sessions(self, sessions: list[tuple[GitOps, Manifest]], agent_factory):
        """Run multiple sessions concurrently."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        tasks = []
        for git, manifest in sessions:
            sm = SessionManager(git)
            agent = agent_factory(manifest)
            loop = ResearchLoop(git, sm, manifest, agent)
            self.loops.append(loop)
            tasks.append(asyncio.create_task(self._run_with_retry(loop)))

        await asyncio.gather(*tasks, return_exceptions=True)

        print(f"[Orchestrator] All loops finished. {len(self.loops)} sessions processed.")

    async def _run_with_retry(self, loop: ResearchLoop, max_retries: int = 3):
        """Run a loop with retry on transient failures."""
        for attempt in range(max_retries):
            try:
                await loop.run()
                return
            except Exception as e:
                print(f"[{loop.manifest.session_id}] Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1 and not self._shutdown:
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    loop.manifest.status = Status.ERROR
                    SessionManager(loop.git).checkpoint(loop.manifest)
                    raise


# ---------------------------------------------------------------------------
# Agent backends — plug in AgentFramework, Claude CLI, or Copilot
# ---------------------------------------------------------------------------

class AgentFrameworkBackend:
    """Uses Microsoft Agent Framework (Python) for experiment execution."""

    def __init__(self, manifest: Manifest):
        self.manifest = manifest
        self._agent = None

    async def _ensure_agent(self):
        if self._agent is not None:
            return

        # Import here so the orchestrator loads even without agent-framework installed
        from agent_framework.azure import AzureOpenAIResponsesClient
        from azure.identity import AzureCliCredential

        client = AzureOpenAIResponsesClient(
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT", ""),
            deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1"),
            credential=AzureCliCredential(),
        )

        self._agent = client.as_agent(
            name="OmegaLooper",
            instructions=self._build_instructions(),
        )

    def _build_instructions(self) -> str:
        return (
            "You are an autonomous code research agent. You receive a research context "
            "and must: 1) Form a specific hypothesis, 2) Describe exact code changes, "
            "3) Evaluate the outcome. Respond ONLY with a JSON object:\n"
            '{"hypothesis": "...", "changes": ["file1.py"], '
            '"result": "win|discard", "metrics": {}, '
            '"reasoning": "...", "diff_summary": "..."}\n'
            "Be bold. Try non-obvious approaches. Never ask for permission."
        )

    async def run_experiment(self, context: dict) -> dict:
        await self._ensure_agent()
        prompt = (
            f"Research: {context['research_prompt']}\n"
            f"Strategy: {context['strategy']}\n"
            f"Experiment #{context['experiment_number']} (wins: {context['wins_so_far']})\n"
            f"Recent: {json.dumps(context['recent_experiments'][-2:], default=str)}\n"
            f"Insights: {context['insights'][-3:]}\n"
            f"Worktree: {context['worktree_path']}\n"
            "Propose and evaluate one experiment. Return JSON only."
        )
        try:
            result = await asyncio.wait_for(self._agent.run(prompt), timeout=600)
        except asyncio.TimeoutError:
            return {"hypothesis": "(agent timeout after 600s)", "changes": [],
                    "result": "error", "metrics": {}, "reasoning": "Agent call timed out",
                    "diff_summary": ""}
        return _safe_parse_agent_json(str(result))


class ClaudeCliBackend:
    """Uses `claude` CLI (Claude Code) as the experiment agent."""

    TIMEOUT = 900  # 15 minutes max per experiment

    def __init__(self, manifest: Manifest):
        self.manifest = manifest

    async def run_experiment(self, context: dict) -> dict:
        prompt = (
            f"You are running OmegaLoop experiment #{context['experiment_number']} "
            f"in {context['worktree_path']}.\n"
            f"Goal: {context['research_prompt']}\n"
            f"Strategy: {context['strategy']}\n"
            f"Make ONE code change, test it, evaluate it.\n"
            f"Respond with JSON: {{hypothesis, changes, result, metrics, reasoning, diff_summary}}"
        )
        claude_bin = shutil.which("claude") or "claude"
        proc = await asyncio.create_subprocess_exec(
            claude_bin, "-p",
            "--output-format", "text",
            cwd=context["worktree_path"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Write prompt via stdin for reliability (no arg length limits)
        proc.stdin.write(prompt.encode())
        proc.stdin.close()
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self.TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"hypothesis": f"(claude CLI timeout after {self.TIMEOUT}s)", "changes": [],
                    "result": "error", "metrics": {}, "reasoning": "Process timed out",
                    "diff_summary": ""}
        return _safe_parse_agent_json(stdout.decode())


class CopilotCliBackend:
    """Uses GitHub Copilot CLI (standalone `copilot` binary) as the experiment agent."""

    TIMEOUT = 900  # 15 minutes max per experiment

    def __init__(self, manifest: Manifest):
        self.manifest = manifest

    async def run_experiment(self, context: dict) -> dict:
        prompt = (
            f"OmegaLoop experiment #{context['experiment_number']}. "
            f"Goal: {context['research_prompt']}. "
            f"Strategy: {context['strategy']}. "
            f"Make one change, evaluate, return JSON."
        )
        copilot_bin = shutil.which("copilot") or "copilot"
        proc = await asyncio.create_subprocess_exec(
            copilot_bin, "-p",
            "--output-format", "text",
            cwd=context["worktree_path"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        proc.stdin.write(prompt.encode())
        proc.stdin.close()
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self.TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"hypothesis": f"(copilot CLI timeout after {self.TIMEOUT}s)", "changes": [],
                    "result": "error", "metrics": {}, "reasoning": "Process timed out",
                    "diff_summary": ""}
        return _safe_parse_agent_json(stdout.decode())


# ---------------------------------------------------------------------------
# Agent factory — select backend based on env/config
# ---------------------------------------------------------------------------

def _safe_parse_agent_json(text: str) -> dict:
    """Parse JSON from agent output, handling markdown fences and partial output."""
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    # Try to find a JSON object in the output
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    # Last resort: return error result
    return {
        "hypothesis": "(agent returned non-JSON output)",
        "changes": [],
        "result": "error",
        "metrics": {},
        "reasoning": f"Raw output: {text[:500]}",
        "diff_summary": "",
    }


BACKENDS = {
    "agent-framework": AgentFrameworkBackend,
    "claude": ClaudeCliBackend,
    "copilot": CopilotCliBackend,
}

def make_agent_factory(backend_name: str = "agent-framework"):
    BackendClass = BACKENDS.get(backend_name, AgentFrameworkBackend)
    def factory(manifest: Manifest):
        return BackendClass(manifest)
    return factory


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="OmegaLoop Orchestrator")
    parser.add_argument("--repo", type=str, help="Path to git repo")
    parser.add_argument("--prompt", type=str, help="Research prompt")
    parser.add_argument("--max", type=int, default=50, help="Max experiments per session")
    parser.add_argument("--resume", action="store_true", help="Resume all incomplete sessions")
    parser.add_argument("--config", type=str, help="JSON config with multiple projects")
    parser.add_argument("--backend", type=str, default="agent-framework",
                        choices=list(BACKENDS.keys()), help="Agent backend")
    parser.add_argument("--push", action="store_true", help="Push results to remote after each batch")
    args = parser.parse_args()

    agent_factory = make_agent_factory(args.backend)
    orchestrator = Orchestrator()
    sessions = []

    if args.config:
        # Multi-project mode: read JSON config
        config = json.loads(Path(args.config).read_text())
        for proj in config.get("projects", []):
            repo_path = proj["repo"]
            git = GitOps(repo_path)
            sm = SessionManager(git)

            if proj.get("resume", False):
                for m in sm.discover_resumable():
                    sessions.append((git, m))
            else:
                m = sm.create_session(proj["prompt"], proj.get("max", args.max))
                sessions.append((git, m))

    elif args.resume:
        # Resume mode: find all incomplete sessions
        repo = args.repo or os.getcwd()
        git = GitOps(repo)
        sm = SessionManager(git)
        for m in sm.discover_resumable():
            sessions.append((git, m))
        if not sessions:
            print("No resumable sessions found.")
            return

    elif args.prompt:
        # Single session mode
        repo = args.repo or os.getcwd()
        git = GitOps(repo)
        sm = SessionManager(git)
        m = sm.create_session(args.prompt, args.max)
        sessions.append((git, m))

    else:
        parser.print_help()
        return

    print(f"[Orchestrator] Machine ID: {MACHINE_ID}")
    print(f"[Orchestrator] {len(sessions)} session(s) to run")
    for _, m in sessions:
        print(f"  {m.session_id} [{m.status}] {m.research_prompt[:60]}")

    await orchestrator.run_sessions(sessions, agent_factory)


def main_sync():
    """Synchronous entry point for pyproject.toml console_scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
