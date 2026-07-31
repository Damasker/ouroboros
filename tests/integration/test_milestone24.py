"""Milestone 24: multi-zone CAD-proxy neutronics."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config
from ouroboros.physics.neutronics_zones import (
    BlanketLayer,
    default_cad_proxy_layers,
    zone_mc_capture,
)

ROOT = Path(__file__).resolve().parents[2]


def test_zone_mc_deterministic():
    layers = default_cad_proxy_layers()
    a = zone_mc_capture(layers, n_particles=64, seed=3)
    b = zone_mc_capture(layers, n_particles=64, seed=3)
    assert a.capture_fraction == b.capture_fraction
    assert sum(a.layer_deposits.values()) == pytest.approx(a.capture_fraction)


def test_zone_mc_empty_layers():
    r = zone_mc_capture([], n_particles=8, seed=0)
    assert r.capture_fraction == 0.0


def test_dt_blanket_zones_trusted():
    cfg = load_config(ROOT / "configs/dt_blanket_zones.yaml")
    cfg.simulation.duration_s = 0.05
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.config_dict["blanket"]["transport"] == "zones"
