"""Spacecraft trajectory post-processing from nozzle thrust (Milestone 22).

Classification: phenomenological 1D rocket equation — not orbital mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.domain.config import SpacecraftSection


@dataclass(frozen=True)
class TrajectoryPoint:
    mass_kg: float
    delta_v_m_s: float
    acceleration_m_s2: float


def integrate_trajectory_series(
    *,
    times_s: list[float],
    thrust_n: list[float],
    mass_flow_kg_s: list[float],
    spacecraft: SpacecraftSection,
) -> dict[str, list[float]]:
    """
    Discrete rocket integration: ṁ = −ṁ_noz, Δv̇ = T/m.

    Propellant limited by wet−dry mass. Returns series keys for SimulationResult.
    """
    n = len(times_s)
    if not spacecraft.enabled or n == 0:
        return {
            "spacecraft_mass_kg": [float("nan")] * n,
            "delta_v_m_s": [float("nan")] * n,
            "acceleration_m_s2": [float("nan")] * n,
        }

    m = max(spacecraft.wet_mass_kg, spacecraft.dry_mass_kg, 1e-12)
    dry = max(spacecraft.dry_mass_kg, 1e-12)
    dv = 0.0
    masses: list[float] = []
    dvs: list[float] = []
    accs: list[float] = []

    for i in range(n):
        t = thrust_n[i] if i < len(thrust_n) else 0.0
        mdot = mass_flow_kg_s[i] if i < len(mass_flow_kg_s) else 0.0
        if not (t == t):  # NaN
            t = 0.0
        if not (mdot == mdot):
            mdot = 0.0
        m_eff = max(m, dry)
        a = t / m_eff if spacecraft.include_thrust_accel else 0.0
        masses.append(m_eff)
        dvs.append(dv)
        accs.append(a)
        if i + 1 < n:
            dt = max(times_s[i + 1] - times_s[i], 0.0)
            if dt > 0.0:
                dv += a * dt
                # Consume propellant only while above dry mass
                dm = min(max(mdot, 0.0) * dt, max(m_eff - dry, 0.0))
                m = m_eff - dm

    return {
        "spacecraft_mass_kg": masses,
        "delta_v_m_s": dvs,
        "acceleration_m_s2": accs,
    }
