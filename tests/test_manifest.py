"""Tests for Manifest dataclass — save, load, roundtrip, schema."""

import json
from pathlib import Path

from orchestrator.engine import Manifest, Status


class TestManifestSaveLoad:
    def test_save_creates_file(self, tmp_path):
        m = Manifest(session_id="test-session", research_prompt="Test")
        path = tmp_path / "manifest.json"
        m.save(path)
        assert path.exists()

    def test_save_valid_json(self, tmp_path):
        m = Manifest(session_id="test-session", research_prompt="Test")
        path = tmp_path / "manifest.json"
        m.save(path)
        data = json.loads(path.read_text())
        assert data["session_id"] == "test-session"

    def test_load_roundtrip(self, tmp_path):
        original = Manifest(
            session_id="roundtrip-test",
            research_prompt="Does it roundtrip?",
            experiment_count=42,
            win_count=7,
            status=Status.LOOPING,
            insights=["insight 1", "insight 2"],
        )
        path = tmp_path / "manifest.json"
        original.save(path)

        loaded = Manifest.load(path)
        assert loaded.session_id == "roundtrip-test"
        assert loaded.experiment_count == 42
        assert loaded.win_count == 7
        assert loaded.status == Status.LOOPING
        assert loaded.insights == ["insight 1", "insight 2"]

    def test_save_updates_timestamp(self, tmp_path):
        m = Manifest(session_id="ts-test")
        assert m.updated_at == ""
        path = tmp_path / "manifest.json"
        m.save(path)
        assert m.updated_at != ""

    def test_load_ignores_unknown_fields(self, tmp_path):
        """Future schema additions shouldn't break loading old manifests."""
        path = tmp_path / "manifest.json"
        data = {"session_id": "compat-test", "research_prompt": "x", "future_field": "hello"}
        path.write_text(json.dumps(data))
        m = Manifest.load(path)
        assert m.session_id == "compat-test"


class TestManifestFromFixture:
    def test_load_full_fixture(self, sample_manifest):
        m = Manifest(**{k: v for k, v in sample_manifest.items() if k in Manifest.__dataclass_fields__})
        assert m.session_id == "20260322-143052-a3f91b-c4d2"
        assert m.experiment_count == 5
        assert m.win_count == 2
        assert len(m.experiments) == 1
        assert m.experiments[0]["result"] == "win"

    def test_load_minimal_fixture(self, minimal_manifest):
        m = Manifest(**{k: v for k, v in minimal_manifest.items() if k in Manifest.__dataclass_fields__})
        assert m.session_id == "20260322-100000-b7e2c0-abcd"
        assert m.experiment_count == 0
        assert m.experiments == []

    def test_schema_version(self, sample_manifest):
        assert sample_manifest["schema_version"] == "2.0"


class TestManifestExperimentAppend:
    def test_append_experiment(self, tmp_path):
        m = Manifest(session_id="append-test")
        m.experiments.append({
            "experiment_id": "exp-001-a3f91b",
            "result": "win",
            "hypothesis": "test hypothesis",
        })
        m.experiment_count = 1

        path = tmp_path / "manifest.json"
        m.save(path)

        loaded = Manifest.load(path)
        assert len(loaded.experiments) == 1
        assert loaded.experiments[0]["experiment_id"] == "exp-001-a3f91b"

    def test_experiments_are_append_only(self, tmp_path):
        """Verify experiments accumulate across saves."""
        path = tmp_path / "manifest.json"
        m = Manifest(session_id="accum-test")

        for i in range(5):
            m.experiments.append({"experiment_id": f"exp-{i:03d}", "result": "discard"})
            m.experiment_count = i + 1
            m.save(path)

        loaded = Manifest.load(path)
        assert len(loaded.experiments) == 5
        assert loaded.experiment_count == 5
