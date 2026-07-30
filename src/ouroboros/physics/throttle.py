"""Passive magnetic throttle model (phenomenological)."""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.domain import MagneticThrottle, ThrottleStatus


@dataclass
class ThrottleDerivatives:
    dI_dt: float
    magnetic_force_n: float
    ohmic_power_w: float
    status: ThrottleStatus


def plasma_proxy_current_a(mass_flow_kg_s: float, scale_a_s_per_kg: float = 1.0e4) -> float:
    """
    Map mass flow to a proxy 'plasma current' for mutual inductance.
    Classification: phenomenological / placeholder.
    """
    return mass_flow_kg_s * scale_a_s_per_kg


def throttle_rhs(
    throttle: MagneticThrottle,
    plasma_current_a: float,
    d_plasma_current_dt: float,
    force_quench: bool = False,
) -> ThrottleDerivatives:
    """
    L dI_s/dt + R I_s = -M dI_p/dt

    => dI_s/dt = (-R I_s - M dI_p/dt) / L
    """
    status = throttle.status
    resistance = throttle.resistance_ohm
    if force_quench or status == ThrottleStatus.QUENCH:
        resistance = max(resistance, throttle.quench_resistance_ohm)
        status = ThrottleStatus.QUENCH

    L = max(throttle.inductance_h, 1e-12)
    dI_dt = (
        -resistance * throttle.current_a - throttle.mutual_inductance_h * d_plasma_current_dt
    ) / L

    # Current / field limits — mark limiting; quench if far beyond
    projected = abs(throttle.current_a)
    field = throttle.estimated_field_t()
    if projected > throttle.current_limit_a or field > throttle.field_limit_t:
        status = ThrottleStatus.LIMITING
    if projected > 1.2 * throttle.current_limit_a or field > 1.2 * throttle.field_limit_t:
        status = ThrottleStatus.QUENCH
        resistance = throttle.quench_resistance_ohm
        dI_dt = (
            -resistance * throttle.current_a - throttle.mutual_inductance_h * d_plasma_current_dt
        ) / L

    ohmic = (throttle.current_a**2) * resistance
    # Magnetic force opposing rapid flow changes (phenomenological)
    # Use coupling to current; sign opposes plasma proxy current growth conceptually via -k*I_s
    force = -throttle.current_a  # scaled outside by coupling_force_coeff
    return ThrottleDerivatives(
        dI_dt=dI_dt, magnetic_force_n=force, ohmic_power_w=ohmic, status=status
    )
