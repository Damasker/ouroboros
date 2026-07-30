"""SI unit conversions. Internal calculations use SI; eV/keV/MeV only via explicit helpers."""

from __future__ import annotations

# Elementary constants (CODATA-aligned values used as fixed project constants)
ELEMENTARY_CHARGE_C: float = 1.602176634e-19
BOLTZMANN_J_PER_K: float = 1.380649e-23
EV_TO_J: float = ELEMENTARY_CHARGE_C
J_TO_EV: float = 1.0 / ELEMENTARY_CHARGE_C
KEV_TO_J: float = 1.0e3 * EV_TO_J
MEV_TO_J: float = 1.0e6 * EV_TO_J
AMU_KG: float = 1.66053906660e-27
PROTON_MASS_KG: float = 1.67262192369e-27
DEUTERIUM_MASS_KG: float = 2.01410177811 * AMU_KG
TRITIUM_MASS_KG: float = 3.01604928199 * AMU_KG
HELIUM4_MASS_KG: float = 4.00260325413 * AMU_KG

# D–T fusion energy partition (established nuclear data)
DT_FUSION_TOTAL_MEV: float = 17.6
DT_ALPHA_MEV: float = 3.5
DT_NEUTRON_MEV: float = 14.1
DT_FUSION_TOTAL_J: float = DT_FUSION_TOTAL_MEV * MEV_TO_J
DT_ALPHA_J: float = DT_ALPHA_MEV * MEV_TO_J
DT_NEUTRON_J: float = DT_NEUTRON_MEV * MEV_TO_J


def ev_to_kelvin(temperature_ev: float) -> float:
    """Convert electron-volts to kelvin: T[K] = T[eV] * e / k_B."""
    return temperature_ev * EV_TO_J / BOLTZMANN_J_PER_K


def kelvin_to_ev(temperature_k: float) -> float:
    """Convert kelvin to electron-volts."""
    return temperature_k * BOLTZMANN_J_PER_K / EV_TO_J


def ev_to_joule(energy_ev: float) -> float:
    return energy_ev * EV_TO_J


def joule_to_ev(energy_j: float) -> float:
    return energy_j * J_TO_EV


def mev_to_joule(energy_mev: float) -> float:
    return energy_mev * MEV_TO_J


def thermal_energy_joule(
    n_ions_m3: float,
    t_ion_k: float,
    n_electrons_m3: float,
    t_electron_k: float,
    volume_m3: float,
) -> float:
    """Internal thermal energy U = 3/2 (n_i k T_i + n_e k T_e) V [J]."""
    return (
        1.5 * BOLTZMANN_J_PER_K * (n_ions_m3 * t_ion_k + n_electrons_m3 * t_electron_k) * volume_m3
    )


def pressure_pa(
    n_ions_m3: float, t_ion_k: float, n_electrons_m3: float, t_electron_k: float
) -> float:
    """Ideal-gas plasma pressure p = n_i k T_i + n_e k T_e [Pa]."""
    return BOLTZMANN_J_PER_K * (n_ions_m3 * t_ion_k + n_electrons_m3 * t_electron_k)
