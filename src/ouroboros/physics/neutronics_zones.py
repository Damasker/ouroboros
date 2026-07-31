"""Multi-zone / CAD-proxy blanket neutronics (Milestone 24).

Classification: simplified ray-march MC through layered optical depths —
not OpenMC/MCNP or CAD-imported geometry.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class BlanketLayer:
    """One blanket layer with optical depth and capture weight."""

    name: str
    optical_depth: float
    capture_weight: float = 1.0  # relative absorption preference


@dataclass(frozen=True)
class ZoneNeutronicsResult:
    capture_fraction: float
    layer_deposits: dict[str, float]  # fraction of source captured in layer
    n_particles: int


def zone_mc_capture(
    layers: list[BlanketLayer],
    *,
    n_particles: int = 128,
    seed: int = 42,
) -> ZoneNeutronicsResult:
    """
    Isotropic rays through a stack of layers. Each layer attenuates with
    τ_i / |μ|; absorption attributed to the layer that stops the neutron.
    """
    n = max(int(n_particles), 1)
    if not layers:
        return ZoneNeutronicsResult(0.0, {}, n)

    rng = random.Random(int(seed))
    deposits = {L.name: 0.0 for L in layers}
    captured = 0
    for _ in range(n):
        mu = max(abs(rng.uniform(-1.0, 1.0)), 1e-3)
        # Remaining optical path budget
        path = -math.log(max(rng.random(), 1e-15)) * mu  # free-flight optical units
        # Walk layers until optical budget exhausted
        remaining = path
        absorbed = False
        for layer in layers:
            tau = max(layer.optical_depth, 0.0) * max(layer.capture_weight, 0.0)
            if remaining <= tau:
                deposits[layer.name] += 1.0
                captured += 1
                absorbed = True
                break
            remaining -= tau
        if not absorbed:
            # leaked
            pass

    for k in deposits:
        deposits[k] /= n
    return ZoneNeutronicsResult(
        capture_fraction=captured / n,
        layer_deposits=deposits,
        n_particles=n,
    )


def default_cad_proxy_layers() -> list[BlanketLayer]:
    """Default Li/steel/water stack used when blanket.layers is empty."""
    return [
        BlanketLayer("first_wall", 0.3, 0.4),
        BlanketLayer("breeder", 1.5, 1.0),
        BlanketLayer("shield", 0.8, 0.7),
    ]
