"""ODE integrator wrapper around SciPy solve_ivp."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

import numpy as np
from scipy.integrate import solve_ivp

from ouroboros.core.exceptions import (
    EnergyBalanceError,
    NonPhysicalStateError,
    SimulationAbortError,
)
from ouroboros.core.multizone import MultiZoneSystem
from ouroboros.core.oned import OneDSystem
from ouroboros.core.system import SERIES_KEYS, LoopSystem
from ouroboros.domain import EnergyLedger, EventSeverity, SimulationEvent, SimulationResult
from ouroboros.domain.config import SimulationConfig

logger = logging.getLogger(__name__)


class SupportsSimulation(Protocol):
    events: list[SimulationEvent]
    _energy_trusted: bool

    def initial_state(self) -> np.ndarray: ...
    def rhs(self, t: float, y: np.ndarray) -> np.ndarray: ...
    def sample_series(self, t: float, y: np.ndarray) -> dict[str, float]: ...
    def ledger_from_state(self, y: np.ndarray) -> EnergyLedger: ...
    def check_energy_or_raise(self, y: np.ndarray, t: float) -> EnergyLedger: ...


def build_system(config: SimulationConfig) -> SupportsSimulation:
    if config.simulation.model == "oned":
        return OneDSystem(config)
    if config.simulation.model == "multizone":
        return MultiZoneSystem(config)
    return LoopSystem(config)


def run_simulation(
    config: SimulationConfig,
    run_id: str | None = None,
    system: SupportsSimulation | None = None,
) -> SimulationResult:
    """Integrate the loop system and return time series + ledger."""
    run_id = run_id or str(uuid.uuid4())
    system = system or build_system(config)
    y0 = system.initial_state()
    system.rhs(0.0, y0)
    t_end = config.simulation.duration_s
    out_dt = max(config.simulation.output_interval_s, 1e-6)
    t_eval = np.arange(0.0, t_end + 0.5 * out_dt, out_dt)
    if t_eval[-1] < t_end:
        t_eval = np.append(t_eval, t_end)

    integ = config.simulation.integrator
    nfev_box = {"n": 0}
    max_nfev = config.numerics.max_nfev

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        nfev_box["n"] += 1
        if nfev_box["n"] > max_nfev:
            raise SimulationAbortError(f"Exceeded max_nfev={max_nfev}")
        return system.rhs(t, y)

    try:
        sol = solve_ivp(
            rhs,
            (0.0, t_end),
            y0,
            method=integ.method,
            rtol=integ.rtol,
            atol=integ.atol,
            t_eval=t_eval,
            max_step=integ.max_step_s,
            dense_output=False,
        )
    except (NonPhysicalStateError, EnergyBalanceError, SimulationAbortError) as exc:
        logger.error("Simulation aborted: %s", exc)
        system.events.append(
            SimulationEvent(
                system.events[-1].time_s if system.events else 0.0,
                "abort",
                str(exc),
                EventSeverity.CRITICAL,
            )
        )
        ledger = system.ledger_from_state(y0)
        sample0 = system.sample_series(0.0, y0)
        keys = list(dict.fromkeys([*SERIES_KEYS, *sample0.keys()]))
        return SimulationResult(
            run_id=run_id,
            times_s=[0.0],
            series={k: [float(sample0.get(k, float("nan")))] for k in keys},
            events=system.events,
            ledger_final=ledger,
            config_dict=config.model_dump(),
            metadata={
                "aborted": True,
                "reason": str(exc),
                "model": config.simulation.model,
            },
            energy_trusted=False,
        )

    if not sol.success:
        system.events.append(
            SimulationEvent(
                float(sol.t[-1]) if sol.t.size else 0.0,
                "integrator_failure",
                sol.message,
                EventSeverity.ERROR,
            )
        )

    times: list[float] = []
    series: dict[str, list[float]] = {}
    energy_trusted = True
    zone_snapshots: list[list[dict[str, Any]]] = []
    cell_snapshots: list[list[dict[str, Any]]] = []

    for i, t in enumerate(sol.t):
        y = sol.y[:, i]
        try:
            system.rhs(float(t), y)
            ledger = system.check_energy_or_raise(y, float(t))
        except (NonPhysicalStateError, EnergyBalanceError, SimulationAbortError) as exc:
            system.events.append(
                SimulationEvent(float(t), "abort", str(exc), EventSeverity.CRITICAL)
            )
            energy_trusted = False
            break
        sample = system.sample_series(float(t), y)
        times.append(float(t))
        for k, v in sample.items():
            series.setdefault(k, []).append(float(v))
        if hasattr(system, "zone_snapshot_segments"):
            zone_snapshots.append(system.zone_snapshot_segments(y))  # type: ignore[attr-defined]
        if hasattr(system, "cell_snapshot") and config.oned.export_cells_in_snapshot:
            cell_snapshots.append(system.cell_snapshot(y))  # type: ignore[attr-defined]
        if not ledger.trusted:
            energy_trusted = False

    # Ensure core SERIES_KEYS exist even if missing
    for k in SERIES_KEYS:
        series.setdefault(k, [float("nan")] * len(times))

    # Milestone 22: rocket Δv post-process (outside plasma energy ledger)
    if config.spacecraft.enabled and times:
        from ouroboros.physics.trajectory import integrate_trajectory_series

        traj = integrate_trajectory_series(
            times_s=times,
            thrust_n=series.get("thrust_n", [0.0] * len(times)),
            mass_flow_kg_s=series.get("nozzle_mass_flow_kg_s", [0.0] * len(times)),
            spacecraft=config.spacecraft,
        )
        series.update(traj)

    y_final = sol.y[:, len(times) - 1] if times else y0
    ledger_final = system.ledger_from_state(y_final)
    if not ledger_final.trusted:
        energy_trusted = False

    meta: dict[str, Any] = {
        "integrator_message": sol.message,
        "integrator_success": bool(sol.success),
        "n_steps": int(getattr(sol, "nfev", nfev_box["n"])),
        "scenario": config.simulation.scenario,
        "model": config.simulation.model,
        "spacecraft_enabled": config.spacecraft.enabled,
    }
    if zone_snapshots:
        meta["zone_snapshot_count"] = len(zone_snapshots)
        meta["final_zone_segments"] = zone_snapshots[-1]
    if cell_snapshots:
        meta["final_cells"] = cell_snapshots[-1]
        meta["n_cells"] = len(cell_snapshots[-1])

    return SimulationResult(
        run_id=run_id,
        times_s=times,
        series=series,
        events=system.events,
        ledger_final=ledger_final,
        config_dict=config.model_dump(),
        metadata=meta,
        energy_trusted=energy_trusted and system._energy_trusted,
    )
