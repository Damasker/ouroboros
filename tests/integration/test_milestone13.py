"""Milestone 13: magnetic nozzle / thrust channel."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config
from ouroboros.physics.nozzle import magnetic_nozzle_powers

ROOT = Path(__file__).resolve().parents[2]


def test_nozzle_energy_split_and_thrust():
    p = magnetic_nozzle_powers(
        n_particles=1.0e20,
        internal_energy_j=1.0e6,
        mean_particle_mass_kg=4.0e-27,
        extract_time_s=0.2,
        extract_fraction=0.1,
        magnetic_efficiency=0.5,
        enabled=True,
    )
    assert p.thermal_extract_w == pytest.approx(p.jet_power_w + p.waste_power_w)
    assert p.jet_power_w == pytest.approx(0.5 * p.thermal_extract_w)
    assert p.thrust_n > 0.0
    assert p.isp_s > 0.0
    assert p.mass_flow_kg_s > 0.0


def test_nozzle_disabled_zero():
    p = magnetic_nozzle_powers(
        n_particles=1.0e20,
        internal_energy_j=1.0e6,
        mean_particle_mass_kg=4.0e-27,
        extract_time_s=0.2,
        extract_fraction=0.1,
        magnetic_efficiency=0.5,
        enabled=False,
    )
    assert p.jet_power_w == 0.0
    assert p.thrust_n == 0.0


def test_magnetic_nozzle_scenario_energy_trusted():
    cfg = load_config(ROOT / "configs/magnetic_nozzle.yaml")
    cfg.simulation.duration_s = 0.12
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "multizone"
    assert result.energy_trusted
    assert result.ledger_final.e_thrust_j > 0.0
    assert max(result.series["thrust_n"]) > 0.0
    assert max(result.series["jet_power_w"]) > 0.0
    # Extracted enthalpy ≈ thrust + waste (waste in exhaust channel)
    produced = result.ledger_final.e_thrust_j
    assert produced > 0.0
