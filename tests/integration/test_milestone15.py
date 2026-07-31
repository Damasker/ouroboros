"""Milestone 15: Rusanov Riemann momentum+pressure fluxes."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import cell_inertias_kg, rusanov_momentum_flux
from ouroboros.units import pressure_pa

ROOT = Path(__file__).resolve().parents[2]


def test_rusanov_energy_exchange_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    velocities = [15.0 + i for i in range(mesh.n_cells)]
    pressures = [1.0e3 + 50.0 * i for i in range(mesh.n_cells)]
    factors = [1.0] * len(mesh.faces)
    res = rusanov_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        face_area_factors=factors,
        pressure_scale=1e-6,
        enabled=True,
    )
    p_ke = sum(masses[i] * velocities[i] * res.dv_dt[i] for i in range(mesh.n_cells))
    assert res.numerical_heating_w == pytest.approx(-p_ke, rel=1e-12, abs=1e-12)


def test_rusanov_disabled_noop():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    res = rusanov_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=[1.0] * mesh.n_cells,
        pressures_pa=[1.0] * mesh.n_cells,
        face_area_factors=[1.0] * len(mesh.faces),
        pressure_scale=1.0,
        enabled=False,
    )
    assert all(x == 0.0 for x in res.dv_dt)


def test_oned_rusanov_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_rusanov.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3
    assert result.config_dict["oned"]["riemann"] == "rusanov"
    # Sanity: pressures finite in plasma
    assert pressure_pa(1e19, 1e6, 1e19, 1e6) > 0.0
