"""Integration tests for scenarios and I/O."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config, write_run_directory
from ouroboros.viz import plot_all

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "config_path",
    [
        "configs/passive.yaml",
        "configs/driven.yaml",
        "configs/synthetic_oscillation.yaml",
        "configs/dt_fusion.yaml",
        "configs/coupled_throttle.yaml",
        "configs/faults/block_branch_a.yaml",
        "configs/faults/quench.yaml",
        "configs/faults/heater_trip.yaml",
    ],
)
def test_scenario_runs(config_path: str, tmp_path: Path):
    cfg = load_config(ROOT / config_path)
    cfg.simulation.duration_s = min(float(cfg.simulation.duration_s), 0.08)
    cfg.simulation.output_interval_s = max(float(cfg.simulation.output_interval_s), 0.01)
    cfg.numerics.max_nfev = 50000
    result = run_simulation(cfg)
    assert len(result.times_s) >= 2
    assert result.metadata.get("aborted") is not True
    out = write_run_directory(result, tmp_path)
    assert (out / "timeseries.csv").exists()
    assert (out / "energy_report.json").exists()
    assert (out / "snapshots.jsonl").exists()
    energy = json.loads((out / "energy_report.json").read_text(encoding="utf-8"))
    assert "ledger" in energy
    line = (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()[0]
    frame = json.loads(line)
    assert frame["snapshot_schema_version"].startswith("1.")
    assert "segments" in frame


def test_passive_circulation_decays_and_exports(tmp_path: Path):
    cfg = load_config(ROOT / "configs/passive.yaml")
    cfg.simulation.duration_s = 0.2
    result = run_simulation(cfg)
    assert abs(result.series["flow_a"][-1]) < abs(cfg.plasma.initial_flow_a_m_s)
    assert result.energy_trusted
    out = write_run_directory(result, tmp_path)
    plots = plot_all(out)
    assert len(plots) >= 10


def test_dt_fusion_produces_nonzero_power():
    cfg = load_config(ROOT / "configs/dt_fusion.yaml")
    cfg.simulation.duration_s = 0.05
    cfg.simulation.output_interval_s = 0.01
    result = run_simulation(cfg)
    assert max(result.series["fusion_power_w"]) > 0.0
    assert max(result.series["neutron_power_w"]) > 0.0
    assert max(result.series["alpha_power_w"]) > 0.0


def test_export_reread_config(tmp_path: Path):
    cfg = load_config(ROOT / "configs/passive.yaml")
    result = run_simulation(cfg)
    out = write_run_directory(result, tmp_path)
    cfg2 = load_config(out / "config.yaml")
    assert cfg2.simulation.scenario == cfg.simulation.scenario
