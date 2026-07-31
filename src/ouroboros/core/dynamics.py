"""Shared helpers for ODE systems."""

from __future__ import annotations

from typing import Any

from ouroboros.domain.config import SimulationConfig
from ouroboros.physics.coupling import PathThrottleDerivatives, path_throttle_rhs
from ouroboros.physics.reduced_mhd import compute_reduced_mhd_forces


def loss_kwargs(cfg: SimulationConfig) -> dict[str, Any]:
    return {
        "anisotropic_transport": cfg.losses.anisotropic_transport,
        "tau_parallel_s": cfg.losses.tau_parallel_s,
        "tau_perp_s": cfg.losses.tau_perp_s,
    }


def dual_path_throttle_step(
    *,
    cfg: SimulationConfig,
    v_a: float,
    v_b: float,
    i_a: float,
    i_b: float,
    dens_a: float,
    dens_b: float,
    resistance_a: float,
    resistance_b: float,
) -> tuple[PathThrottleDerivatives, PathThrottleDerivatives, float]:
    """
    Compute momentum/throttle derivatives for paths A/B including optional reduced-MHD stubs.

    Returns (deriv_a, deriv_b, extra_dissipation_w) where extra_dissipation is Alfvén-like
    damping power accumulated into the friction ledger channel.
    """
    mhd = compute_reduced_mhd_forces(
        v_a=v_a,
        v_b=v_b,
        i_a=i_a,
        i_b=i_b,
        dens_a=dens_a,
        dens_b=dens_b,
        mean_particle_mass_kg=cfg.plasma.mean_particle_mass_kg,
        cross_section_m2=cfg.geometry.branch_cross_section_m2,
        turns_a=cfg.throttle_a.coil_turns_per_metre,
        turns_b=cfg.throttle_b.coil_turns_per_metre,
        enabled=cfg.reduced_mhd.enabled,
        magnetic_pressure_scale=cfg.reduced_mhd.magnetic_pressure_scale,
        alfven_damping_fraction=cfg.reduced_mhd.alfven_damping_fraction,
    )
    f_other_a = cfg.drive.drive_force_a_n - cfg.plasma.friction_coeff_kg_s * v_a + mhd.force_a_n
    f_other_b = cfg.drive.drive_force_b_n - cfg.plasma.friction_coeff_kg_s * v_b + mhd.force_b_n
    da = path_throttle_rhs(
        velocity_m_s=v_a,
        current_a=i_a,
        force_nonmagnetic_n=f_other_a,
        effective_inertia_kg=cfg.plasma.effective_inertia_kg,
        inductance_h=cfg.throttle_a.inductance_h,
        resistance_ohm=resistance_a,
        coupling_mode=cfg.throttle_a.coupling_mode,
        emf_coeff_v_s_per_m=cfg.throttle_a.emf_coeff_v_s_per_m,
        coupling_force_coeff_n_per_a=cfg.throttle_a.coupling_force_coeff_n_per_a,
        mutual_inductance_h=cfg.throttle_a.mutual_inductance_h,
    )
    db = path_throttle_rhs(
        velocity_m_s=v_b,
        current_a=i_b,
        force_nonmagnetic_n=f_other_b,
        effective_inertia_kg=cfg.plasma.effective_inertia_kg,
        inductance_h=cfg.throttle_b.inductance_h,
        resistance_ohm=resistance_b,
        coupling_mode=cfg.throttle_b.coupling_mode,
        emf_coeff_v_s_per_m=cfg.throttle_b.emf_coeff_v_s_per_m,
        coupling_force_coeff_n_per_a=cfg.throttle_b.coupling_force_coeff_n_per_a,
        mutual_inductance_h=cfg.throttle_b.mutual_inductance_h,
    )
    # Alfvén drag power ≈ -F_drag·v when F_drag is the damping part; approximate via
    # total MHD force when pressure scale is 0 (default).
    p_mhd = -(mhd.force_a_n * v_a + mhd.force_b_n * v_b)
    # Only count dissipative (positive) contribution
    p_mhd = max(p_mhd, 0.0)
    return da, db, p_mhd
