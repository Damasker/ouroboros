"""Monte Carlo neutron capture estimator (Milestone 20).

Classification: simplified / pedagogical MC — not a production neutronics code.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class MCNeutronResult:
    """Estimated blanket capture fraction from slab MC."""

    capture_fraction: float
    n_particles: int
    optical_depth: float


def mc_neutron_capture_fraction(
    *,
    optical_depth: float,
    n_particles: int = 64,
    seed: int = 42,
) -> MCNeutronResult:
    """
    Isotropic slab Monte Carlo: neutrons born on one face of a blanket slab
    with optical depth τ. Absorption probability per history:
    P_abs = 1 − exp(−τ / |μ|) with μ = cos θ.

    Deterministic for fixed (τ, n, seed).
    """
    n = max(int(n_particles), 1)
    tau = max(float(optical_depth), 0.0)
    if tau <= 0.0:
        return MCNeutronResult(0.0, n, tau)

    rng = random.Random(int(seed))
    captured = 0
    for _ in range(n):
        # Isotropic μ ∈ (0,1] toward the slab
        mu = max(abs(rng.uniform(-1.0, 1.0)), 1e-3)
        p_abs = 1.0 - math.exp(-tau / mu)
        if rng.random() < p_abs:
            captured += 1
    return MCNeutronResult(capture_fraction=captured / n, n_particles=n, optical_depth=tau)
