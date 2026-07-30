"""Tests for multi-zone 0D model (Milestone 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ouroboros.core import build_system, run_simulation
from ouroboros.core.multizone import MultiZoneSystem
from ouroboros.geometry.network import build_zone_network
from ouroboros.io import load_config, write_run_directory

ROOT = Path(__file__).resolve().parents[2]


def test_zone_network_has_expected_topology():
    net = build_zone_network()
    assert net.n_zones >= 8
    assert "reaction_chamber" in net.zone_index
    assert "branch_a" in net.zone_index
    assert "branch_b" in net.zone_index
    ids = {e.source + "->" + e.target for e in net.edges}
    assert "throttle_a->reaction_chamber" in ids
    assert "return_to_split->feed_a" in ids


def test_build_system_dispatches_multizone():
    cfg = load_config(ROOT / "configs/multizone_passive.yaml")
    sys = build_system(cfg)
    assert isinstance(sys, MultiZoneSystem)
    assert sys.layout.n_zones == sys.network.n_zones


def test_multizone_passive_energy_and_decay(tmp_path: Path):
    cfg = load_config(ROOT / "configs/multizone_passive.yaml")
    cfg.simulation.duration_s = 0.2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "multizone"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-4
    assert abs(result.series["flow_a"][-1]) < abs(cfg.plasma.initial_flow_a_m_s)
    assert "zone_density:reaction_chamber" in result.series
    out = write_run_directory(result, tmp_path)
    frame = json.loads((out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    seg_ids = {s["id"] for s in frame["segments"]}
    assert "reaction_chamber" in seg_ids
    assert "branch_a" in seg_ids
    assert len(frame["segments"]) >= 8


def test_multizone_particle_conservation_no_sources():
    cfg = load_config(ROOT / "configs/multizone_passive.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.drive.fueling_rate_s = 0.0
    cfg.fusion.enabled = False
    sys = MultiZoneSystem(cfg)
    y0 = sys.initial_state()
    n0 = float(sum(y0[sys.layout.idx_n(i)] for i in range(sys.layout.n_zones)))
    from scipy.integrate import solve_ivp

    sys2 = MultiZoneSystem(cfg)
    y = sys2.initial_state()
    sol = solve_ivp(sys2.rhs, (0, 0.1), y, method="LSODA", rtol=1e-7, atol=1e-10, max_step=1e-3)
    assert sol.success
    n1 = float(sum(sol.y[sys2.layout.idx_n(i), -1] for i in range(sys2.layout.n_zones)))
    assert n1 == pytest.approx(n0, rel=1e-6, abs=1.0)


def test_multizone_driven_runs():
    cfg = load_config(ROOT / "configs/multizone_driven.yaml")
    cfg.simulation.duration_s = 0.08
    cfg.simulation.output_interval_s = 0.01
    result = run_simulation(cfg)
    assert len(result.times_s) >= 2
    assert result.metadata.get("aborted") is not True
    assert max(result.series["external_power_w"]) > 0.0
