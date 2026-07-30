"""ODE integrator wrapper around SciPy solve_ivp."""

from __future__ import annotations

import logging
import uuid

import numpy as np
from scipy.integrate import solve_ivp

from ouroboros.core.exceptions import (
    EnergyBalanceError,
    NonPhysicalStateError,
    SimulationAbortError,
)
from ouroboros.core.system import SERIES_KEYS, LoopSystem
from ouroboros.domain import EventSeverity, SimulationEvent, SimulationResult
from ouroboros.domain.config import SimulationConfig

logger = logging.getLogger(__name__)


def run_simulation(
    config: SimulationConfig,
    run_id: str | None = None,
    system: LoopSystem | None = None,
) -> SimulationResult:
    """Integrate the loop system and return time series + ledger."""
    run_id = run_id or str(uuid.uuid4())
    system = system or LoopSystem(config)
    y0 = system.initial_state()
    # Refresh diagnostics at t=0
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
        return SimulationResult(
            run_id=run_id,
            times_s=[0.0],
            series={k: [float(sample0[k])] for k in SERIES_KEYS},
            events=system.events,
            ledger_final=ledger,
            config_dict=config.model_dump(),
            metadata={"aborted": True, "reason": str(exc)},
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
    series: dict[str, list[float]] = {k: [] for k in SERIES_KEYS}
    energy_trusted = True

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
        for k in SERIES_KEYS:
            series[k].append(float(sample[k]))
        if not ledger.trusted:
            energy_trusted = False

    y_final = sol.y[:, len(times) - 1] if times else y0
    ledger_final = system.ledger_from_state(y_final)
    if not ledger_final.trusted:
        energy_trusted = False

    return SimulationResult(
        run_id=run_id,
        times_s=times,
        series=series,
        events=system.events,
        ledger_final=ledger_final,
        config_dict=config.model_dump(),
        metadata={
            "integrator_message": sol.message,
            "integrator_success": bool(sol.success),
            "n_steps": int(getattr(sol, "nfev", nfev_box["n"])),
            "scenario": config.simulation.scenario,
        },
        energy_trusted=energy_trusted and system._energy_trusted,
    )
