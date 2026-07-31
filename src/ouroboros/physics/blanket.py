"""Neutron blanket channel (simplified / phenomenological)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlanketPowers:
    """Instantaneous blanket power channels [W]."""

    neutron_in_w: float = 0.0  # full neutron fusion power
    captured_w: float = 0.0  # deposited in blanket thermal bin
    leaked_w: float = 0.0  # immediate loss
    coolant_extract_w: float = 0.0  # removed from blanket
    breeding_rate_s: float = 0.0  # placeholder T atoms/s


@dataclass
class BlanketState:
    """Lumped blanket thermal energy [J] and optional tritium inventory [atoms]."""

    thermal_energy_j: float = 0.0
    tritium_inventory: float = 0.0


def blanket_rhs(
    *,
    neutron_power_w: float,
    thermal_energy_j: float,
    capture_fraction: float,
    coolant_time_s: float,
    breeding_ratio: float,
    enabled: bool,
) -> tuple[float, float, BlanketPowers]:
    """
    Returns (dE_b/dt, dN_T/dt, powers).

    Classification: phenomenological / simplified.
    Not a transport or activation calculation.
    """
    if not enabled:
        # Legacy: all neutron power treated as immediate blanket "output" elsewhere.
        return 0.0, 0.0, BlanketPowers(neutron_in_w=neutron_power_w)

    cap = min(max(capture_fraction, 0.0), 1.0)
    captured = cap * max(neutron_power_w, 0.0)
    leaked = max(neutron_power_w, 0.0) - captured
    tau = max(coolant_time_s, 1e-12)
    extract = max(thermal_energy_j, 0.0) / tau
    # TBR stub: breeding_ratio * neutron reaction rate proxy via E_n / 14.1 MeV
    from ouroboros.units import DT_NEUTRON_J

    n_rate = max(neutron_power_w, 0.0) / max(DT_NEUTRON_J, 1e-30)
    breed = max(breeding_ratio, 0.0) * n_rate * cap
    dE = captured - extract
    return dE, breed, BlanketPowers(
        neutron_in_w=neutron_power_w,
        captured_w=captured,
        leaked_w=leaked,
        coolant_extract_w=extract,
        breeding_rate_s=breed,
    )
