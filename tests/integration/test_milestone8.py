"""Milestone 8: consistent coupling, anisotropic transport, burn demos."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.io import load_config
from ouroboros.physics.coupling import coupling_power_residual_w, path_throttle_rhs
from ouroboros.physics.losses import anisotropic_transport_powers_w, compute_zone_losses

ROOT = Path(__file__).resolve().parents[2]


def test_consistent_coupling_power_identity():
    d = path_throttle_rhs(
        velocity_m_s=10.0,
        current_a=3.0,
        force_nonmagnetic_n=0.01,
        effective_inertia_kg=1e-4,
        inductance_h=1e-3,
        resistance_ohm=1e-3,
        coupling_mode="consistent",
        emf_coeff_v_s_per_m=2e-3,
    )
    assert abs(coupling_power_residual_w(d)) < 1e-12


def test_anisotropic_transport_splits():
    p_par, p_perp = anisotropic_transport_powers_w(100.0, 0.05, 0.5, 1.0)
    assert p_par > p_perp
    losses = compute_zone_losses(
        n_e_m3=1e19,
        t_e_k=1e6,
        volume_m3=1.0,
        internal_energy_j=100.0,
        tau_e_s=0.1,
        confinement_factor=1.0,
        enabled_bremsstrahlung=False,
        enabled_transport=True,
        enabled_wall=False,
        enabled_exhaust=False,
        wall_loss_coeff_s=0.0,
        exhaust_loss_coeff_s=0.0,
        z_eff=1.0,
        anisotropic_transport=True,
        tau_parallel_s=0.05,
        tau_perp_s=0.5,
    )
    assert losses.transport_w == pytest.approx(p_par + p_perp)
    assert losses.transport_parallel_w == pytest.approx(p_par)


def test_coupled_consistent_energy_trusted():
    cfg = load_config(ROOT / "configs/coupled_consistent.yaml")
    cfg.simulation.duration_s = 0.2
    result = run_simulation(cfg)
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-4
    # Currents should respond to flow under consistent EMF
    assert max(abs(x) for x in result.series["current_throttle_a"]) > 0.0


def test_multizone_dt_burn():
    cfg = load_config(ROOT / "configs/multizone_dt.yaml")
    cfg.simulation.duration_s = 0.08
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "multizone"
    assert max(result.series["fusion_power_w"]) > 0.0
    assert result.metadata.get("aborted") is not True


def test_oned_dt_burn():
    cfg = load_config(ROOT / "configs/oned_dt.yaml")
    cfg.simulation.duration_s = 0.06
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert max(result.series["fusion_power_w"]) > 0.0
    assert result.metadata.get("aborted") is not True
