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
    expansion_ratio: float = 1.0,
    gamma: float = 5.0 / 3.0,
    thermal_velocity_blend: float = 0.0,
    ion_temperature_k: float = 0.0,
) -> NozzlePowers:
    """
    Extract a fraction of zone inventory per extract_time; convert η of removed
    enthalpy to jet power. Exhaust speed from P_jet = ½ ṁ v².

    Optional Milestone 22 blend with ideal isentropic expansion velocity
    v_id ≈ √[2γ/(γ−1) · (kT/m) · (1 − ε^{−(γ−1)})] (ε = expansion_ratio).

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
        v_mag = math.sqrt(2.0 * p_jet / mdot)
    else:
        v_mag = 0.0

    blend = min(max(thermal_velocity_blend, 0.0), 1.0)
    v_ex = v_mag
    if blend > 0.0 and ion_temperature_k > 0.0 and mean_particle_mass_kg > 0.0:
        from ouroboros.units import BOLTZMANN_J_PER_K

        g = max(gamma, 1.0001)
        eps = max(expansion_ratio, 1.0)
        # Simplified pressure-ratio proxy from area ratio
        pe_pc = eps ** (-g)
        bracket = max(1.0 - pe_pc ** ((g - 1.0) / g), 0.0)
        v_id = math.sqrt(
            (2.0 * g / (g - 1.0))
            * (BOLTZMANN_J_PER_K * ion_temperature_k / mean_particle_mass_kg)
            * bracket
        )
        v_ex = (1.0 - blend) * v_mag + blend * eta * v_id
        # Reconcile jet power with blended exhaust speed
        p_jet = 0.5 * mdot * v_ex * v_ex
        if p_jet > p_th:
            p_jet = p_th
            v_ex = math.sqrt(2.0 * p_jet / mdot) if mdot > 1e-45 else 0.0
        p_waste = p_th - p_jet

    if mdot > 1e-45 and v_ex > 0.0:
        thrust = mdot * v_ex
        isp = v_ex / G0
    else:
        thrust = isp = 0.0
        v_ex = 0.0

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
