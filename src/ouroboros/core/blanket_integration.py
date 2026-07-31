"""Helpers for neutron blanket integration into ODE systems."""

from __future__ import annotations

from ouroboros.domain import EnergyLedger
from ouroboros.domain.config import SimulationConfig
from ouroboros.physics.blanket import BlanketPowers, blanket_rhs
from ouroboros.physics.neutron_mc import mc_neutron_capture_fraction


def _capture_fraction(cfg: SimulationConfig) -> float:
    if cfg.blanket.transport == "mc":
        return mc_neutron_capture_fraction(
            optical_depth=cfg.blanket.mc_optical_depth,
            n_particles=cfg.blanket.mc_particles,
            seed=cfg.blanket.mc_seed,
        ).capture_fraction
    return cfg.blanket.capture_fraction


def apply_blanket_ode(
    *,
    cfg: SimulationConfig,
    neutron_power_w: float,
    e_blanket_j: float,
) -> tuple[float, float, float, float, BlanketPowers]:
    """
    Returns (dE_blanket/dt, d_acc_neut_out/dt, d_acc_leak/dt, d_acc_coolant/dt, powers).

    When blanket disabled: neut_out = full neutron power (legacy), leak=coolant=0, dE=0.
    When enabled: neut_out=0 for legacy channel; leak and coolant accumulate; dE from capture-extract.
    """
    dE, _dT, powers = blanket_rhs(
        neutron_power_w=neutron_power_w,
        thermal_energy_j=e_blanket_j,
        capture_fraction=_capture_fraction(cfg),
        coolant_time_s=cfg.blanket.coolant_time_s,
        breeding_ratio=cfg.blanket.breeding_ratio,
        enabled=cfg.blanket.enabled,
    )
    if cfg.blanket.enabled:
        return dE, 0.0, powers.leaked_w, powers.coolant_extract_w, powers
    return 0.0, neutron_power_w, 0.0, 0.0, powers


def fill_neutron_ledger_fields(
    ledger: EnergyLedger,
    *,
    cfg: SimulationConfig,
    e_blanket_j: float,
    acc_neut_produced_j: float,
    acc_neut_legacy_out_j: float,
    acc_leak_j: float,
    acc_coolant_j: float,
) -> None:
    ledger.blanket_dynamic = cfg.blanket.enabled
    ledger.e_blanket_j = e_blanket_j if cfg.blanket.enabled else 0.0
    ledger.e_neutron_produced_j = acc_neut_produced_j
    ledger.e_neutron_leaked_j = acc_leak_j
    ledger.e_coolant_extracted_j = acc_coolant_j
    # Legacy field: instant neutron sink OR (for reports) produced when dynamic
    ledger.e_neutron_blanket_j = (
        acc_neut_produced_j if cfg.blanket.enabled else acc_neut_legacy_out_j
    )
