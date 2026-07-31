"""Milestone 20: Monte Carlo neutron capture."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config
from ouroboros.physics.neutron_mc import mc_neutron_capture_fraction

ROOT = Path(__file__).resolve().parents[2]


def test_mc_capture_deterministic():
    a = mc_neutron_capture_fraction(optical_depth=0.8, n_particles=64, seed=1)
    b = mc_neutron_capture_fraction(optical_depth=0.8, n_particles=64, seed=1)
    assert a.capture_fraction == b.capture_fraction
    assert 0.0 < a.capture_fraction < 1.0


def test_mc_zero_optical_depth():
    r = mc_neutron_capture_fraction(optical_depth=0.0, n_particles=32, seed=0)
    assert r.capture_fraction == 0.0


def test_dt_blanket_mc_trusted():
    cfg = load_config(ROOT / "configs/dt_blanket_mc.yaml")
    cfg.simulation.duration_s = 0.05
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["blanket"]["transport"] == "mc"
    assert result.ledger_final.blanket_dynamic is True
