"""Pydantic configuration models (YAML-backed)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IntegratorConfig(BaseModel):
    method: Literal["LSODA", "BDF", "Radau", "RK45", "DOP853"] = "LSODA"
    rtol: float = 1e-6
    atol: float = 1e-9
    min_step_s: float = 1e-9
    max_step_s: float = 1e-2
    first_step_s: float | None = None


class SimulationSection(BaseModel):
    duration_s: float = 1.0
    output_interval_s: float = 1e-3
    integrator: IntegratorConfig = Field(default_factory=IntegratorConfig)
    seed: int = 0
    strict_energy: bool = False
    scenario: str = "passive"
    model: Literal["lumped", "multizone", "oned"] = "lumped"


class GeometrySection(BaseModel):
    chamber_volume_m3: float = 1.0
    branch_a_volume_m3: float = 0.4
    branch_b_volume_m3: float = 0.4
    return_channel_volume_m3: float = 0.3
    expansion_volume_m3: float = 0.2
    branch_cross_section_m2: float = 0.05


class PlasmaSection(BaseModel):
    initial_density_m3: float = 1.0e19
    initial_ion_temperature_ev: float = 100.0
    initial_electron_temperature_ev: float = 100.0
    initial_flow_a_m_s: float = 50.0
    initial_flow_b_m_s: float = 45.0  # intentional asymmetry
    deuterium_fraction: float = 0.5
    tritium_fraction: float = 0.5
    helium_fraction: float = 0.0
    impurity_fraction: float = 0.0
    mean_particle_mass_kg: float = 4.18e-27  # ~2.5 amu average DT placeholder
    effective_inertia_kg: float = 1.0e-6  # phenomenological
    friction_coeff_kg_s: float = 2.0e-5  # phenomenological
    confinement_factor: float = 1.0
    confinement_time_s: float = 0.1  # phenomenological tau_E


class ThrottleSection(BaseModel):
    inductance_h: float = 1.0e-3
    resistance_ohm: float = 1.0e-4
    mutual_inductance_h: float = 0.0
    current_limit_a: float = 1.0e4
    field_limit_t: float = 5.0
    coil_turns_per_metre: float = 100.0
    initial_current_a: float = 0.0
    quench_resistance_ohm: float = 1.0
    coupling_force_coeff_n_per_a: float = 0.0  # phenomenological F_mag
    # Milestone 8: consistent electromechanical coupling
    coupling_mode: Literal["none", "phenomenological", "consistent"] = "none"
    emf_coeff_v_s_per_m: float = 0.0  # k_em [V/(m/s)] = [N/A]


class FusionSection(BaseModel):
    enabled: bool = False
    reaction: Literal["DT"] = "DT"
    reactivity_model: Literal["bosch_hale", "placeholder"] = "bosch_hale"


class LossesSection(BaseModel):
    bremsstrahlung: bool = True
    transport: bool = True
    wall: bool = True
    exhaust: bool = True
    magnetic: bool = True
    recovery_fraction: float = 0.0  # phenomenological
    wall_loss_coeff_s: float = 1.0  # 1/tau_wall phenomenological
    exhaust_loss_coeff_s: float = 0.2
    impurity_z_eff: float = 1.0
    # Anisotropic transport stub (Milestone 8)
    anisotropic_transport: bool = False
    tau_parallel_s: float = 0.05
    tau_perp_s: float = 0.5


class ReducedMHDSection(BaseModel):
    """Reduced-MHD-like forces (Milestone 8 stubs → Milestone 10 energy-aware)."""

    enabled: bool = False
    magnetic_pressure_scale: float = 0.0
    alfven_damping_fraction: float = 0.0
    # Hydrodynamic Δp·A along paths (return/branch → chamber)
    pressure_drive: bool = False
    pressure_drive_scale: float = 1.0
    # Exchange mp + Δp work with plasma internal energy (keeps ledger closed)
    compressional_exchange: bool = True


class ControllerSection(BaseModel):
    type: Literal["none", "pid", "slow_supervisor"] = "none"
    parameters: dict[str, Any] = Field(default_factory=dict)


class EnergySection(BaseModel):
    relative_tolerance: float = 1e-4
    absolute_floor_j: float = 1.0


class NumericsSection(BaseModel):
    """Numerical safety guards — not physics."""

    max_temperature_ev: float = 100_000.0  # soft ceiling; trips event if crossed
    max_density_m3: float = 1.0e22
    max_nfev: int = 200_000


class DriveSection(BaseModel):
    """External / synthetic drive terms (phenomenological)."""

    external_heater_w: float = 0.0
    synthetic_heat_w: float = 0.0
    synthetic_heat_modulation_hz: float = 0.0
    synthetic_heat_modulation_amp: float = 0.0
    drive_force_a_n: float = 0.0
    drive_force_b_n: float = 0.0
    fueling_rate_s: float = 0.0  # particles/s added to chamber


class FaultSection(BaseModel):
    branch_a_blocked: bool = False
    branch_b_blocked: bool = False
    cooling_loss: bool = False
    force_quench_a: bool = False
    force_quench_b: bool = False
    density_spike_factor: float = 1.0
    heater_trip: bool = False
    helium_source_rate_s: float = 0.0
    trip_energy_balance: bool = False


class MultiZoneSection(BaseModel):
    """Options for simulation.model == multizone."""

    geometry_file: str | None = "geometry/loop_geometry.json"


class OneDSection(BaseModel):
    """Options for simulation.model == oned (Milestone 7+)."""

    geometry_file: str | None = "geometry/loop_geometry.json"
    cells_per_segment: int = 4
    export_cells_in_snapshot: bool = True
    # Milestone 11/12: dual_path | cell_pressure | cell_velocity
    momentum_mode: Literal["dual_path", "cell_pressure", "cell_velocity"] = "dual_path"
    pressure_force_scale: float = 1.0e-6
    # When cell_pressure / cell_velocity: exchange pressure work with cell U
    compressional_exchange: bool = True
    # Milestone 14: upwind momentum flux (cell_velocity only)
    momentum_flux: bool = False
    thermalize_momentum_flux: bool = True
    # Milestone 15: none | rusanov (replaces cell_grad_p + upwind when set)
    riemann: Literal["none", "rusanov"] = "none"


class BlanketSection(BaseModel):
    """Neutron blanket channel (Milestone 9). Disabled = legacy instant neutron sink."""

    enabled: bool = False
    capture_fraction: float = 0.9  # phenomenological
    coolant_time_s: float = 0.5
    breeding_ratio: float = 1.05  # placeholder TBR
    initial_thermal_energy_j: float = 0.0


class NozzleSection(BaseModel):
    """Magnetic nozzle / directed exhaust (Milestone 13). Speculative propulsion proxy."""

    enabled: bool = False
    zone_id: str = "expansion"  # multizone/oned; lumped uses chamber
    extract_fraction: float = 0.05  # fraction of zone inventory per extract_time
    extract_time_s: float = 0.2
    magnetic_efficiency: float = 0.6  # jet / extracted enthalpy


class SimulationConfig(BaseModel):
    simulation: SimulationSection = Field(default_factory=SimulationSection)
    geometry: GeometrySection = Field(default_factory=GeometrySection)
    plasma: PlasmaSection = Field(default_factory=PlasmaSection)
    throttle_a: ThrottleSection = Field(default_factory=ThrottleSection)
    throttle_b: ThrottleSection = Field(default_factory=ThrottleSection)
    fusion: FusionSection = Field(default_factory=FusionSection)
    losses: LossesSection = Field(default_factory=LossesSection)
    controller: ControllerSection = Field(default_factory=ControllerSection)
    energy: EnergySection = Field(default_factory=EnergySection)
    numerics: NumericsSection = Field(default_factory=NumericsSection)
    drive: DriveSection = Field(default_factory=DriveSection)
    faults: FaultSection = Field(default_factory=FaultSection)
    multizone: MultiZoneSection = Field(default_factory=MultiZoneSection)
    oned: OneDSection = Field(default_factory=OneDSection)
    reduced_mhd: ReducedMHDSection = Field(default_factory=ReducedMHDSection)
    blanket: BlanketSection = Field(default_factory=BlanketSection)
    nozzle: NozzleSection = Field(default_factory=NozzleSection)
