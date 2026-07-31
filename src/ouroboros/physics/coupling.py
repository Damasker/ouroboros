"""Electromechanical throttle–flow coupling models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CouplingMode = Literal["none", "phenomenological", "consistent"]


@dataclass(frozen=True)
class PathThrottleDerivatives:
    """RHS pieces for one flow path + its throttle."""

    dv_dt: float
    dI_dt: float
    f_magnetic_n: float
    ohmic_power_w: float
    coupling_power_mech_w: float  # F_mag * v
    coupling_power_elec_w: float  # I * back_emf


def path_throttle_rhs(
    *,
    velocity_m_s: float,
    current_a: float,
    force_nonmagnetic_n: float,
    effective_inertia_kg: float,
    inductance_h: float,
    resistance_ohm: float,
    coupling_mode: CouplingMode,
    # consistent: k_em [N/A] = [V/(m/s)]
    emf_coeff_v_s_per_m: float = 0.0,
    # phenomenological (legacy): independent force coeff and mutual inductance
    coupling_force_coeff_n_per_a: float = 0.0,
    mutual_inductance_h: float = 0.0,
    plasma_current_scale_a_s_per_m: float = 1.0e2,
) -> PathThrottleDerivatives:
    """
    Compute dv/dt and dI/dt for one path.

    consistent:
        F_mag = -k I
        L I' + R I = k v
        => d/dt(E_kin+E_mag) = F_other·v - I^2 R  (coupling powers cancel).

    phenomenological:
        F_mag = -k_f I
        L I' + R I = -M * α * dv/dt
        (may leave energy residual; documented).

    none:
        F_mag = 0, mutual terms off (only ohmic RL on I).
    """
    L = max(inductance_h, 1e-12)
    M_eff = max(effective_inertia_kg, 1e-30)
    v = velocity_m_s
    I = current_a
    R = max(resistance_ohm, 0.0)

    if coupling_mode == "none":
        f_mag = 0.0
        dv = (force_nonmagnetic_n + f_mag) / M_eff
        dI = (-R * I) / L
        back_emf = 0.0
    elif coupling_mode == "consistent":
        # Motor/generator convention:
        #   F_mag = -k I
        #   L I' + R I = k v
        # => F_mag*v + electrical intake I*(k v - something wait): energies cancel except ohmic.
        k = emf_coeff_v_s_per_m
        f_mag = -k * I
        dv = (force_nonmagnetic_n + f_mag) / M_eff
        back_emf = k * v  # generated EMF; circuit: L I' + R I = back_emf
        dI = (back_emf - R * I) / L
    else:  # phenomenological
        f_mag = -coupling_force_coeff_n_per_a * I
        dv = (force_nonmagnetic_n + f_mag) / M_eff
        dIp = plasma_current_scale_a_s_per_m * dv
        dI = (-R * I - mutual_inductance_h * dIp) / L
        back_emf = mutual_inductance_h * dIp  # not equal to -F*v/I in general

    ohmic = I * I * R
    return PathThrottleDerivatives(
        dv_dt=dv,
        dI_dt=dI,
        f_magnetic_n=f_mag,
        ohmic_power_w=ohmic,
        coupling_power_mech_w=f_mag * v,
        coupling_power_elec_w=I * back_emf,
    )


def coupling_power_residual_w(deriv: PathThrottleDerivatives) -> float:
    """Should be ~0 for consistent mode: F_mag*v + I*(k v) = 0 when F_mag=-k I."""
    return deriv.coupling_power_mech_w + deriv.coupling_power_elec_w
