"""Reduced-MHD-like forces with energy-channel splits (Milestone 10).

Classification: phenomenological / simplified — not a real MHD solver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


MU0 = 1.2566370614e-6


@dataclass(frozen=True)
class ReducedMHDForces:
    """Path forces and power-channel bookkeeping."""

    force_a_n: float = 0.0
    force_b_n: float = 0.0
    # Dissipative (Alfvén-like) — ledger friction when power > 0
    force_diss_a_n: float = 0.0
    force_diss_b_n: float = 0.0
    # Magnetic pressure stiffness — thermalize to plasma U when exchange on
    force_mp_a_n: float = 0.0
    force_mp_b_n: float = 0.0
    # Hydrodynamic Δp·A — exchange with plasma U
    force_pressure_a_n: float = 0.0
    force_pressure_b_n: float = 0.0

    def dissipative_power_w(self, v_a: float, v_b: float) -> float:
        """Power removed from kinetic by drag (≥0)."""
        p = -(self.force_diss_a_n * v_a + self.force_diss_b_n * v_b)
        return max(p, 0.0)

    def exchange_power_to_internal_w(self, v_a: float, v_b: float) -> float:
        """
        Power into plasma internal energy from mp + pressure channels.

        Equals −(F_mp + F_p)·v so that d/dt(E_kin + E_int) from these forces is 0.
        """
        fa = self.force_mp_a_n + self.force_pressure_a_n
        fb = self.force_mp_b_n + self.force_pressure_b_n
        return -(fa * v_a + fb * v_b)


def magnetic_pressure_force_n(
    *,
    velocity_m_s: float,
    current_a: float,
    cross_section_m2: float,
    coil_turns_per_metre: float,
    enabled: bool,
    scale: float,
) -> float:
    """
    Magnetic-pressure stiffness opposing flow: F ≈ −scale (B²/2μ₀) A tanh(v/v₀).

    Uses B ~ μ₀ n I. Classification: placeholder / phenomenological.
    """
    if not enabled or scale == 0.0:
        return 0.0
    b = MU0 * coil_turns_per_metre * abs(current_a)
    pressure = (b * b) / (2.0 * MU0)
    # Smooth sign so RHS is Lipschitz for BDF/LSODA
    v0 = 1.0  # m/s scale
    direction = -math.tanh(velocity_m_s / v0)
    return direction * scale * pressure * max(cross_section_m2, 0.0)


def alfvén_damping_force_n(
    *,
    velocity_m_s: float,
    density_m3: float,
    mean_particle_mass_kg: float,
    magnetic_field_t: float,
    enabled: bool,
    damping_fraction: float,
) -> float:
    """
    Linear drag scaled by a crude Alfvén speed.
    F = −f ρ v_A v  (A_eff absorbed into f).
    Classification: placeholder.
    """
    if not enabled or damping_fraction == 0.0:
        return 0.0
    rho = max(density_m3 * mean_particle_mass_kg, 1e-30)
    v_a = magnetic_field_t / (MU0 * rho) ** 0.5 if magnetic_field_t > 0 else 0.0
    b = damping_fraction * rho * v_a * 1.0  # [kg/s] phenomenological
    return -b * velocity_m_s


def hydrodynamic_pressure_force_n(
    *,
    p_upstream_pa: float,
    p_downstream_pa: float,
    cross_section_m2: float,
    enabled: bool,
    scale: float,
) -> float:
    """
    Lumped Δp·A drive along a path: F = scale (p_up − p_down) A.

    Classification: simplified hydro / phenomenological.
    """
    if not enabled or scale == 0.0:
        return 0.0
    return scale * (p_upstream_pa - p_downstream_pa) * max(cross_section_m2, 0.0)


def compute_reduced_mhd_forces(
    *,
    v_a: float,
    v_b: float,
    i_a: float,
    i_b: float,
    dens_a: float,
    dens_b: float,
    mean_particle_mass_kg: float,
    cross_section_m2: float,
    turns_a: float,
    turns_b: float,
    enabled: bool,
    magnetic_pressure_scale: float,
    alfven_damping_fraction: float,
    pressure_drive: bool = False,
    pressure_drive_scale: float = 1.0,
    p_a_pa: float = 0.0,
    p_b_pa: float = 0.0,
    p_c_pa: float = 0.0,
    p_r_pa: float = 0.0,
) -> ReducedMHDForces:
    if not enabled:
        return ReducedMHDForces()

    ba = MU0 * turns_a * abs(i_a)
    bb = MU0 * turns_b * abs(i_b)

    fd_a = alfvén_damping_force_n(
        velocity_m_s=v_a,
        density_m3=dens_a,
        mean_particle_mass_kg=mean_particle_mass_kg,
        magnetic_field_t=ba,
        enabled=True,
        damping_fraction=alfven_damping_fraction,
    )
    fd_b = alfvén_damping_force_n(
        velocity_m_s=v_b,
        density_m3=dens_b,
        mean_particle_mass_kg=mean_particle_mass_kg,
        magnetic_field_t=bb,
        enabled=True,
        damping_fraction=alfven_damping_fraction,
    )
    fmp_a = magnetic_pressure_force_n(
        velocity_m_s=v_a,
        current_a=i_a,
        cross_section_m2=cross_section_m2,
        coil_turns_per_metre=turns_a,
        enabled=True,
        scale=magnetic_pressure_scale,
    )
    fmp_b = magnetic_pressure_force_n(
        velocity_m_s=v_b,
        current_a=i_b,
        cross_section_m2=cross_section_m2,
        coil_turns_per_metre=turns_b,
        enabled=True,
        scale=magnetic_pressure_scale,
    )
    # Path positive direction: return → branch → chamber. Drive from (p_r − p_c).
    # Branch-local correction uses branch pressure vs chamber.
    p_up_a = 0.5 * (p_r_pa + p_a_pa)
    p_up_b = 0.5 * (p_r_pa + p_b_pa)
    fp_a = hydrodynamic_pressure_force_n(
        p_upstream_pa=p_up_a,
        p_downstream_pa=p_c_pa,
        cross_section_m2=cross_section_m2,
        enabled=pressure_drive,
        scale=pressure_drive_scale,
    )
    fp_b = hydrodynamic_pressure_force_n(
        p_upstream_pa=p_up_b,
        p_downstream_pa=p_c_pa,
        cross_section_m2=cross_section_m2,
        enabled=pressure_drive,
        scale=pressure_drive_scale,
    )
    return ReducedMHDForces(
        force_a_n=fd_a + fmp_a + fp_a,
        force_b_n=fd_b + fmp_b + fp_b,
        force_diss_a_n=fd_a,
        force_diss_b_n=fd_b,
        force_mp_a_n=fmp_a,
        force_mp_b_n=fmp_b,
        force_pressure_a_n=fp_a,
        force_pressure_b_n=fp_b,
    )
