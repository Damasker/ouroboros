"""Exceptions for non-physical or untrusted simulation states."""

from __future__ import annotations


class OuroborosError(Exception):
    """Base error."""


class NonPhysicalStateError(OuroborosError):
    """Raised when density/temperature/particle number become negative or invalid."""


class EnergyBalanceError(OuroborosError):
    """Raised in strict mode when energy residual exceeds tolerance."""


class SimulationAbortError(OuroborosError):
    """Raised on fault trips or operator stop."""
