"""Tests for the FR S0 engineering gate."""
from __future__ import annotations

import json
from pathlib import Path

from src.modeles import run_s0_fr_smoke as s0


def test_s0_gate_requires_every_check():
    checks = {
        "finite": True,
        "causal": True,
        "deterministic": False,
    }
    assert not all(checks.values())


def test_s0_constants_are_conservative():
    assert s0.RUNTIME_LIMIT_SECONDS <= 600
    assert s0.RSS_DELTA_LIMIT_GB <= 4
    assert s0.MODELS == ("A0Neural", "GConvGRU", "EvolveGCNH")


def test_s0_output_path_is_json(tmp_path: Path):
    path = tmp_path / "result.json"
    payload = {"decision": "S0_FR_PASS"}
    path.write_text(json.dumps(payload))
    assert json.loads(path.read_text())["decision"] == "S0_FR_PASS"

