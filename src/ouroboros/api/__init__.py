"""Public simulation control API (no GUI dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ouroboros.core import build_system, run_simulation
from ouroboros.domain import SimulationResult
from ouroboros.domain.config import SimulationConfig
from ouroboros.io import load_config, write_run_directory


class SimulationSession:
    """
    Control surface:
    - create / load config
    - step / run interval
    - stop
    - get state / history
    - export
    """

    def __init__(self, config: SimulationConfig, run_id: str | None = None) -> None:
        self.config = config
        self.system = build_system(config)
        self.y = self.system.initial_state()
        self.t = 0.0
        self.run_id = run_id
        self._stopped = False
        self.history_t: list[float] = [0.0]
        self.history: dict[str, list[float]] = {}
        sample0 = self.system.sample_series(0.0, self.y)
        for k, v in sample0.items():
            self.history[k] = [v]
        self._result: SimulationResult | None = None

    @classmethod
    def from_config_file(cls, path: str | Path) -> SimulationSession:
        return cls(load_config(path))

    def step(self, dt: float) -> dict[str, float]:
        if self._stopped:
            raise RuntimeError("Session stopped")
        from scipy.integrate import solve_ivp

        integ = self.config.simulation.integrator
        sol = solve_ivp(
            self.system.rhs,
            (self.t, self.t + dt),
            self.y,
            method=integ.method,
            rtol=integ.rtol,
            atol=integ.atol,
            max_step=min(integ.max_step_s, dt),
        )
        if not sol.success:
            raise RuntimeError(sol.message)
        self.t = float(sol.t[-1])
        self.y = sol.y[:, -1].copy()
        self.system.rhs(self.t, self.y)
        sample = self.system.sample_series(self.t, self.y)
        self.history_t.append(self.t)
        for k, v in sample.items():
            self.history.setdefault(k, []).append(v)
        self.system.check_energy_or_raise(self.y, self.t)
        return sample

    def run_interval(self, duration_s: float | None = None) -> SimulationResult:
        if duration_s is not None:
            self.config.simulation.duration_s = duration_s
        result = run_simulation(self.config, run_id=self.run_id, system=build_system(self.config))
        self._result = result
        self._stopped = True
        return result

    def stop(self) -> None:
        self._stopped = True

    def get_state(self) -> dict[str, Any]:
        self.system.rhs(self.t, self.y)
        return {
            "time_s": self.t,
            "stopped": self._stopped,
            "sample": self.system.sample_series(self.t, self.y),
            "ledger": self.system.ledger_from_state(self.y).to_dict(),
        }

    def get_history(self, keys: list[str] | None = None) -> dict[str, list[float]]:
        keys = keys or list(self.history.keys())
        out = {"time_s": list(self.history_t)}
        for k in keys:
            out[k] = list(self.history.get(k, []))
        return out

    def export(self, root: str | Path) -> Path:
        if self._result is None:
            self._result = self.run_interval()
        return write_run_directory(self._result, root)
