"""Physics package exports."""

from ouroboros.physics.fusion import (
    BoschHaleReactivityModel,
    PlaceholderReactivityModel,
    ReactivityModel,
    fusion_rate_per_second,
    get_reactivity_model,
)
from ouroboros.physics.losses import LossPowers, compute_zone_losses, magnetic_ohmic_power_w
from ouroboros.physics.throttle import plasma_proxy_current_a, throttle_rhs

__all__ = [
    "BoschHaleReactivityModel",
    "LossPowers",
    "PlaceholderReactivityModel",
    "ReactivityModel",
    "compute_zone_losses",
    "fusion_rate_per_second",
    "get_reactivity_model",
    "magnetic_ohmic_power_w",
    "plasma_proxy_current_a",
    "throttle_rhs",
]
