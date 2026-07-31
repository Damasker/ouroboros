"""Milestone 17: Rusanov total-energy Riemann flux."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import (
    cell_inertias_kg,
    hllc_momentum_flux,
    rusanov_energy_flux,
)

ROOT = Path(__file__).resolve().parents[2]


def test_rusanov_energy_flux_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    velocities = [15.0 + i for i in range(mesh.n_cells)]
    pressures = [1.0e3 + 50.0 * i for i in range(mesh.n_cells)]
    internals = [2.0e3 + 10.0 * i for i in range(mesh.n_cells)]
    factors = [1.0] * len(mesh.faces)
    mflux = hllc_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        face_area_factors=factors,
        pressure_scale=1e-6,
        enabled=True,
    )
    eflux = rusanov_energy_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        internal_energy_j=internals,
        face_area_factors=factors,
        pressure_scale=1e-6,
        dv_dt=mflux.dv_dt,
        enabled=True,
    )
    # Closed mesh: ∑dE = 0 ⇒ ∑dU + ∑m v dv = 0
    p_ke = sum(masses[i] * velocities[i] * mflux.dv_dt[i] for i in range(mesh.n_cells))
    assert sum(eflux.du_dt) + p_ke == pytest.approx(0.0, abs=1e-9)


def test_rusanov_energy_disabled_noop():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    res = rusanov_energy_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=[1.0] * mesh.n_cells,
        pressures_pa=[1.0] * mesh.n_cells,
        internal_energy_j=[1.0] * mesh.n_cells,
        face_area_factors=[1.0] * len(mesh.faces),
        pressure_scale=1.0,
        dv_dt=[0.0] * mesh.n_cells,
        enabled=False,
    )
    assert all(x == 0.0 for x in res.du_dt)


def test_oned_energy_flux_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_energy_flux.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3
    assert result.config_dict["oned"]["riemann"] == "hllc"
    assert result.config_dict["oned"]["riemann_energy"] is True
