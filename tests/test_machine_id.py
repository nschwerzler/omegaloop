"""Tests for machine ID generation."""

import hashlib
import platform
import uuid

from orchestrator.engine import get_machine_id, MACHINE_ID


class TestMachineId:
    def test_returns_6_chars(self):
        mid = get_machine_id()
        assert len(mid) == 6

    def test_is_hex_string(self):
        mid = get_machine_id()
        assert all(c in "0123456789abcdef" for c in mid)

    def test_stable_across_calls(self):
        """Same machine should always produce the same ID."""
        id1 = get_machine_id()
        id2 = get_machine_id()
        assert id1 == id2

    def test_module_level_matches(self):
        """MACHINE_ID constant should match get_machine_id()."""
        assert MACHINE_ID == get_machine_id()

    def test_uses_hostname_and_mac(self):
        """Verify the ID is derived from hostname + MAC."""
        raw = f"{platform.node()}-{uuid.getnode()}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:6]
        assert get_machine_id() == expected

    def test_different_inputs_differ(self):
        """Different hostname+MAC combinations should produce different IDs."""
        raw_a = "DESKTOP-A-123456789"
        raw_b = "LAPTOP-B-987654321"
        id_a = hashlib.sha256(raw_a.encode()).hexdigest()[:6]
        id_b = hashlib.sha256(raw_b.encode()).hexdigest()[:6]
        assert id_a != id_b

    def test_collision_probability(self):
        """Spot check: 1000 random inputs should produce 1000 unique IDs."""
        ids = set()
        for i in range(1000):
            raw = f"host-{i}-{i * 17}"
            mid = hashlib.sha256(raw.encode()).hexdigest()[:6]
            ids.add(mid)
        assert len(ids) == 1000
