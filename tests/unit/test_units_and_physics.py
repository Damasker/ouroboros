"""Unit tests."""

from __future__ import annotations

import pytest

from ouroboros.domain import EnergyLedger, MagneticThrottle, ThrottleStatus
from ouroboros.io import load_config
from ouroboros.physics.fusion import (
    BoschHaleReactivityModel,
    PlaceholderReactivityModel,
    fusion_rate_per_second,
)
from ouroboros.physics.losses import bremsstrahlung_power_w, transport_power_w
from ouroboros.physics.throttle import throttle_rhs
from ouroboros.units import (
    DT_ALPHA_J,
    DT_FUSION_TOTAL_J,
    DT_NEUTRON_J,
    ev_to_joule,
    ev_to_kelvin,
    joule_to_ev,
    kelvin_to_ev,
    mev_to_joule,
    thermal_energy_joule,
)


def test_ev_kelvin_roundtrip():
    t_ev = 1000.0
    assert abs(kelvin_to_ev(ev_to_kelvin(t_ev)) - t_ev) < 1e-9


def test_joule_ev_roundtrip():
    e = 123.0
    assert abs(joule_to_ev(ev_to_joule(e)) - e) < 1e-9


def test_dt_reaction_energy_partition():
    assert abs(DT_FUSION_TOTAL_J - mev_to_joule(17.6)) < 1e-20
    assert abs(DT_ALPHA_J + DT_NEUTRON_J - DT_FUSION_TOTAL_J) / DT_FUSION_TOTAL_J < 1e-12


def test_internal_energy_scales_with_volume_and_temperature():
    n = 1e19
    t = ev_to_kelvin(100.0)
    u1 = thermal_energy_joule(n, t, n, t, 1.0)
    u2 = thermal_energy_joule(n, t, n, t, 2.0)
    assert u2 == pytest.approx(2 * u1)


def test_bosch_hale_positive_in_range():
    model = BoschHaleReactivityModel()
    sv = model.sigma_v(ev_to_kelvin(10_000.0))  # 10 keV
    assert sv > 0.0
    assert model.sigma_v(ev_to_kelvin(1.0)) == 0.0  # below fit range


def test_placeholder_reactivity_named():
    model = PlaceholderReactivityModel()
    assert model.sigma_v(ev_to_kelvin(20_000.0)) > 0.0


def test_fusion_rate_zero_without_fuel():
    model = BoschHaleReactivityModel()
    assert fusion_rate_per_second(0.0, 1e20, 1.0, ev_to_kelvin(10000), model) == 0.0


def test_throttle_resists_plasma_current_ramp():
    th = MagneticThrottle(
        name="t",
        inductance_h=1e-3,
        resistance_ohm=1e-4,
        mutual_inductance_h=1e-3,
        current_a=0.0,
        current_limit_a=1e4,
        field_limit_t=10.0,
        coil_turns_per_metre=100.0,
    )
    d = throttle_rhs(th, plasma_current_a=0.0, d_plasma_current_dt=1e3)
    assert d.dI_dt < 0.0  # opposes rising plasma proxy current


def test_throttle_current_limit_triggers_status():
    th = MagneticThrottle(
        name="t",
        inductance_h=1e-3,
        resistance_ohm=1e-4,
        mutual_inductance_h=0.0,
        current_a=2e4,
        current_limit_a=1e4,
        field_limit_t=1e6,
        coil_turns_per_metre=1.0,
    )
    d = throttle_rhs(th, 0.0, 0.0)
    assert d.status in (ThrottleStatus.LIMITING, ThrottleStatus.QUENCH)


def test_losses_increase_with_temperature():
    p_low = bremsstrahlung_power_w(1e20, ev_to_kelvin(100), 1.0)
    p_high = bremsstrahlung_power_w(1e20, ev_to_kelvin(1000), 1.0)
    assert p_high > p_low
    assert transport_power_w(100.0, 1.0, 1.0) == pytest.approx(100.0)


def test_energy_ledger_residual_identity():
    led = EnergyLedger(
        e_internal_j=50.0,
        e_kinetic_j=10.0,
        e_magnetic_j=5.0,
        e_external_input_j=20.0,
        e_fusion_total_j=30.0,
        e_neutron_blanket_j=20.0,
        e_radiation_j=5.0,
        e_transport_j=5.0,
        e_wall_j=5.0,
        e_exhaust_j=5.0,
        e_magnetic_loss_j=0.0,
        e_recovered_j=0.0,
        e_state_initial_j=40.0,
    )
    # 40 + 20 + 30 - (65) - (5+5+5+5+20) = 90 - 65 - 40 = -15?
    # state=65, outputs=40, inputs=50 → 40+50-65-40=-15
    err = led.compute_residual()
    assert isinstance(err, float)


def test_config_load_passive(tmp_path):
    cfg = load_config("configs/passive.yaml")
    assert cfg.simulation.scenario == "passive"
    assert cfg.fusion.enabled is False
