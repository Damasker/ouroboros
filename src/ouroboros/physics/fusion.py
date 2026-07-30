"""Fusion reactivity models."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from ouroboros.units import kelvin_to_ev


class ReactivityModel(ABC):
    """Interface for <sigma v> [m^3/s] as function of ion temperature."""

    @abstractmethod
    def sigma_v(self, ion_temperature_k: float) -> float:
        raise NotImplementedError


class PlaceholderReactivityModel(ReactivityModel):
    """
    Placeholder demo model — NOT a physical reactivity fit.

    Uses a smooth bump peaking near 20 keV for qualitative Scenario tests only.
    Classification: placeholder.
    """

    def __init__(self, peak_m3_s: float = 1.0e-22, peak_kev: float = 20.0, width_kev: float = 15.0):
        self.peak_m3_s = peak_m3_s
        self.peak_kev = peak_kev
        self.width_kev = width_kev

    def sigma_v(self, ion_temperature_k: float) -> float:
        if ion_temperature_k <= 0.0:
            return 0.0
        t_kev = kelvin_to_ev(ion_temperature_k) / 1.0e3
        x = (t_kev - self.peak_kev) / self.width_kev
        return self.peak_m3_s * math.exp(-(x * x))


class BoschHaleReactivityModel(ReactivityModel):
    """
    Bosch–Hale analytic approximation for thermal D–T reactivity.

    Source: H.-S. Bosch and G.M. Hale, Nuclear Fusion 32 (1992) 611–631.
    Coefficients as tabulated for the D–T reaction (BG table).
    Validity: roughly 0.1–100 keV ion temperature (see paper). Outside range → 0 with care.

    Classification: established physics (analytic fit to evaluated cross sections).
    Returns <sigma v> in m^3/s.
    """

    # Table VIII / common Bosch-Hale DT coefficients (keV units in formula)
    C1 = 1.17302e-9
    C2 = 1.51361e-2
    C3 = 7.51886e-2
    C4 = 4.60643e-3
    C5 = 1.35000e-2
    C6 = -1.06750e-4
    C7 = 1.36600e-5
    BG = 34.3827  # keV^{1/2}
    MRC2 = 1124656.0  # reduced mass * c^2 in keV

    T_MIN_KEV = 0.1
    T_MAX_KEV = 100.0

    def sigma_v(self, ion_temperature_k: float) -> float:
        if ion_temperature_k <= 0.0:
            return 0.0
        ti_kev = kelvin_to_ev(ion_temperature_k) / 1.0e3
        if ti_kev < self.T_MIN_KEV or ti_kev > self.T_MAX_KEV:
            return 0.0
        # theta and xi as in Bosch & Hale
        c2, c3, c4, c5, c6, c7 = self.C2, self.C3, self.C4, self.C5, self.C6, self.C7
        theta = ti_kev / (
            1.0
            - (ti_kev * (c2 + ti_kev * (c4 + ti_kev * c6)))
            / (1.0 + ti_kev * (c3 + ti_kev * (c5 + ti_kev * c7)))
        )
        xi = (self.BG**2 / (4.0 * theta)) ** (1.0 / 3.0)
        # Result in cm^3/s in original paper with C1; convert to m^3/s (*1e-6)
        sv_cm3 = self.C1 * theta * math.sqrt(xi / (self.MRC2 * ti_kev**3)) * math.exp(-3.0 * xi)
        return sv_cm3 * 1.0e-6


def get_reactivity_model(name: str) -> ReactivityModel:
    if name == "bosch_hale":
        return BoschHaleReactivityModel()
    if name == "placeholder":
        return PlaceholderReactivityModel()
    raise ValueError(f"Unknown reactivity model: {name}")


def fusion_rate_per_second(
    n_d_m3: float,
    n_t_m3: float,
    volume_m3: float,
    ion_temperature_k: float,
    model: ReactivityModel,
) -> float:
    """R_f = n_D n_T <sigma v> V [reactions/s]."""
    return n_d_m3 * n_t_m3 * model.sigma_v(ion_temperature_k) * volume_m3
