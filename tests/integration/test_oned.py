"""Tests for 1D finite-volume loop model (Milestone 7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scipy.integrate import solve_ivp

from ouroboros.core import build_system, run_simulation
from ouroboros.core.oned import OneDSystem
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config, write_run_directory

ROOT = Path(__file__).resolve().parents[2]


def test_oned_mesh_has_cells_and_faces():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    mesh = build_oned_mesh(cfg)
    assert mesh.n_cells == len(mesh.network.zones) * cfg.oned.cells_per_segment  # type: ignore[union-attr]
    assert len(mesh.faces) > mesh.n_cells  # intra + inter segment
    assert mesh.chamber_cells


def test_build_system_dispatches_oned():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    sys = build_system(cfg)
    assert isinstance(sys, OneDSystem)


def test_oned_passive_energy_mass_and_snapshots(tmp_path: Path):
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.simulation.duration_s = 0.15
    cfg.oned.cells_per_segment = 3
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3
    assert abs(result.series["flow_a"][-1]) < abs(cfg.plasma.initial_flow_a_m_s)
    assert result.series["n_cells"][0] >= 3 * 8
    out = write_run_directory(result, tmp_path)
    lines = (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
    frame = json.loads(lines[-1])
    assert frame["snapshot_schema_version"] == "1.1.0"
    assert len(frame["segments"]) >= 8
    assert "cells" in frame
    assert len(frame["cells"]) >= 3


def test_oned_particle_conservation_closed_loop():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    cfg.fusion.enabled = False
    cfg.drive.fueling_rate_s = 0.0
    sys = OneDSystem(cfg)
    y0 = sys.initial_state()
    n0 = float(sum(y0[sys.layout.idx_n(i)] for i in range(sys.layout.n_cells)))
    sol = solve_ivp(sys.rhs, (0.0, 0.08), y0, method="LSODA", rtol=1e-7, atol=1e-10, max_step=1e-3)
    assert sol.success
    n1 = float(sum(sol.y[sys.layout.idx_n(i), -1] for i in range(sys.layout.n_cells)))
    assert n1 == pytest.approx(n0, rel=1e-5, abs=1.0)


def test_oned_driven_runs():
    cfg = load_config(ROOT / "configs/oned_driven.yaml")
    cfg.simulation.duration_s = 0.08
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert len(result.times_s) >= 2
    assert result.metadata.get("aborted") is not True
    assert max(result.series["external_power_w"]) > 0.0
