"""Map NozzleSection (+ optional T) into magnetic_nozzle_powers kwargs."""

from __future__ import annotations

from typing import Any

from ouroboros.domain.config import NozzleSection


def nozzle_kwargs(
    nozzle: NozzleSection,
    *,
    n_particles: float,
    internal_energy_j: float,
    mean_particle_mass_kg: float,
    enabled: bool,
    ion_temperature_k: float = 0.0,
) -> dict[str, Any]:
    return {
        "n_particles": n_particles,
        "internal_energy_j": internal_energy_j,
        "mean_particle_mass_kg": mean_particle_mass_kg,
        "extract_time_s": nozzle.extract_time_s,
        "extract_fraction": nozzle.extract_fraction,
        "magnetic_efficiency": nozzle.magnetic_efficiency,
        "enabled": enabled,
        "expansion_ratio": nozzle.expansion_ratio,
        "gamma": nozzle.gamma,
        "thermal_velocity_blend": nozzle.thermal_velocity_blend,
        "ion_temperature_k": ion_temperature_k,
    }
