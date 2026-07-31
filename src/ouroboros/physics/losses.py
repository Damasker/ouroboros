"""Modular loss models. Each can be disabled via configuration."""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.units import BOLTZMANN_J_PER_K, ELEMENTARY_CHARGE_C


@dataclass(frozen=True)
class LossPowers:
    bremsstrahlung_w: float = 0.0
    transport_w: float = 0.0
    transport_parallel_w: float = 0.0
    transport_perp_w: float = 0.0
    wall_w: float = 0.0
    exhaust_w: float = 0.0
    magnetic_w: float = 0.0

    @property
    def total_w(self) -> float:
        return (
            self.bremsstrahlung_w
            + self.transport_w
            + self.wall_w
            + self.exhaust_w
            + self.magnetic_w
        )


def bremsstrahlung_power_w(
    n_e_m3: float,
    t_e_k: float,
    volume_m3: float,
    z_eff: float = 1.0,
) -> float:
    """
    Simplified hydrogenic bremsstrahlung estimate.

    P_brem ≈ 1.69e-38 * n_e^2 * sqrt(T_e[eV]) * Z_eff * V
    with n in m^-3, V in m^3, result in watts.
    Coefficient is a standard order-of-magnitude plasma formula (simplified physics).
    """
    if n_e_m3 <= 0.0 or t_e_k <= 0.0 or volume_m3 <= 0.0:
        return 0.0
    t_ev = t_e_k * BOLTZMANN_J_PER_K / ELEMENTARY_CHARGE_C
    return 1.69e-38 * (n_e_m3**2) * (t_ev**0.5) * z_eff * volume_m3


def transport_power_w(internal_energy_j: float, tau_e_s: float, confinement_factor: float) -> float:
    """Phenomenological: P_transport = U / (tau_E * kappa)."""
    tau = max(tau_e_s * max(confinement_factor, 1e-12), 1e-12)
    return max(internal_energy_j, 0.0) / tau


def anisotropic_transport_powers_w(
    internal_energy_j: float,
    tau_parallel_s: float,
    tau_perp_s: float,
    confinement_factor: float,
) -> tuple[float, float]:
    """
    Split phenomenological transport into parallel / perpendicular channels.

    Classification: phenomenological stub (not Braginskii).
    Returns (P_parallel, P_perp).
    """
    kappa = max(confinement_factor, 1e-12)
    u = max(internal_energy_j, 0.0)
    p_par = u / max(tau_parallel_s * kappa, 1e-12)
    p_perp = u / max(tau_perp_s * kappa, 1e-12)
    return p_par, p_perp


def wall_power_w(internal_energy_j: float, wall_loss_coeff_s: float) -> float:
    """Phenomenological wall sink P = coeff * U."""
    return max(internal_energy_j, 0.0) * max(wall_loss_coeff_s, 0.0)


def exhaust_power_w(internal_energy_j: float, exhaust_loss_coeff_s: float) -> float:
    """Phenomenological exhaust channel before recovery."""
    return max(internal_energy_j, 0.0) * max(exhaust_loss_coeff_s, 0.0)


def magnetic_ohmic_power_w(current_a: float, resistance_ohm: float) -> float:
    """I^2 R loss in throttle circuit."""
    try:
        return float(current_a) ** 2 * max(resistance_ohm, 0.0)
    except OverflowError:
        return float("inf")


def compute_zone_losses(
    *,
    n_e_m3: float,
    t_e_k: float,
    volume_m3: float,
    internal_energy_j: float,
    tau_e_s: float,
    confinement_factor: float,
    enabled_bremsstrahlung: bool,
    enabled_transport: bool,
    enabled_wall: bool,
    enabled_exhaust: bool,
    wall_loss_coeff_s: float,
    exhaust_loss_coeff_s: float,
    z_eff: float,
    anisotropic_transport: bool = False,
    tau_parallel_s: float = 0.05,
    tau_perp_s: float = 0.5,
) -> LossPowers:
    p_par = p_perp = 0.0
    p_trans = 0.0
    if enabled_transport:
        if anisotropic_transport:
            p_par, p_perp = anisotropic_transport_powers_w(
                internal_energy_j, tau_parallel_s, tau_perp_s, confinement_factor
            )
            p_trans = p_par + p_perp
        else:
            p_trans = transport_power_w(internal_energy_j, tau_e_s, confinement_factor)
    return LossPowers(
        bremsstrahlung_w=bremsstrahlung_power_w(n_e_m3, t_e_k, volume_m3, z_eff)
        if enabled_bremsstrahlung
        else 0.0,
        transport_w=p_trans,
        transport_parallel_w=p_par,
        transport_perp_w=p_perp,
        wall_w=wall_power_w(internal_energy_j, wall_loss_coeff_s) if enabled_wall else 0.0,
        exhaust_w=exhaust_power_w(internal_energy_j, exhaust_loss_coeff_s)
        if enabled_exhaust
        else 0.0,
        magnetic_w=0.0,
    )
