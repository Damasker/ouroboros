"""Milestone 26: planar 3DOF orbital mechanics."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.domain.config import SpacecraftSection
from ouroboros.io import load_config
from ouroboros.physics.orbit3dof import integrate_orbit3dof_series

ROOT = Path(__file__).resolve().parents[2]


def test_orbit_keeps_finite_radius():
    sc = SpacecraftSection(
        enabled=True,
        orbit_3dof=True,
        dry_mass_kg=100.0,
        wet_mass_kg=120.0,
        gravity_mu_m3_s2=3.986e14,
        initial_x_m=6.778e6,
        initial_vy_m_s=7.67e3,
    )
    out = integrate_orbit3dof_series(
        times_s=[0.0, 1.0, 2.0],
        thrust_n=[0.0, 0.0, 0.0],
        mass_flow_kg_s=[0.0, 0.0, 0.0],
        spacecraft=sc,
    )
    assert all(math.isfinite(r) and r > 1e6 for r in out["orbit_radius_m"])


def test_orbit_3dof_scenario():
    cfg = load_config(ROOT / "configs/orbit_3dof.yaml")
    cfg.simulation.duration_s = 0.1
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["spacecraft"]["orbit_3dof"] is True
    assert "orbit_x_m" in result.series
    assert result.series["orbit_radius_m"][0] == pytest.approx(6.778e6, rel=1e-6)
