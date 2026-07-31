"""Milestone 19: Roe Riemann + wave-MHD pressure augmentation."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import cell_inertias_kg, roe_energy_flux, roe_momentum_flux

ROOT = Path(__file__).resolve().parents[2]


def test_roe_energy_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    velocities = [12.0 + i for i in range(mesh.n_cells)]
    pressures = [1.0e3 + 40.0 * i for i in range(mesh.n_cells)]
    internals = [2.0e3 + 8.0 * i for i in range(mesh.n_cells)]
    factors = [1.0] * len(mesh.faces)
    mflux = roe_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        face_area_factors=factors,
        pressure_scale=1e-6,
        enabled=True,
    )
    eflux = roe_energy_flux(
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
    p_ke = sum(masses[i] * velocities[i] * mflux.dv_dt[i] for i in range(mesh.n_cells))
    assert sum(eflux.du_dt) + p_ke == pytest.approx(0.0, abs=1e-8)


def test_oned_roe_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_roe.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["oned"]["riemann"] == "roe"


def test_oned_wave_mhd_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_wave_mhd.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["oned"]["wave_mhd"] is True
