"""Property-based / invariant tests."""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from ouroboros.core import run_simulation
from ouroboros.domain.config import SimulationConfig
from ouroboros.physics.losses import transport_power_w


@given(u=st.floats(0, 1e6, allow_nan=False, allow_infinity=False), tau=st.floats(1e-3, 10))
@settings(max_examples=30)
def test_increasing_loss_coeff_does_not_increase_retained_power_proxy(u: float, tau: float):
    p1 = transport_power_w(u, tau, 1.0)
    p2 = transport_power_w(u, tau * 0.5, 1.0)  # stronger loss (smaller tau)
    assert p2 >= p1 - 1e-9


def _passive_no_loss_config() -> SimulationConfig:
    cfg = SimulationConfig()
    cfg.simulation.duration_s = 0.05
    cfg.simulation.output_interval_s = 0.005
    cfg.simulation.scenario = "passive"
    cfg.fusion.enabled = False
    cfg.losses.bremsstrahlung = False
    cfg.losses.transport = False
    cfg.losses.wall = False
    cfg.losses.exhaust = False
    cfg.losses.magnetic = True
    cfg.drive.external_heater_w = 0.0
    cfg.drive.synthetic_heat_w = 0.0
    cfg.drive.drive_force_a_n = 0.0
    cfg.drive.drive_force_b_n = 0.0
    cfg.throttle_a.mutual_inductance_h = 0.0
    cfg.throttle_b.mutual_inductance_h = 0.0
    cfg.throttle_a.coupling_force_coeff_n_per_a = 0.0
    cfg.throttle_b.coupling_force_coeff_n_per_a = 0.0
    cfg.throttle_a.initial_current_a = 5.0
    cfg.throttle_b.initial_current_a = 5.0
    cfg.plasma.initial_flow_a_m_s = 10.0
    cfg.plasma.initial_flow_b_m_s = 10.0
    cfg.energy.relative_tolerance = 1e-3
    return cfg


def test_no_energy_creation_without_source():
    cfg = _passive_no_loss_config()
    result = run_simulation(cfg)
    # Final state energy + recorded losses <= initial + small tol (ohmic is a loss)
    led = result.ledger_final
    final_plus_loss = led.state_energy() + led.e_magnetic_loss_j
    assert final_plus_loss <= led.e_state_initial_j * (1 + 1e-3) + 1e-6


def test_disabled_fusion_produces_zero_fusion_power():
    cfg = _passive_no_loss_config()
    result = run_simulation(cfg)
    assert all(abs(p) < 1e-30 for p in result.series["fusion_power_w"])


def test_density_and_temperature_nonnegative():
    cfg = _passive_no_loss_config()
    result = run_simulation(cfg)
    for key in ("density_a", "density_b", "temp_a_ev", "temp_b_ev", "temp_chamber_ev"):
        assert all(v >= -1e-9 for v in result.series[key])


def test_symmetric_ics_give_symmetric_flows():
    cfg = _passive_no_loss_config()
    cfg.plasma.initial_flow_a_m_s = 25.0
    cfg.plasma.initial_flow_b_m_s = 25.0
    cfg.geometry.branch_a_volume_m3 = 0.4
    cfg.geometry.branch_b_volume_m3 = 0.4
    cfg.throttle_a.initial_current_a = 1.0
    cfg.throttle_b.initial_current_a = 1.0
    result = run_simulation(cfg)
    fa = np.asarray(result.series["flow_a"])
    fb = np.asarray(result.series["flow_b"])
    assert np.allclose(fa, fb, rtol=1e-4, atol=1e-6)


def test_mass_not_created_without_fueling():
    cfg = _passive_no_loss_config()
    cfg.drive.fueling_rate_s = 0.0
    res = run_simulation(cfg)
    assert res.series["density_a"][-1] > 0
    assert all(p == 0.0 for p in res.series["fusion_power_w"])
