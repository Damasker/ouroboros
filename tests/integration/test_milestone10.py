"""Milestone 10: energy-consistent reduced MHD."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config
from ouroboros.physics.reduced_mhd import (
    ReducedMHDForces,
    compute_reduced_mhd_forces,
    hydrodynamic_pressure_force_n,
    magnetic_pressure_force_n,
)

ROOT = Path(__file__).resolve().parents[2]


def test_magnetic_pressure_opposes_flow():
    f_pos = magnetic_pressure_force_n(
        velocity_m_s=10.0,
        current_a=100.0,
        cross_section_m2=0.05,
        coil_turns_per_metre=50.0,
        enabled=True,
        scale=1.0,
    )
    f_neg = magnetic_pressure_force_n(
        velocity_m_s=-10.0,
        current_a=100.0,
        cross_section_m2=0.05,
        coil_turns_per_metre=50.0,
        enabled=True,
        scale=1.0,
    )
    assert f_pos < 0.0
    assert f_neg > 0.0


def test_exchange_power_identity():
    mhd = ReducedMHDForces(
        force_mp_a_n=-2.0,
        force_mp_b_n=-1.0,
        force_pressure_a_n=0.5,
        force_pressure_b_n=0.0,
    )
    v_a, v_b = 3.0, 4.0
    # Kinetic power from these forces = F·v; internal gets −F·v
    p_kin = (mhd.force_mp_a_n + mhd.force_pressure_a_n) * v_a
    p_kin += (mhd.force_mp_b_n + mhd.force_pressure_b_n) * v_b
    assert mhd.exchange_power_to_internal_w(v_a, v_b) == pytest.approx(-p_kin)


def test_hydro_pressure_drive_sign():
    f = hydrodynamic_pressure_force_n(
        p_upstream_pa=200.0,
        p_downstream_pa=100.0,
        cross_section_m2=0.05,
        enabled=True,
        scale=1.0,
    )
    assert f == pytest.approx(5.0)


def test_compute_forces_split_channels():
    mhd = compute_reduced_mhd_forces(
        v_a=20.0,
        v_b=15.0,
        i_a=80.0,
        i_b=60.0,
        dens_a=1e19,
        dens_b=1e19,
        mean_particle_mass_kg=4e-27,
        cross_section_m2=0.05,
        turns_a=100.0,
        turns_b=100.0,
        enabled=True,
        magnetic_pressure_scale=0.01,
        alfven_damping_fraction=1e-3,
        pressure_drive=True,
        pressure_drive_scale=1e-6,
        p_a_pa=1e3,
        p_b_pa=1e3,
        p_c_pa=5e2,
        p_r_pa=1.2e3,
    )
    assert mhd.force_diss_a_n != 0.0 or mhd.force_mp_a_n != 0.0
    assert mhd.force_a_n == pytest.approx(
        mhd.force_diss_a_n + mhd.force_mp_a_n + mhd.force_pressure_a_n
    )
    assert mhd.dissipative_power_w(20.0, 15.0) >= 0.0


def test_reduced_mhd_scenario_energy_trusted():
    cfg = load_config(ROOT / "configs/reduced_mhd.yaml")
    cfg.simulation.duration_s = 0.2
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-4
    # MHD channels should have acted (currents + flows nonzero)
    assert max(abs(x) for x in result.series["flow_a"]) > 0.0


def test_magnetic_pressure_without_exchange_may_untrust():
    """Document legacy path: mp work without compressional exchange can break ledger."""
    cfg = load_config(ROOT / "configs/reduced_mhd.yaml")
    cfg.simulation.duration_s = 0.15
    cfg.reduced_mhd.compressional_exchange = False
    cfg.reduced_mhd.pressure_drive = False
    cfg.reduced_mhd.alfven_damping_fraction = 0.0
    cfg.reduced_mhd.magnetic_pressure_scale = 1.0  # strong
    result = run_simulation(cfg)
    # Either residual grows or still ok if work ~0; assert exchange-on path is preferred
    cfg2 = load_config(ROOT / "configs/reduced_mhd.yaml")
    cfg2.simulation.duration_s = 0.15
    cfg2.reduced_mhd.compressional_exchange = True
    cfg2.reduced_mhd.magnetic_pressure_scale = 1.0
    cfg2.reduced_mhd.pressure_drive = False
    cfg2.reduced_mhd.alfven_damping_fraction = 0.0
    good = run_simulation(cfg2)
    assert good.energy_trusted
    assert good.ledger_final.relative_residual <= result.ledger_final.relative_residual + 1e-6
