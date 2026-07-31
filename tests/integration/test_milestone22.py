"""Milestone 22: enhanced nozzle + spacecraft trajectory."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.domain.config import SpacecraftSection
from ouroboros.io import load_config
from ouroboros.physics.nozzle import magnetic_nozzle_powers
from ouroboros.physics.trajectory import integrate_trajectory_series

ROOT = Path(__file__).resolve().parents[2]


def test_ideal_blend_changes_exhaust():
    base = magnetic_nozzle_powers(
        n_particles=1e20,
        internal_energy_j=1e5,
        mean_particle_mass_kg=3.3e-27,
        extract_time_s=0.2,
        extract_fraction=0.1,
        magnetic_efficiency=0.6,
        enabled=True,
    )
    blended = magnetic_nozzle_powers(
        n_particles=1e20,
        internal_energy_j=1e5,
        mean_particle_mass_kg=3.3e-27,
        extract_time_s=0.2,
        extract_fraction=0.1,
        magnetic_efficiency=0.6,
        enabled=True,
        expansion_ratio=10.0,
        thermal_velocity_blend=0.8,
        ion_temperature_k=1e6,
    )
    assert blended.exhaust_velocity_m_s != pytest.approx(base.exhaust_velocity_m_s)
    assert blended.jet_power_w + blended.waste_power_w == pytest.approx(
        blended.thermal_extract_w, rel=1e-12
    )


def test_trajectory_integration_monotonic_dv():
    sc = SpacecraftSection(enabled=True, dry_mass_kg=100.0, wet_mass_kg=150.0)
    out = integrate_trajectory_series(
        times_s=[0.0, 0.1, 0.2],
        thrust_n=[10.0, 10.0, 10.0],
        mass_flow_kg_s=[1.0, 1.0, 1.0],
        spacecraft=sc,
    )
    assert out["delta_v_m_s"][0] == 0.0
    assert out["delta_v_m_s"][-1] > out["delta_v_m_s"][0]
    assert out["spacecraft_mass_kg"][-1] <= out["spacecraft_mass_kg"][0]


def test_nozzle_trajectory_scenario():
    cfg = load_config(ROOT / "configs/nozzle_trajectory.yaml")
    cfg.simulation.duration_s = 0.1
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["spacecraft"]["enabled"] is True
    assert "delta_v_m_s" in result.series
    assert result.series["delta_v_m_s"][-1] >= 0.0
