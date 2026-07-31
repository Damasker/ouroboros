"""Reduced-MHD-like stubs (phenomenological / placeholder)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReducedMHDForces:
    """Extra forces on path velocities. Not a real MHD solver."""

    force_a_n: float = 0.0
    force_b_n: float = 0.0


def magnetic_pressure_force_n(
    *,
    current_a: float,
    cross_section_m2: float,
    coil_turns_per_metre: float,
    enabled: bool,
    scale: float,
) -> float:
    """
    Placeholder: F ~ -scale * (B^2/2mu0) * A * sign(I) proxy using B~mu0 n I.

    Classification: placeholder / speculative — not Grad–Shafranov or MHD equilibrium.
    """
    if not enabled or scale == 0.0:
        return 0.0
    mu0 = 1.2566370614e-6
    b = mu0 * coil_turns_per_metre * abs(current_a)
    pressure = (b * b) / (2.0 * mu0)
    # Oppose current sign as a crude "magnetic stiffness" on flow
    direction = -1.0 if current_a >= 0.0 else 1.0
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
    Placeholder linear drag scaled by a crude Alfvén speed.
    F = -f * rho * A_eff * v_A * v  with A_eff absorbed into phenomenological f.
    Classification: placeholder.
    """
    if not enabled or damping_fraction == 0.0:
        return 0.0
    mu0 = 1.2566370614e-6
    rho = max(density_m3 * mean_particle_mass_kg, 1e-30)
    v_a = magnetic_field_t / (mu0 * rho) ** 0.5 if magnetic_field_t > 0 else 0.0
    # Drag coefficient [kg/s] ~ damping_fraction * rho * v_A * 1 m^2
    b = damping_fraction * rho * v_a * 1.0
    return -b * velocity_m_s


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
) -> ReducedMHDForces:
    mu0 = 1.2566370614e-6
    ba = mu0 * turns_a * abs(i_a)
    bb = mu0 * turns_b * abs(i_b)
    fa = magnetic_pressure_force_n(
        current_a=i_a,
        cross_section_m2=cross_section_m2,
        coil_turns_per_metre=turns_a,
        enabled=enabled,
        scale=magnetic_pressure_scale,
    ) + alfvén_damping_force_n(
        velocity_m_s=v_a,
        density_m3=dens_a,
        mean_particle_mass_kg=mean_particle_mass_kg,
        magnetic_field_t=ba,
        enabled=enabled,
        damping_fraction=alfven_damping_fraction,
    )
    fb = magnetic_pressure_force_n(
        current_a=i_b,
        cross_section_m2=cross_section_m2,
        coil_turns_per_metre=turns_b,
        enabled=enabled,
        scale=magnetic_pressure_scale,
    ) + alfvén_damping_force_n(
        velocity_m_s=v_b,
        density_m3=dens_b,
        mean_particle_mass_kg=mean_particle_mass_kg,
        magnetic_field_t=bb,
        enabled=enabled,
        damping_fraction=alfven_damping_fraction,
    )
    return ReducedMHDForces(force_a_n=fa, force_b_n=fb)
