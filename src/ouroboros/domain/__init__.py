"""Domain entities for the Ouroboros plasma loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ThrottleStatus(str, Enum):
    NORMAL = "normal"
    LIMITING = "limiting"
    QUENCH = "quench"
    FAULT = "fault"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PlasmaState:
    """Lumped plasma state for one zone. All fields SI unless noted in comments."""

    particle_number: float  # [1]
    density_m3: float  # [m^-3]
    volume_m3: float  # [m^3]
    flow_velocity_m_s: float  # [m/s]
    mass_flow_kg_s: float  # [kg/s]
    ion_temperature_k: float  # [K]
    electron_temperature_k: float  # [K]
    pressure_pa: float  # [Pa]
    internal_energy_j: float  # [J]
    magnetic_energy_j: float  # [J]
    deuterium_fraction: float  # [-]
    tritium_fraction: float  # [-]
    helium_fraction: float  # [-]
    impurity_fraction: float  # [-]
    residence_time_s: float  # [s]
    confinement_factor: float  # [-] phenomenological

    def validate_nonnegative(self) -> list[str]:
        problems: list[str] = []
        checks = {
            "particle_number": self.particle_number,
            "density_m3": self.density_m3,
            "volume_m3": self.volume_m3,
            "ion_temperature_k": self.ion_temperature_k,
            "electron_temperature_k": self.electron_temperature_k,
            "pressure_pa": self.pressure_pa,
            "internal_energy_j": self.internal_energy_j,
            "magnetic_energy_j": self.magnetic_energy_j,
        }
        for name, value in checks.items():
            if value < 0.0:
                problems.append(f"{name} is negative: {value}")
        return problems

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlasmaBranch:
    name: str
    state: PlasmaState
    effective_inertia_kg: float  # phenomenological [kg]
    cross_section_m2: float  # [m^2]
    friction_coeff_kg_s: float  # [kg/s] for F = -b v
    blocked: bool = False


@dataclass
class MagneticThrottle:
    name: str
    inductance_h: float
    resistance_ohm: float
    mutual_inductance_h: float
    current_a: float
    current_limit_a: float
    field_limit_t: float
    coil_turns_per_metre: float  # phenomenological B ~ mu0 n I
    status: ThrottleStatus = ThrottleStatus.NORMAL
    quench_resistance_ohm: float = 1.0  # placeholder dump resistance

    @property
    def stored_energy_j(self) -> float:
        return 0.5 * self.inductance_h * self.current_a**2

    def estimated_field_t(self) -> float:
        mu0 = 1.2566370614e-6
        return mu0 * self.coil_turns_per_metre * abs(self.current_a)


@dataclass
class ReactionChamber:
    state: PlasmaState
    synthetic_heat_w: float = 0.0  # placeholder / scenario 3


@dataclass
class ReturnChannel:
    state: PlasmaState
    split_fraction_to_a: float = 0.5


@dataclass
class ExpansionSection:
    state: PlasmaState
    expansion_ratio: float = 1.0  # phenomenological


@dataclass
class Separator:
    helium_removal_rate_s: float = 0.0  # [s^-1] phenomenological
    impurity_removal_rate_s: float = 0.0


@dataclass
class ExternalHeater:
    power_w: float = 0.0
    enabled: bool = True


@dataclass
class SimulationEvent:
    time_s: float
    kind: str
    message: str
    severity: EventSeverity = EventSeverity.INFO
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnergyLedger:
    """Strict energy bookkeeping. All values in joules unless named as power."""

    e_internal_j: float = 0.0
    e_kinetic_j: float = 0.0
    e_magnetic_j: float = 0.0
    e_external_input_j: float = 0.0
    e_fusion_total_j: float = 0.0
    e_alpha_to_plasma_j: float = 0.0
    e_neutron_blanket_j: float = 0.0
    e_recovered_j: float = 0.0
    e_radiation_j: float = 0.0
    e_transport_j: float = 0.0
    e_wall_j: float = 0.0
    e_exhaust_j: float = 0.0
    e_magnetic_loss_j: float = 0.0
    e_friction_j: float = 0.0
    e_drive_work_j: float = 0.0  # mechanical work from external drive forces
    e_error_j: float = 0.0
    e_state_initial_j: float = 0.0
    trusted: bool = True
    relative_residual: float = 0.0

    def state_energy(self) -> float:
        return self.e_internal_j + self.e_kinetic_j + self.e_magnetic_j

    def inputs(self) -> float:
        return (
            self.e_external_input_j
            + self.e_fusion_total_j
            + self.e_recovered_j
            + self.e_drive_work_j
        )

    def outputs_and_losses(self) -> float:
        return (
            self.e_radiation_j
            + self.e_transport_j
            + self.e_wall_j
            + self.e_exhaust_j
            + self.e_magnetic_loss_j
            + self.e_neutron_blanket_j
            + self.e_friction_j
        )

    def compute_residual(self) -> float:
        self.e_error_j = (
            self.e_state_initial_j + self.inputs() - self.state_energy() - self.outputs_and_losses()
        )
        return self.e_error_j

    def relative_error(self, floor_j: float = 1.0) -> float:
        scale = max(
            abs(self.e_state_initial_j),
            abs(self.state_energy()),
            abs(self.inputs()),
            floor_j,
        )
        self.relative_residual = abs(self.e_error_j) / scale
        return self.relative_residual

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    run_id: str
    times_s: list[float]
    series: dict[str, list[float]]
    events: list[SimulationEvent]
    ledger_final: EnergyLedger
    config_dict: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    energy_trusted: bool = True
