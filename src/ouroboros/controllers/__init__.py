"""Controllers: slow actuators only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ControlSignals:
    external_heater_w: float = 0.0
    fueling_rate_s: float = 0.0
    valve_coeff_a: float = 1.0
    valve_coeff_b: float = 1.0
    branch_flow_limit_a: float = 1.0e9
    branch_flow_limit_b: float = 1.0e9
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlSensors:
    time_s: float
    density_a: float
    density_b: float
    temperature_chamber_k: float
    q_factor: float
    fusion_power_w: float
    flow_a: float
    flow_b: float


class Controller(ABC):
    @abstractmethod
    def update(self, sensors: ControlSensors, base: ControlSignals) -> ControlSignals:
        raise NotImplementedError

    def name(self) -> str:
        return type(self).__name__


class NoController(Controller):
    def update(self, sensors: ControlSensors, base: ControlSignals) -> ControlSignals:
        return base


class PIDController(Controller):
    """PID on chamber temperature error → external heater (slowish academic controller)."""

    def __init__(
        self,
        setpoint_k: float,
        kp: float,
        ki: float,
        kd: float,
        power_min_w: float = 0.0,
        power_max_w: float = 1.0e8,
    ) -> None:
        self.setpoint_k = setpoint_k
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.power_min_w = power_min_w
        self.power_max_w = power_max_w
        self._integral = 0.0
        self._prev_error: float | None = None
        self._prev_time: float | None = None

    def update(self, sensors: ControlSensors, base: ControlSignals) -> ControlSignals:
        error = self.setpoint_k - sensors.temperature_chamber_k
        dt = 0.0 if self._prev_time is None else max(sensors.time_s - self._prev_time, 0.0)
        if dt > 0.0:
            self._integral += error * dt
        derivative = 0.0
        if self._prev_error is not None and dt > 0.0:
            derivative = (error - self._prev_error) / dt
        power = self.kp * error + self.ki * self._integral + self.kd * derivative
        power = min(max(power, self.power_min_w), self.power_max_w)
        self._prev_error = error
        self._prev_time = sensors.time_s
        out = ControlSignals(
            external_heater_w=power,
            fueling_rate_s=base.fueling_rate_s,
            valve_coeff_a=base.valve_coeff_a,
            valve_coeff_b=base.valve_coeff_b,
            branch_flow_limit_a=base.branch_flow_limit_a,
            branch_flow_limit_b=base.branch_flow_limit_b,
            metadata={"pid_error": error, "controller": "pid"},
        )
        return out


class SlowSupervisorController(Controller):
    """
    Changes only slow setpoints on a coarse cadence.
    Fast oscillations should come from passive dynamics, not micro-step correction.
    """

    def __init__(
        self,
        update_period_s: float = 0.05,
        heater_w: float = 0.0,
        fueling_rate_s: float = 0.0,
        density_target_m3: float = 1.0e19,
        valve_gain: float = 0.1,
    ) -> None:
        self.update_period_s = update_period_s
        self.heater_w = heater_w
        self.fueling_rate_s = fueling_rate_s
        self.density_target_m3 = density_target_m3
        self.valve_gain = valve_gain
        self._last_update = -1.0e99
        self._cached = ControlSignals(
            external_heater_w=heater_w,
            fueling_rate_s=fueling_rate_s,
        )

    def update(self, sensors: ControlSensors, base: ControlSignals) -> ControlSignals:
        if sensors.time_s - self._last_update < self.update_period_s:
            return self._cached
        self._last_update = sensors.time_s
        # Slow density balancing via valves
        err_a = sensors.density_a - self.density_target_m3
        err_b = sensors.density_b - self.density_target_m3
        valve_a = min(
            max(1.0 - self.valve_gain * err_a / max(self.density_target_m3, 1.0), 0.2), 1.5
        )
        valve_b = min(
            max(1.0 - self.valve_gain * err_b / max(self.density_target_m3, 1.0), 0.2), 1.5
        )
        self._cached = ControlSignals(
            external_heater_w=self.heater_w
            if base.external_heater_w == 0
            else base.external_heater_w,
            fueling_rate_s=self.fueling_rate_s,
            valve_coeff_a=valve_a,
            valve_coeff_b=valve_b,
            branch_flow_limit_a=base.branch_flow_limit_a,
            branch_flow_limit_b=base.branch_flow_limit_b,
            metadata={"controller": "slow_supervisor", "valve_a": valve_a, "valve_b": valve_b},
        )
        return self._cached


def build_controller(type_name: str, parameters: dict[str, Any]) -> Controller:
    if type_name == "none":
        return NoController()
    if type_name == "pid":
        return PIDController(
            setpoint_k=float(parameters.get("setpoint_k", 1.16e7)),
            kp=float(parameters.get("kp", 1.0e-2)),
            ki=float(parameters.get("ki", 1.0e-4)),
            kd=float(parameters.get("kd", 0.0)),
            power_min_w=float(parameters.get("power_min_w", 0.0)),
            power_max_w=float(parameters.get("power_max_w", 1.0e9)),
        )
    if type_name == "slow_supervisor":
        return SlowSupervisorController(
            update_period_s=float(parameters.get("update_period_s", 0.05)),
            heater_w=float(parameters.get("heater_w", 0.0)),
            fueling_rate_s=float(parameters.get("fueling_rate_s", 0.0)),
            density_target_m3=float(parameters.get("density_target_m3", 1.0e19)),
            valve_gain=float(parameters.get("valve_gain", 0.1)),
        )
    raise ValueError(f"Unknown controller type: {type_name}")
