"""Milestone 23: HLLD-like MHD Riemann."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import cell_inertias_kg, hlld_energy_flux, hlld_momentum_flux

ROOT = Path(__file__).resolve().parents[2]


def test_hlld_energy_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1e-4)
    velocities = [10.0 + i for i in range(mesh.n_cells)]
    pressures = [1.0e3 + 30.0 * i for i in range(mesh.n_cells)]
    internals = [2.0e3 + 5.0 * i for i in range(mesh.n_cells)]
    pmag = [50.0 + i for i in range(mesh.n_cells)]
    factors = [1.0] * len(mesh.faces)
    mflux = hlld_momentum_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        face_area_factors=factors,
        pressure_scale=1e-6,
        magnetic_pressures_pa=pmag,
        enabled=True,
    )
    eflux = hlld_energy_flux(
        mesh,
        masses_kg=masses,
        velocities_m_s=velocities,
        pressures_pa=pressures,
        internal_energy_j=internals,
        face_area_factors=factors,
        pressure_scale=1e-6,
        dv_dt=mflux.dv_dt,
        magnetic_pressures_pa=pmag,
        enabled=True,
    )
    p_ke = sum(masses[i] * velocities[i] * mflux.dv_dt[i] for i in range(mesh.n_cells))
    assert sum(eflux.du_dt) + p_ke == pytest.approx(0.0, abs=1e-8)


def test_oned_hlld_scenario_trusted():
    cfg = load_config(ROOT / "configs/oned_hlld.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["oned"]["riemann"] == "hlld"
