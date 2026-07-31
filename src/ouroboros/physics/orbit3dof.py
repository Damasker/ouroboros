"""Planar 3DOF orbital mechanics with thrust (Milestone 26).

State in inertial XY: position, velocity. Central gravity μ/r².
Thrust along instantaneous velocity (or +x if |v|~0).

Classification: pedagogical 3DOF — not 6DOF attitude / full ephemeris.
"""

from __future__ import annotations

import math

from ouroboros.domain.config import SpacecraftSection


def integrate_orbit3dof_series(
    *,
    times_s: list[float],
    thrust_n: list[float],
    mass_flow_kg_s: list[float],
    spacecraft: SpacecraftSection,
) -> dict[str, list[float]]:
    """
    Integrate planar orbit + rocket mass. Returns position/velocity/Δv series.
    """
    n = len(times_s)
    nan = float("nan")
    empty = {
        "spacecraft_mass_kg": [nan] * n,
        "delta_v_m_s": [nan] * n,
        "acceleration_m_s2": [nan] * n,
        "orbit_x_m": [nan] * n,
        "orbit_y_m": [nan] * n,
        "orbit_vx_m_s": [nan] * n,
        "orbit_vy_m_s": [nan] * n,
        "orbit_radius_m": [nan] * n,
    }
    if not spacecraft.enabled or n == 0:
        return empty

    m = max(spacecraft.wet_mass_kg, spacecraft.dry_mass_kg, 1e-12)
    dry = max(spacecraft.dry_mass_kg, 1e-12)
    mu = max(spacecraft.gravity_mu_m3_s2, 0.0)
    x = float(spacecraft.initial_x_m)
    y = float(spacecraft.initial_y_m)
    vx = float(spacecraft.initial_vx_m_s)
    vy = float(spacecraft.initial_vy_m_s)
    dv = 0.0

    masses: list[float] = []
    dvs: list[float] = []
    accs: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    vxs: list[float] = []
    vys: list[float] = []
    rs: list[float] = []

    for i in range(n):
        t = thrust_n[i] if i < len(thrust_n) else 0.0
        mdot = mass_flow_kg_s[i] if i < len(mass_flow_kg_s) else 0.0
        if not (t == t):
            t = 0.0
        if not (mdot == mdot):
            mdot = 0.0
        m_eff = max(m, dry)
        r = math.hypot(x, y)
        # Gravity
        if r > 1.0 and mu > 0.0:
            ax_g = -mu * x / (r**3)
            ay_g = -mu * y / (r**3)
        else:
            ax_g = ay_g = 0.0
        # Thrust along velocity
        speed = math.hypot(vx, vy)
        if spacecraft.include_thrust_accel and speed > 1e-12:
            ax_t = (t / m_eff) * (vx / speed)
            ay_t = (t / m_eff) * (vy / speed)
            a_thrust = t / m_eff
        elif spacecraft.include_thrust_accel and t > 0.0:
            ax_t, ay_t, a_thrust = t / m_eff, 0.0, t / m_eff
        else:
            ax_t = ay_t = a_thrust = 0.0

        masses.append(m_eff)
        dvs.append(dv)
        accs.append(a_thrust)
        xs.append(x)
        ys.append(y)
        vxs.append(vx)
        vys.append(vy)
        rs.append(r)

        if i + 1 < n:
            dt = max(times_s[i + 1] - times_s[i], 0.0)
            if dt > 0.0:
                ax = ax_g + ax_t
                ay = ay_g + ay_t
                vx += ax * dt
                vy += ay * dt
                x += vx * dt
                y += vy * dt
                dv += a_thrust * dt
                dm = min(max(mdot, 0.0) * dt, max(m_eff - dry, 0.0))
                m = m_eff - dm

    return {
        "spacecraft_mass_kg": masses,
        "delta_v_m_s": dvs,
        "acceleration_m_s2": accs,
        "orbit_x_m": xs,
        "orbit_y_m": ys,
        "orbit_vx_m_s": vxs,
        "orbit_vy_m_s": vys,
        "orbit_radius_m": rs,
    }
