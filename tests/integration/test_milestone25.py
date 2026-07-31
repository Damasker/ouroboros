"""Milestone 25: native client bridge protocol."""

from __future__ import annotations

from pathlib import Path

from ouroboros.core import run_simulation
from ouroboros.io import load_config, write_run_directory
from ouroboros.io.client_bridge import PROTOCOL_VERSION, build_client_frame, protocol_manifest

ROOT = Path(__file__).resolve().parents[2]


def test_protocol_manifest():
    m = protocol_manifest()
    assert m["version"] == PROTOCOL_VERSION
    assert "godot4" in m["engines"]


def test_client_frame_shape():
    fr = build_client_frame(
        run_id="x",
        time_s=0.1,
        segments=[{"id": "branch_a", "density": 1.0}],
        spacecraft={"mass_kg": 500.0},
    )
    assert fr["protocol"] == "ouroboros.client"
    assert fr["segments"][0]["id"] == "branch_a"


def test_client_stream_written(tmp_path: Path):
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.simulation.duration_s = 0.05
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    run_dir = write_run_directory(result, tmp_path)
    stream = run_dir / "client_stream.jsonl"
    assert stream.is_file()
    lines = [ln for ln in stream.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1


def test_engine_stubs_exist():
    assert (ROOT / "clients/godot/OuroborosClient.gd").is_file()
    assert (ROOT / "clients/unity/OuroborosClient.cs").is_file()
