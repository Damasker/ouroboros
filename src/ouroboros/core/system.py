"""0D dual-branch plasma loop ODE system."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ouroboros.controllers import (
    Controller,
    ControlSensors,
    ControlSignals,
    build_controller,
)
from ouroboros.core.exceptions import (
    EnergyBalanceError,
    NonPhysicalStateError,
)
from ouroboros.domain import (
    EnergyLedger,
    EventSeverity,
    MagneticThrottle,
    PlasmaState,
    SimulationEvent,
    ThrottleStatus,
)
from ouroboros.domain.config import SimulationConfig
from ouroboros.physics.fusion import fusion_rate_per_second, get_reactivity_model
from ouroboros.physics.losses import compute_zone_losses
from ouroboros.units import (
    DT_ALPHA_J,
    DT_FUSION_TOTAL_J,
    DT_NEUTRON_J,
    ev_to_kelvin,
    kelvin_to_ev,
    pressure_pa,
    thermal_energy_joule,
)

logger = logging.getLogger(__name__)

# State vector layout
IDX_N_A, IDX_U_A, IDX_V_A = 0, 1, 2
IDX_N_B, IDX_U_B, IDX_V_B = 3, 4, 5
IDX_N_C, IDX_U_C = 6, 7
IDX_N_R, IDX_U_R = 8, 9
IDX_I_A, IDX_I_B = 10, 11
IDX_ACC_EXT = 12
IDX_ACC_FUS = 13
IDX_ACC_ALPHA = 14
IDX_ACC_NEUT = 15
IDX_ACC_RAD = 16
IDX_ACC_TRANS = 17
IDX_ACC_WALL = 18
IDX_ACC_EXH = 19
IDX_ACC_MAGLOSS = 20
IDX_ACC_REC = 21
IDX_N_HE_C = 22
IDX_ACC_FRICTION = 23
IDX_ACC_DRIVE = 24
IDX_E_BLANKET = 25
IDX_ACC_NEUT_LEAK = 26
IDX_ACC_COOLANT = 27
IDX_ACC_THRUST = 28
N_STATE = 29

SERIES_KEYS = [
    "density_a",
    "density_b",
    "density_chamber",
    "temp_a_ev",
    "temp_b_ev",
    "temp_chamber_ev",
    "flow_a",
    "flow_b",
    "mass_flow_a",
    "mass_flow_b",
    "current_throttle_a",
    "current_throttle_b",
    "magnetic_energy",
    "fusion_power_w",
    "alpha_power_w",
    "neutron_power_w",
    "external_power_w",
    "loss_power_w",
    "recovered_power_w",
    "wall_energy_j",
    "q_factor",
    "energy_residual_j",
    "energy_residual_rel",
    "controller_heater_w",
    "internal_energy_total_j",
    "kinetic_energy_j",
    "blanket_energy_j",
    "blanket_coolant_power_w",
    "neutron_leak_power_w",
    "thrust_n",
    "isp_s",
    "jet_power_w",
    "nozzle_mass_flow_kg_s",
    "spacecraft_mass_kg",
    "delta_v_m_s",
    "acceleration_m_s2",
    "orbit_x_m",
    "orbit_y_m",
    "orbit_vx_m_s",
    "orbit_vy_m_s",
    "orbit_radius_m",
]


def _temperature_from_energy(n: float, u: float, volume: float) -> float:
    """Assume Ti=Te, n_e=n_i=n/V → U = 3 N k T → T = U/(3 N k)."""
    from ouroboros.units import BOLTZMANN_J_PER_K

    if n <= 0.0 or volume <= 0.0:
        return 0.0
    # U = 3/2 * 2 * N k T = 3 N k T with N particles ions ≈ electrons
    return u / (3.0 * n * BOLTZMANN_J_PER_K)


def _rebuild_state(
    n: float, u: float, v: float, volume: float, cfg: SimulationConfig
) -> PlasmaState:

    density = n / volume if volume > 0 else 0.0
    temp_k = _temperature_from_energy(n, u, volume)
    # mass_flow = rho * A * v
    mass_flow = (
        density * cfg.plasma.mean_particle_mass_kg * cfg.geometry.branch_cross_section_m2 * v
    )
    p = pressure_pa(density, temp_k, density, temp_k)
    return PlasmaState(
        particle_number=n,
        density_m3=density,
        volume_m3=volume,
        flow_velocity_m_s=v,
        mass_flow_kg_s=mass_flow,
        ion_temperature_k=temp_k,
        electron_temperature_k=temp_k,
        pressure_pa=p,
        internal_energy_j=u,
        magnetic_energy_j=0.0,
        deuterium_fraction=cfg.plasma.deuterium_fraction,
        tritium_fraction=cfg.plasma.tritium_fraction,
        helium_fraction=cfg.plasma.helium_fraction,
        impurity_fraction=cfg.plasma.impurity_fraction,
        residence_time_s=cfg.plasma.confinement_time_s,
        confinement_factor=cfg.plasma.confinement_factor,
    )


@dataclass
class InstantDiagnostics:
    fusion_power_w: float = 0.0
    alpha_power_w: float = 0.0
    neutron_power_w: float = 0.0
    external_power_w: float = 0.0
    loss_power_w: float = 0.0
    recovered_power_w: float = 0.0
    q_factor: float = float("nan")
    controller_meta: dict[str, Any] = field(default_factory=dict)


class LoopSystem:
    """Coupled ODE model of the dual-branch loop."""

    def __init__(self, config: SimulationConfig, controller: Controller | None = None) -> None:
        self.config = config
        self.controller = controller or build_controller(
            config.controller.type, config.controller.parameters
        )
        self.reactivity = get_reactivity_model(config.fusion.reactivity_model)
        self.events: list[SimulationEvent] = []
        self._control = ControlSignals(
            external_heater_w=config.drive.external_heater_w,
            fueling_rate_s=config.drive.fueling_rate_s,
        )
        self._last_diag = InstantDiagnostics()
        self._aborted = False
        self._energy_trusted = True
        self.e_state_initial = 0.0

        # Throttle handles (currents live in state vector)
        self.throttle_a = MagneticThrottle(
            name="throttle_a",
            inductance_h=config.throttle_a.inductance_h,
            resistance_ohm=config.throttle_a.resistance_ohm,
            mutual_inductance_h=config.throttle_a.mutual_inductance_h,
            current_a=config.throttle_a.initial_current_a,
            current_limit_a=config.throttle_a.current_limit_a,
            field_limit_t=config.throttle_a.field_limit_t,
            coil_turns_per_metre=config.throttle_a.coil_turns_per_metre,
            quench_resistance_ohm=config.throttle_a.quench_resistance_ohm,
        )
        self.throttle_b = MagneticThrottle(
            name="throttle_b",
            inductance_h=config.throttle_b.inductance_h,
            resistance_ohm=config.throttle_b.resistance_ohm,
            mutual_inductance_h=config.throttle_b.mutual_inductance_h,
            current_a=config.throttle_b.initial_current_a,
            current_limit_a=config.throttle_b.current_limit_a,
            field_limit_t=config.throttle_b.field_limit_t,
            coil_turns_per_metre=config.throttle_b.coil_turns_per_metre,
            quench_resistance_ohm=config.throttle_b.quench_resistance_ohm,
        )

    def initial_state(self) -> np.ndarray:
        cfg = self.config
        ti = ev_to_kelvin(cfg.plasma.initial_ion_temperature_ev)
        te = ev_to_kelvin(cfg.plasma.initial_electron_temperature_ev)
        n0 = cfg.plasma.initial_density_m3

        def pack_zone(volume: float, v: float = 0.0) -> tuple[float, float]:
            N = n0 * volume
            U = thermal_energy_joule(n0, ti, n0, te, volume)
            return N, U

        na, ua = pack_zone(cfg.geometry.branch_a_volume_m3, cfg.plasma.initial_flow_a_m_s)
        nb, ub = pack_zone(cfg.geometry.branch_b_volume_m3, cfg.plasma.initial_flow_b_m_s)
        nc, uc = pack_zone(cfg.geometry.chamber_volume_m3)
        nr, ur = pack_zone(cfg.geometry.return_channel_volume_m3)

        if cfg.faults.density_spike_factor != 1.0:
            na *= cfg.faults.density_spike_factor
            ua *= cfg.faults.density_spike_factor

        y = np.zeros(N_STATE, dtype=float)
        y[IDX_N_A], y[IDX_U_A], y[IDX_V_A] = na, ua, cfg.plasma.initial_flow_a_m_s
        y[IDX_N_B], y[IDX_U_B], y[IDX_V_B] = nb, ub, cfg.plasma.initial_flow_b_m_s
        y[IDX_N_C], y[IDX_U_C] = nc, uc
        y[IDX_N_R], y[IDX_U_R] = nr, ur
        y[IDX_I_A] = cfg.throttle_a.initial_current_a
        y[IDX_I_B] = cfg.throttle_b.initial_current_a
        y[IDX_N_HE_C] = cfg.plasma.helium_fraction * nc
        y[IDX_E_BLANKET] = cfg.blanket.initial_thermal_energy_j if cfg.blanket.enabled else 0.0

        self.e_state_initial = self._state_energy(y)
        return y

    def _state_energy(self, y: np.ndarray) -> float:
        cfg = self.config
        m_eff = cfg.plasma.effective_inertia_kg
        e_int = float(y[IDX_U_A] + y[IDX_U_B] + y[IDX_U_C] + y[IDX_U_R])
        e_kin = 0.5 * m_eff * (float(y[IDX_V_A]) ** 2 + float(y[IDX_V_B]) ** 2)
        e_mag = 0.5 * cfg.throttle_a.inductance_h * float(y[IDX_I_A]) ** 2
        e_mag += 0.5 * cfg.throttle_b.inductance_h * float(y[IDX_I_B]) ** 2
        e_bl = float(y[IDX_E_BLANKET]) if cfg.blanket.enabled else 0.0
        return e_int + e_kin + e_mag + e_bl

    def _exchange_rate(self, n_src: float, v: float, volume: float, valve: float) -> float:
        """Convective particle throughput ~ |v| / L * N * valve, L = V/A phenomenological."""
        cfg = self.config
        length = volume / max(cfg.geometry.branch_cross_section_m2, 1e-12)
        tau = length / max(abs(v), 1e-9)
        return valve * n_src / max(tau, 1e-9)

    def rhs(self, t: float, y: np.ndarray) -> np.ndarray:
        if self._aborted:
            return np.zeros_like(y)

        cfg = self.config
        dydt = np.zeros_like(y)

        # Unpack
        n_a, u_a, v_a = float(y[IDX_N_A]), float(y[IDX_U_A]), float(y[IDX_V_A])
        n_b, u_b, v_b = float(y[IDX_N_B]), float(y[IDX_U_B]), float(y[IDX_V_B])
        n_c, u_c = float(y[IDX_N_C]), float(y[IDX_U_C])
        n_r, u_r = float(y[IDX_N_R]), float(y[IDX_U_R])
        i_a, i_b = float(y[IDX_I_A]), float(y[IDX_I_B])
        n_he = float(y[IDX_N_HE_C])

        # Non-physical detection (do not silently clip)
        for label, val in [
            ("N_a", n_a),
            ("N_b", n_b),
            ("N_c", n_c),
            ("N_r", n_r),
            ("U_a", u_a),
            ("U_b", u_b),
            ("U_c", u_c),
            ("U_r", u_r),
        ]:
            if val < -1e-6:
                msg = f"Non-physical negative {label}={val} at t={t}"
                self.events.append(SimulationEvent(t, "nonphysical", msg, EventSeverity.CRITICAL))
                self._aborted = True
                raise NonPhysicalStateError(msg)

        va_vol = cfg.geometry.branch_a_volume_m3
        vb_vol = cfg.geometry.branch_b_volume_m3
        vc = cfg.geometry.chamber_volume_m3

        dens_a = n_a / va_vol
        dens_b = n_b / vb_vol
        dens_c = n_c / vc
        temp_c = _temperature_from_energy(n_c, u_c, vc)

        # Numerical safety ceiling (not a physical model)
        t_ceil_k = ev_to_kelvin(cfg.numerics.max_temperature_ev)
        if temp_c > t_ceil_k or dens_c > cfg.numerics.max_density_m3:
            msg = (
                f"Numerical safety limit exceeded at t={t}: "
                f"T_c={kelvin_to_ev(temp_c):.3e} eV, n_c={dens_c:.3e}"
            )
            self.events.append(SimulationEvent(t, "numerics_limit", msg, EventSeverity.CRITICAL))
            self._aborted = True
            raise NonPhysicalStateError(msg)
        q_tmp = self._last_diag.q_factor
        sensors = ControlSensors(
            time_s=t,
            density_a=dens_a,
            density_b=dens_b,
            temperature_chamber_k=temp_c,
            q_factor=0.0 if math.isnan(q_tmp) else q_tmp,
            fusion_power_w=self._last_diag.fusion_power_w,
            flow_a=v_a,
            flow_b=v_b,
        )
        base = ControlSignals(
            external_heater_w=0.0 if cfg.faults.heater_trip else cfg.drive.external_heater_w,
            fueling_rate_s=cfg.drive.fueling_rate_s,
        )
        self._control = self.controller.update(sensors, base)

        valve_a = self._control.valve_coeff_a
        valve_b = self._control.valve_coeff_b
        if cfg.faults.branch_a_blocked:
            valve_a = 0.0
        if cfg.faults.branch_b_blocked:
            valve_b = 0.0

        # Particle exchange: branches → chamber → return → split to branches
        rate_a_to_c = self._exchange_rate(n_a, v_a, va_vol, valve_a)
        rate_b_to_c = self._exchange_rate(n_b, v_b, vb_vol, valve_b)
        # Chamber drains to return with characteristic time
        rate_c_to_r = n_c / max(cfg.plasma.confinement_time_s, 1e-9) * 0.5
        # Return splits
        split_a = 0.5
        rate_r_to_a = split_a * n_r / max(cfg.plasma.confinement_time_s, 1e-9) * 0.5
        rate_r_to_b = (1.0 - split_a) * n_r / max(cfg.plasma.confinement_time_s, 1e-9) * 0.5

        fuel = self._control.fueling_rate_s
        he_source = cfg.faults.helium_source_rate_s

        # Fusion in chamber
        f_d = max(cfg.plasma.deuterium_fraction * (1.0 - n_he / max(n_c, 1.0)), 0.0)
        f_t = max(cfg.plasma.tritium_fraction * (1.0 - n_he / max(n_c, 1.0)), 0.0)
        n_d = dens_c * f_d
        n_t = dens_c * f_t
        r_fusion = 0.0
        p_fusion = 0.0
        p_alpha = 0.0
        p_neut = 0.0
        if cfg.fusion.enabled:
            r_fusion = fusion_rate_per_second(n_d, n_t, vc, temp_c, self.reactivity)
            p_fusion = r_fusion * DT_FUSION_TOTAL_J
            p_alpha = r_fusion * DT_ALPHA_J
            p_neut = r_fusion * DT_NEUTRON_J

        # Losses per zone (chamber dominant for radiation)
        z_eff = cfg.losses.impurity_z_eff
        if cfg.faults.cooling_loss:
            # placeholder: disable wall extraction → energy stays / transport reduced removal
            wall_coeff = 0.0
        else:
            wall_coeff = cfg.losses.wall_loss_coeff_s

        losses_c = compute_zone_losses(
            n_e_m3=dens_c,
            t_e_k=temp_c,
            volume_m3=vc,
            internal_energy_j=u_c,
            tau_e_s=cfg.plasma.confinement_time_s,
            confinement_factor=cfg.plasma.confinement_factor,
            enabled_bremsstrahlung=cfg.losses.bremsstrahlung,
            enabled_transport=cfg.losses.transport,
            enabled_wall=cfg.losses.wall,
            enabled_exhaust=cfg.losses.exhaust,
            wall_loss_coeff_s=wall_coeff,
            exhaust_loss_coeff_s=cfg.losses.exhaust_loss_coeff_s,
            z_eff=z_eff,
            anisotropic_transport=cfg.losses.anisotropic_transport,
            tau_parallel_s=cfg.losses.tau_parallel_s,
            tau_perp_s=cfg.losses.tau_perp_s,
        )
        # Small losses on branches
        temp_a = _temperature_from_energy(n_a, u_a, va_vol)
        temp_b = _temperature_from_energy(n_b, u_b, vb_vol)
        losses_a = compute_zone_losses(
            n_e_m3=dens_a,
            t_e_k=temp_a,
            volume_m3=va_vol,
            internal_energy_j=u_a,
            tau_e_s=cfg.plasma.confinement_time_s,
            confinement_factor=cfg.plasma.confinement_factor,
            enabled_bremsstrahlung=cfg.losses.bremsstrahlung,
            enabled_transport=False,
            enabled_wall=False,
            enabled_exhaust=False,
            wall_loss_coeff_s=0.0,
            exhaust_loss_coeff_s=0.0,
            z_eff=z_eff,
        )
        losses_b = compute_zone_losses(
            n_e_m3=dens_b,
            t_e_k=temp_b,
            volume_m3=vb_vol,
            internal_energy_j=u_b,
            tau_e_s=cfg.plasma.confinement_time_s,
            confinement_factor=cfg.plasma.confinement_factor,
            enabled_bremsstrahlung=cfg.losses.bremsstrahlung,
            enabled_transport=False,
            enabled_wall=False,
            enabled_exhaust=False,
            wall_loss_coeff_s=0.0,
            exhaust_loss_coeff_s=0.0,
            z_eff=z_eff,
        )

        p_rad = losses_a.bremsstrahlung_w + losses_b.bremsstrahlung_w + losses_c.bremsstrahlung_w
        p_trans = losses_c.transport_w
        p_wall = losses_c.wall_w
        p_exh = losses_c.exhaust_w
        p_rec = cfg.losses.recovery_fraction * p_exh

        # External / synthetic heat
        p_ext = self._control.external_heater_w
        p_syn = cfg.drive.synthetic_heat_w
        if cfg.drive.synthetic_heat_modulation_hz > 0.0:
            p_syn += cfg.drive.synthetic_heat_modulation_amp * math.sin(
                2.0 * math.pi * cfg.drive.synthetic_heat_modulation_hz * t
            )
            p_syn = max(p_syn, 0.0)

        # Particle ODEs
        dydt[IDX_N_A] = rate_r_to_a - rate_a_to_c
        dydt[IDX_N_B] = rate_r_to_b - rate_b_to_c
        dydt[IDX_N_C] = rate_a_to_c + rate_b_to_c - rate_c_to_r - 2.0 * r_fusion + fuel
        dydt[IDX_N_R] = rate_c_to_r - rate_r_to_a - rate_r_to_b
        dydt[IDX_N_HE_C] = r_fusion + he_source - n_he * 0.01  # weak removal placeholder

        # Energy carry with particles (specific energy u/n)
        def carry(n: float, u: float, rate: float) -> float:
            if n <= 1e-12:
                return 0.0
            return (u / n) * rate

        # Branch energy
        dydt[IDX_U_A] = (
            carry(n_r, u_r, rate_r_to_a) - carry(n_a, u_a, rate_a_to_c) - losses_a.bremsstrahlung_w
        )
        dydt[IDX_U_B] = (
            carry(n_r, u_r, rate_r_to_b) - carry(n_b, u_b, rate_b_to_c) - losses_b.bremsstrahlung_w
        )
        # Branch bremsstrahlung already removed from U_a/U_b; chamber loses only its own radiation.
        dydt[IDX_U_C] = (
            carry(n_a, u_a, rate_a_to_c)
            + carry(n_b, u_b, rate_b_to_c)
            - carry(n_c, u_c, rate_c_to_r)
            + p_alpha
            + p_ext
            + p_syn
            + p_rec
            - losses_c.bremsstrahlung_w
            - p_trans
            - p_wall
            - p_exh
        )
        dydt[IDX_U_R] = (
            carry(n_c, u_c, rate_c_to_r)
            - carry(n_r, u_r, rate_r_to_a)
            - carry(n_r, u_r, rate_r_to_b)
        )

        # Magnetic nozzle (lumped: chamber is the extraction proxy)
        from ouroboros.physics.nozzle import magnetic_nozzle_powers

        from ouroboros.physics.nozzle_config import nozzle_kwargs

        nz = magnetic_nozzle_powers(
            **nozzle_kwargs(
                cfg.nozzle,
                n_particles=n_c,
                internal_energy_j=u_c,
                mean_particle_mass_kg=cfg.plasma.mean_particle_mass_kg,
                enabled=cfg.nozzle.enabled,
                ion_temperature_k=temp_c,
            )
        )
        dydt[IDX_N_C] -= nz.particle_rate_s
        dydt[IDX_U_C] -= nz.thermal_extract_w

        # Flow dynamics + throttles (Milestone 8 coupling modes)
        ra = cfg.throttle_a.resistance_ohm
        rb = cfg.throttle_b.resistance_ohm
        if cfg.faults.force_quench_a or self.throttle_a.status == ThrottleStatus.QUENCH:
            ra = max(ra, cfg.throttle_a.quench_resistance_ohm)
            self.throttle_a.status = ThrottleStatus.QUENCH
        if cfg.faults.force_quench_b or self.throttle_b.status == ThrottleStatus.QUENCH:
            rb = max(rb, cfg.throttle_b.quench_resistance_ohm)
            self.throttle_b.status = ThrottleStatus.QUENCH

        from ouroboros.core.dynamics import dual_path_throttle_step

        temp_a = _temperature_from_energy(n_a, u_a, va_vol)
        temp_b = _temperature_from_energy(n_b, u_b, vb_vol)
        vr = cfg.geometry.return_channel_volume_m3
        dens_r = n_r / max(vr, 1e-30)
        temp_r = _temperature_from_energy(n_r, u_r, vr)
        p_a = pressure_pa(dens_a, temp_a, dens_a, temp_a)
        p_b = pressure_pa(dens_b, temp_b, dens_b, temp_b)
        p_c = pressure_pa(dens_c, temp_c, dens_c, temp_c)
        p_r = pressure_pa(dens_r, temp_r, dens_r, temp_r)

        step = dual_path_throttle_step(
            cfg=cfg,
            v_a=v_a,
            v_b=v_b,
            i_a=i_a,
            i_b=i_b,
            dens_a=dens_a,
            dens_b=dens_b,
            resistance_a=ra,
            resistance_b=rb,
            p_a_pa=p_a,
            p_b_pa=p_b,
            p_c_pa=p_c,
            p_r_pa=p_r,
        )
        da, db = step.path_a, step.path_b
        dydt[IDX_V_A] = da.dv_dt
        dydt[IDX_V_B] = db.dv_dt
        dydt[IDX_I_A] = da.dI_dt
        dydt[IDX_I_B] = db.dI_dt
        dydt[IDX_U_C] += step.plasma_heating_w

        p_friction = cfg.plasma.friction_coeff_kg_s * (v_a * v_a + v_b * v_b) + step.dissipative_power_w
        p_drive_work = cfg.drive.drive_force_a_n * v_a + cfg.drive.drive_force_b_n * v_b

        # Limit checks
        self.throttle_a.current_a = i_a
        self.throttle_b.current_a = i_b
        for th, lim_i, lim_b in [
            (self.throttle_a, cfg.throttle_a.current_limit_a, cfg.throttle_a.field_limit_t),
            (self.throttle_b, cfg.throttle_b.current_limit_a, cfg.throttle_b.field_limit_t),
        ]:
            if abs(th.current_a) > lim_i or th.estimated_field_t() > lim_b:
                th.status = ThrottleStatus.LIMITING
            if abs(th.current_a) > 1.2 * lim_i or th.estimated_field_t() > 1.2 * lim_b:
                if th.status != ThrottleStatus.QUENCH:
                    self.events.append(
                        SimulationEvent(
                            t,
                            "quench",
                            f"{th.name} quench threshold exceeded",
                            EventSeverity.ERROR,
                        )
                    )
                th.status = ThrottleStatus.QUENCH

        # Soft current limiter for numerical safety (does not silently fix negatives of plasma state)
        if abs(i_a) > 1e8 or abs(i_b) > 1e8:
            msg = f"Throttle current overflow at t={t}: Ia={i_a}, Ib={i_b}"
            self.events.append(SimulationEvent(t, "current_overflow", msg, EventSeverity.CRITICAL))
            self._aborted = True
            raise NonPhysicalStateError(msg)

        p_mag_loss = 0.0
        if cfg.losses.magnetic:
            p_mag_loss = da.ohmic_power_w + db.ohmic_power_w
            if p_mag_loss == float("inf"):
                raise NonPhysicalStateError(f"Magnetic loss overflow at t={t}")

        # Magnetic ohmic comes from magnetic energy / is dissipation — track as loss.
        # Kinetic/magnetic exchange via mutual terms is internal to state energy.

        # Accumulator derivatives for ledger + blanket channel
        from ouroboros.core.blanket_integration import apply_blanket_ode

        dEb, d_legacy, d_leak, d_cool, bpow = apply_blanket_ode(
            cfg=cfg, neutron_power_w=p_neut, e_blanket_j=float(y[IDX_E_BLANKET])
        )
        dydt[IDX_E_BLANKET] = dEb
        dydt[IDX_ACC_EXT] = p_ext + p_syn
        dydt[IDX_ACC_FUS] = p_fusion
        dydt[IDX_ACC_ALPHA] = p_alpha
        dydt[IDX_ACC_NEUT] = p_neut  # produced
        dydt[IDX_ACC_NEUT_LEAK] = d_leak
        dydt[IDX_ACC_COOLANT] = d_cool
        # When blanket off, legacy instant neutron output uses ACC_NEUT via ledger mapping;
        # d_legacy equals p_neut and is informational only (ACC_NEUT already tracks it).
        _ = d_legacy
        dydt[IDX_ACC_RAD] = p_rad
        dydt[IDX_ACC_TRANS] = p_trans
        dydt[IDX_ACC_WALL] = p_wall
        dydt[IDX_ACC_EXH] = p_exh + nz.waste_power_w
        dydt[IDX_ACC_MAGLOSS] = p_mag_loss
        dydt[IDX_ACC_REC] = p_rec
        dydt[IDX_ACC_FRICTION] = p_friction
        dydt[IDX_ACC_DRIVE] = p_drive_work
        dydt[IDX_ACC_THRUST] = nz.jet_power_w

        q = p_fusion / p_ext if p_ext > 1e-12 else float("nan")
        self._last_diag = InstantDiagnostics(
            fusion_power_w=p_fusion,
            alpha_power_w=p_alpha,
            neutron_power_w=p_neut,
            external_power_w=p_ext + p_syn,
            loss_power_w=p_rad + p_trans + p_wall + p_exh * (1.0 - cfg.losses.recovery_fraction),
            recovered_power_w=p_rec,
            q_factor=q,
            controller_meta={
                **dict(self._control.metadata),
                "blanket_coolant_w": bpow.coolant_extract_w,
                "neutron_leak_w": bpow.leaked_w,
                "mhd_dissipative_w": step.dissipative_power_w,
                "mhd_plasma_heating_w": step.plasma_heating_w,
                "mhd_force_a_n": step.mhd.force_a_n,
                "mhd_force_b_n": step.mhd.force_b_n,
                "thrust_n": nz.thrust_n,
                "isp_s": nz.isp_s,
                "jet_power_w": nz.jet_power_w,
                "nozzle_mass_flow_kg_s": nz.mass_flow_kg_s,
            },
        )
        return dydt

    def ledger_from_state(self, y: np.ndarray) -> EnergyLedger:
        cfg = self.config
        m_eff = cfg.plasma.effective_inertia_kg
        from ouroboros.core.blanket_integration import fill_neutron_ledger_fields

        ledger = EnergyLedger(
            e_internal_j=float(y[IDX_U_A] + y[IDX_U_B] + y[IDX_U_C] + y[IDX_U_R]),
            e_kinetic_j=0.5 * m_eff * (float(y[IDX_V_A]) ** 2 + float(y[IDX_V_B]) ** 2),
            e_magnetic_j=(
                0.5 * cfg.throttle_a.inductance_h * float(y[IDX_I_A]) ** 2
                + 0.5 * cfg.throttle_b.inductance_h * float(y[IDX_I_B]) ** 2
            ),
            e_external_input_j=float(y[IDX_ACC_EXT]),
            e_fusion_total_j=float(y[IDX_ACC_FUS]),
            e_alpha_to_plasma_j=float(y[IDX_ACC_ALPHA]),
            e_recovered_j=float(y[IDX_ACC_REC]),
            e_radiation_j=float(y[IDX_ACC_RAD]),
            e_transport_j=float(y[IDX_ACC_TRANS]),
            e_wall_j=float(y[IDX_ACC_WALL]),
            e_exhaust_j=float(y[IDX_ACC_EXH]),
            e_magnetic_loss_j=float(y[IDX_ACC_MAGLOSS]),
            e_friction_j=float(y[IDX_ACC_FRICTION]),
            e_drive_work_j=float(y[IDX_ACC_DRIVE]),
            e_thrust_j=float(y[IDX_ACC_THRUST]),
            e_state_initial_j=self.e_state_initial,
        )
        fill_neutron_ledger_fields(
            ledger,
            cfg=cfg,
            e_blanket_j=float(y[IDX_E_BLANKET]),
            acc_neut_produced_j=float(y[IDX_ACC_NEUT]),
            acc_neut_legacy_out_j=float(y[IDX_ACC_NEUT]),
            acc_leak_j=float(y[IDX_ACC_NEUT_LEAK]),
            acc_coolant_j=float(y[IDX_ACC_COOLANT]),
        )
        ledger.compute_residual()
        ledger.relative_error(cfg.energy.absolute_floor_j)
        if ledger.relative_residual > cfg.energy.relative_tolerance:
            ledger.trusted = False
            self._energy_trusted = False
        return ledger

    def sample_series(self, t: float, y: np.ndarray) -> dict[str, float]:
        from ouroboros.units import kelvin_to_ev

        cfg = self.config
        ledger = self.ledger_from_state(y)
        dens_a = float(y[IDX_N_A]) / cfg.geometry.branch_a_volume_m3
        dens_b = float(y[IDX_N_B]) / cfg.geometry.branch_b_volume_m3
        dens_c = float(y[IDX_N_C]) / cfg.geometry.chamber_volume_m3
        ta = _temperature_from_energy(
            float(y[IDX_N_A]), float(y[IDX_U_A]), cfg.geometry.branch_a_volume_m3
        )
        tb = _temperature_from_energy(
            float(y[IDX_N_B]), float(y[IDX_U_B]), cfg.geometry.branch_b_volume_m3
        )
        tc = _temperature_from_energy(
            float(y[IDX_N_C]), float(y[IDX_U_C]), cfg.geometry.chamber_volume_m3
        )
        rho_a = dens_a * cfg.plasma.mean_particle_mass_kg
        rho_b = dens_b * cfg.plasma.mean_particle_mass_kg
        A = cfg.geometry.branch_cross_section_m2
        diag = self._last_diag
        return {
            "density_a": dens_a,
            "density_b": dens_b,
            "density_chamber": dens_c,
            "temp_a_ev": kelvin_to_ev(ta),
            "temp_b_ev": kelvin_to_ev(tb),
            "temp_chamber_ev": kelvin_to_ev(tc),
            "flow_a": float(y[IDX_V_A]),
            "flow_b": float(y[IDX_V_B]),
            "mass_flow_a": rho_a * A * float(y[IDX_V_A]),
            "mass_flow_b": rho_b * A * float(y[IDX_V_B]),
            "current_throttle_a": float(y[IDX_I_A]),
            "current_throttle_b": float(y[IDX_I_B]),
            "magnetic_energy": ledger.e_magnetic_j,
            "fusion_power_w": diag.fusion_power_w,
            "alpha_power_w": diag.alpha_power_w,
            "neutron_power_w": diag.neutron_power_w,
            "external_power_w": diag.external_power_w,
            "loss_power_w": diag.loss_power_w,
            "recovered_power_w": diag.recovered_power_w,
            "wall_energy_j": ledger.e_wall_j,
            "q_factor": diag.q_factor,
            "energy_residual_j": ledger.e_error_j,
            "energy_residual_rel": ledger.relative_residual,
            "controller_heater_w": self._control.external_heater_w,
            "internal_energy_total_j": ledger.e_internal_j,
            "kinetic_energy_j": ledger.e_kinetic_j,
            "blanket_energy_j": ledger.e_blanket_j,
            "blanket_coolant_power_w": float(diag.controller_meta.get("blanket_coolant_w", 0.0)),
            "neutron_leak_power_w": float(diag.controller_meta.get("neutron_leak_w", 0.0)),
            "thrust_n": float(diag.controller_meta.get("thrust_n", 0.0)),
            "isp_s": float(diag.controller_meta.get("isp_s", 0.0)),
            "jet_power_w": float(diag.controller_meta.get("jet_power_w", 0.0)),
            "nozzle_mass_flow_kg_s": float(diag.controller_meta.get("nozzle_mass_flow_kg_s", 0.0)),
        }

    def check_energy_or_raise(self, y: np.ndarray, t: float) -> EnergyLedger:
        ledger = self.ledger_from_state(y)
        if not ledger.trusted:
            msg = (
                f"Energy residual {ledger.relative_residual:.3e} exceeds "
                f"tolerance {self.config.energy.relative_tolerance} at t={t}"
            )
            self.events.append(SimulationEvent(t, "energy_balance", msg, EventSeverity.WARNING))
            if self.config.simulation.strict_energy or self.config.faults.trip_energy_balance:
                self._aborted = True
                raise EnergyBalanceError(msg)
        return ledger
