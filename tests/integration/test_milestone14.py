"""Milestone 14: upwind momentum flux for cell_velocity."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import cell_inertias_kg, upwind_momentum_flux

ROOT = Path(__file__).resolve().parents[2]


def test_upwind_momentum_flux_dissipates_or_zero():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    # Shear: different velocities so upwinding can dissipate KE
    velocities = [20.0 if i % 2 == 0 else 5.0 for i in range(mesh.n_cells)]
    face_speeds = [10.0 for _ in mesh.faces]
    res = upwind_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        face_speeds_m_s=face_speeds,
        enabled=True,
    )
    assert len(res.dv_dt) == mesh.n_cells
    p_ke = sum(masses[i] * velocities[i] * res.dv_dt[i] for i in range(mesh.n_cells))
    assert p_ke <= 1e-12
    assert res.numerical_heating_w == pytest.approx(max(-p_ke, 0.0), abs=1e-12)


def test_momentum_flux_disabled_noop():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    velocities = [10.0] * mesh.n_cells
    face_speeds = [1.0] * len(mesh.faces)
    res = upwind_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        face_speeds_m_s=face_speeds,
        enabled=False,
    )
    assert all(x == 0.0 for x in res.dv_dt)
    assert res.numerical_heating_w == 0.0


def test_oned_momentum_flux_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_momentum_flux.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3
    assert result.config_dict["oned"]["momentum_flux"] is True
