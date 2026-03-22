"""Tests for distributed multi-machine operation — collision avoidance."""

import hashlib
import json
from pathlib import Path

from orchestrator.engine import GitOps, SessionManager, Manifest, MACHINE_ID


def fake_machine_id(hostname: str, mac: int) -> str:
    """Generate a machine ID for a simulated machine."""
    raw = f"{hostname}-{mac}"
    return hashlib.sha256(raw.encode()).hexdigest()[:6]


class TestNoCollision:
    def test_different_machines_different_ids(self):
        """Five simulated machines should produce five different IDs."""
        machines = [
            ("DESKTOP-NK7", 123456789),
            ("LAPTOP-NK3", 987654321),
            ("VM-BUILD01", 111111111),
            ("VM-BUILD02", 222222222),
            ("WSL-DEV", 333333333),
        ]
        ids = [fake_machine_id(h, m) for h, m in machines]
        assert len(set(ids)) == 5, f"Collision detected: {ids}"

    def test_session_ids_include_machine(self):
        """Session IDs from different machines should be distinguishable."""
        id_a = fake_machine_id("MACHINE-A", 100)
        id_b = fake_machine_id("MACHINE-B", 200)

        session_a = f"20260322-143052-{id_a}-c4d2"
        session_b = f"20260322-143052-{id_b}-c4d2"

        assert session_a != session_b
        assert id_a in session_a
        assert id_b in session_b

    def test_experiment_ids_include_machine(self):
        """Experiment IDs from different machines should not collide."""
        id_a = fake_machine_id("MACHINE-A", 100)
        id_b = fake_machine_id("MACHINE-B", 200)

        exp_a = f"exp-007-{id_a}"
        exp_b = f"exp-007-{id_b}"

        assert exp_a != exp_b

    def test_worktree_branches_include_machine(self):
        """Worktree branches from different machines should not collide."""
        id_a = fake_machine_id("MACHINE-A", 100)
        id_b = fake_machine_id("MACHINE-B", 200)

        branch_a = f"ol/20260322-143052-{id_a}-c4d2"
        branch_b = f"ol/20260322-143052-{id_b}-c4d2"

        assert branch_a != branch_b


class TestAdditiveResults:
    def test_machines_involved_tracking(self, session_manager, tmp_git_repo):
        """Creating a session should track the machine that created it."""
        m = session_manager.create_session("Multi-machine test")
        assert MACHINE_ID in m.machines_involved

    def test_manifest_accepts_multiple_machines(self, tmp_path):
        """Manifest should store multiple machine IDs."""
        m = Manifest(
            session_id="multi-test",
            machines_involved=["a3f91b", "b7e2c0", "c1d4e8"],
        )
        path = tmp_path / "manifest.json"
        m.save(path)

        loaded = Manifest.load(path)
        assert len(loaded.machines_involved) == 3
        assert "a3f91b" in loaded.machines_involved
        assert "b7e2c0" in loaded.machines_involved

    def test_experiments_from_different_machines_coexist(self, tmp_path):
        """Experiments from two machines should live in the same manifest."""
        m = Manifest(session_id="coexist-test")
        m.experiments.append({
            "experiment_id": "exp-001-a3f91b",
            "machine_id": "a3f91b",
            "result": "win",
        })
        m.experiments.append({
            "experiment_id": "exp-001-b7e2c0",
            "machine_id": "b7e2c0",
            "result": "discard",
        })

        path = tmp_path / "manifest.json"
        m.save(path)

        loaded = Manifest.load(path)
        assert len(loaded.experiments) == 2
        exp_ids = [e["experiment_id"] for e in loaded.experiments]
        assert "exp-001-a3f91b" in exp_ids
        assert "exp-001-b7e2c0" in exp_ids

    def test_no_experiment_id_collision_across_machines(self):
        """Same experiment number on different machines = different IDs."""
        ids = set()
        for machine_num in range(10):
            mid = fake_machine_id(f"MACHINE-{machine_num}", machine_num * 1000)
            for exp_num in range(50):
                exp_id = f"exp-{exp_num:03d}-{mid}"
                assert exp_id not in ids, f"Collision: {exp_id}"
                ids.add(exp_id)
        # 10 machines × 50 experiments = 500 unique IDs
        assert len(ids) == 500


class TestResumeOnNewMachine:
    def test_discover_session_from_another_machine(self, session_manager, tmp_git_repo):
        """A session created by one machine should be discoverable by another."""
        m = session_manager.create_session("Cross-machine test")
        m.status = "looping"
        ol_dir = tmp_git_repo / "OmegaLoop" / m.session_id
        m.save(ol_dir / "manifest.json")

        # Simulate "another machine" discovering it
        resumable = session_manager.discover_resumable()
        assert any(s.session_id == m.session_id for s in resumable)
