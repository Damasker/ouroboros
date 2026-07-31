"""Magnetic nozzle / directed exhaust channel (Milestone 13).

Classification: phenomenological / speculative — not a validated thruster model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

G0 = 9.80665  # m/s²


@dataclass(frozen=True)
class NozzlePowers:
    """Instantaneous nozzle extraction and thrust metrics."""

    particle_rate_s: float = 0.0  # particles/s leaving plasma
    thermal_extract_w: float = 0.0  # internal energy removed [W]
    jet_power_w: float = 0.0  # directed kinetic (useful)
    waste_power_w: float = 0.0  # not converted to jet
    thrust_n: float = 0.0
    isp_s: float = 0.0
    mass_flow_kg_s: float = 0.0
    exhaust_velocity_m_s: float = 0.0


def magnetic_nozzle_powers(
    *,
    n_particles: float,
    internal_energy_j: float,
    mean_particle_mass_kg: float,
    extract_time_s: float,
    extract_fraction: float,
    magnetic_efficiency: float,
    enabled: bool,
) -> NozzlePowers:
    """
    Extract a fraction of zone inventory per extract_time; convert η of removed
    enthalpy to jet power. Exhaust speed from P_jet = ½ ṁ v².

    Energy identity: thermal_extract = jet + waste.
    """
    if not enabled or n_particles <= 1e-12 or internal_energy_j <= 0.0:
        return NozzlePowers()

    tau = max(extract_time_s, 1e-12)
    frac = min(max(extract_fraction, 0.0), 1.0)
    eta = min(max(magnetic_efficiency, 0.0), 1.0)

    n_dot = frac * n_particles / tau
    # Carry specific internal energy with extracted particles
    u_spec = internal_energy_j / n_particles
    p_th = u_spec * n_dot
    p_jet = eta * p_th
    p_waste = p_th - p_jet

    mdot = max(mean_particle_mass_kg, 0.0) * n_dot
    if mdot > 1e-45 and p_jet > 0.0:
        v_ex = math.sqrt(2.0 * p_jet / mdot)
        thrust = mdot * v_ex
        isp = v_ex / G0
    else:
        v_ex = thrust = isp = 0.0

    return NozzlePowers(
        particle_rate_s=n_dot,
        thermal_extract_w=p_th,
        jet_power_w=p_jet,
        waste_power_w=p_waste,
        thrust_n=thrust,
        isp_s=isp,
        mass_flow_kg_s=mdot,
        exhaust_velocity_m_s=v_ex,
    )
