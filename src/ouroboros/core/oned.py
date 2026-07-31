"""1D finite-volume plasma loop model (Milestone 7)."""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from ouroboros.controllers import (
    Controller,
    ControlSensors,
    ControlSignals,
    build_controller,
)
from ouroboros.core.exceptions import EnergyBalanceError, NonPhysicalStateError
from ouroboros.core.system import InstantDiagnostics, _temperature_from_energy
from ouroboros.domain import (
    EnergyLedger,
    EventSeverity,
    MagneticThrottle,
    SimulationEvent,
    ThrottleStatus,
)
from ouroboros.domain.config import SimulationConfig
from ouroboros.geometry.oned_mesh import build_oned_mesh
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


class OneDLayout:
    """State layout: [N_0,U_0,...,N_{nc-1},U_{nc-1}, v_a,v_b,I_a,I_b, acc..., N_He]."""

    def __init__(self, n_cells: int) -> None:
        self.n_cells = n_cells
        base = 2 * n_cells
        self.idx_v_a = base
        self.idx_v_b = base + 1
        self.idx_i_a = base + 2
        self.idx_i_b = base + 3
        acc0 = base + 4
        self.idx_acc_ext = acc0
        self.idx_acc_fus = acc0 + 1
        self.idx_acc_alpha = acc0 + 2
        self.idx_acc_neut = acc0 + 3
        self.idx_acc_rad = acc0 + 4
        self.idx_acc_trans = acc0 + 5
        self.idx_acc_wall = acc0 + 6
        self.idx_acc_exh = acc0 + 7
        self.idx_acc_magloss = acc0 + 8
        self.idx_acc_rec = acc0 + 9
        self.idx_acc_friction = acc0 + 10
        self.idx_acc_drive = acc0 + 11
        self.idx_n_he = acc0 + 12
        self.idx_e_blanket = acc0 + 13
        self.idx_acc_neut_leak = acc0 + 14
        self.idx_acc_coolant = acc0 + 15
        self.n_state = acc0 + 16

    def idx_n(self, i: int) -> int:
        return 2 * i

    def idx_u(self, i: int) -> int:
        return 2 * i + 1


class OneDSystem:
    """
    Conservative 1D finite-volume model along segment centerlines.

    Classification: simplified physics (upwind advection of N and U; dual-path velocity ODEs).
    """

    def __init__(self, config: SimulationConfig, controller: Controller | None = None) -> None:
        self.config = config
        self.controller = controller or build_controller(
            config.controller.type, config.controller.parameters
        )
        self.reactivity = get_reactivity_model(config.fusion.reactivity_model)
        self.mesh = build_oned_mesh(config)
        self.layout = OneDLayout(self.mesh.n_cells)
        self.events: list[SimulationEvent] = []
        self._control = ControlSignals(
            external_heater_w=config.drive.external_heater_w,
            fueling_rate_s=config.drive.fueling_rate_s,
        )
        self._last_diag = InstantDiagnostics()
        self._aborted = False
        self._energy_trusted = True
        self.e_state_initial = 0.0

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
        y = np.zeros(self.layout.n_state, dtype=float)
        L = self.layout
        for cell in self.mesh.cells:
            dens = n0
            if cell.path == "a" and cfg.faults.density_spike_factor != 1.0:
                dens *= cfg.faults.density_spike_factor
            N = dens * cell.volume_m3
            U = thermal_energy_joule(dens, ti, dens, te, cell.volume_m3)
            y[L.idx_n(cell.global_index)] = N
            y[L.idx_u(cell.global_index)] = U
        y[L.idx_v_a] = cfg.plasma.initial_flow_a_m_s
        y[L.idx_v_b] = cfg.plasma.initial_flow_b_m_s
        y[L.idx_i_a] = cfg.throttle_a.initial_current_a
        y[L.idx_i_b] = cfg.throttle_b.initial_current_a
        if self.mesh.chamber_cells:
            n_ch = sum(float(y[L.idx_n(i)]) for i in self.mesh.chamber_cells)
            y[L.idx_n_he] = cfg.plasma.helium_fraction * n_ch
        y[L.idx_e_blanket] = cfg.blanket.initial_thermal_energy_j if cfg.blanket.enabled else 0.0
        self.e_state_initial = self._state_energy(y)
        return y

    def _state_energy(self, y: np.ndarray) -> float:
        cfg = self.config
        L = self.layout
        e_int = float(sum(y[L.idx_u(i)] for i in range(L.n_cells)))
        m_eff = cfg.plasma.effective_inertia_kg
        e_kin = 0.5 * m_eff * (float(y[L.idx_v_a]) ** 2 + float(y[L.idx_v_b]) ** 2)
        e_mag = 0.5 * cfg.throttle_a.inductance_h * float(y[L.idx_i_a]) ** 2
        e_mag += 0.5 * cfg.throttle_b.inductance_h * float(y[L.idx_i_b]) ** 2
        e_bl = float(y[L.idx_e_blanket]) if cfg.blanket.enabled else 0.0
        return e_int + e_kin + e_mag + e_bl

    def _path_velocity(self, path: str, v_a: float, v_b: float) -> float:
        """Signed speed along an oriented face (positive = left→right)."""
        if path == "a":
            return v_a
        if path == "b":
            return v_b
        return 0.5 * (v_a + v_b)

    def rhs(self, t: float, y: np.ndarray) -> np.ndarray:
        if self._aborted:
            return np.zeros_like(y)

        cfg = self.config
        L = self.layout
        mesh = self.mesh
        dydt = np.zeros_like(y)

        v_a = float(y[L.idx_v_a])
        v_b = float(y[L.idx_v_b])
        i_a = float(y[L.idx_i_a])
        i_b = float(y[L.idx_i_b])

        Ns = np.array([float(y[L.idx_n(i)]) for i in range(L.n_cells)])
        Us = np.array([float(y[L.idx_u(i)]) for i in range(L.n_cells)])
        if np.any(Ns < -1e-6) or np.any(Us < -1e-6):
            msg = f"Non-physical negative 1D state at t={t}"
            self.events.append(SimulationEvent(t, "nonphysical", msg, EventSeverity.CRITICAL))
            self._aborted = True
            raise NonPhysicalStateError(msg)

        dens = np.array([Ns[i] / mesh.cells[i].volume_m3 for i in range(L.n_cells)])
        temps = np.array(
            [
                _temperature_from_energy(Ns[i], Us[i], mesh.cells[i].volume_m3)
                for i in range(L.n_cells)
            ]
        )

        # Chamber aggregates
        ch_cells = mesh.chamber_cells
        if ch_cells:
            n_ch = float(sum(Ns[i] for i in ch_cells))
            u_ch = float(sum(Us[i] for i in ch_cells))
            v_ch = float(sum(mesh.cells[i].volume_m3 for i in ch_cells))
            dens_c = n_ch / v_ch
            temp_c = _temperature_from_energy(n_ch, u_ch, v_ch)
        else:
            n_ch = dens_c = temp_c = 0.0
            v_ch = 1.0

        t_ceil = ev_to_kelvin(cfg.numerics.max_temperature_ev)
        if temp_c > t_ceil or dens_c > cfg.numerics.max_density_m3:
            msg = f"Numerical safety limit exceeded at t={t}"
            self.events.append(SimulationEvent(t, "numerics_limit", msg, EventSeverity.CRITICAL))
            self._aborted = True
            raise NonPhysicalStateError(msg)

        def mean_zone_density(zid: str) -> float:
            idxs = mesh.zone_cell_indices.get(zid, [])
            if not idxs:
                return dens_c
            return float(sum(dens[i] for i in idxs) / len(idxs))

        dens_a = mean_zone_density("branch_a")
        dens_b = mean_zone_density("branch_b")

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
        valve_a = 0.0 if cfg.faults.branch_a_blocked else self._control.valve_coeff_a
        valve_b = 0.0 if cfg.faults.branch_b_blocked else self._control.valve_coeff_b

        dN = np.zeros(L.n_cells)
        dU = np.zeros(L.n_cells)

        # Upwind finite-volume fluxes
        for face in mesh.faces:
            u = self._path_velocity(face.path, v_a, v_b)
            valve = 1.0
            if face.valve_key == "a":
                valve = valve_a
            elif face.valve_key == "b":
                valve = valve_b
            u_eff = u * valve * face.split_fraction
            li, ri = face.left, face.right
            if u_eff >= 0.0:
                n_up = dens[li]
                e_spec = Us[li] / max(Ns[li], 1e-30)  # J per particle
            else:
                n_up = dens[ri]
                e_spec = Us[ri] / max(Ns[ri], 1e-30)
            # Particle number flux [1/s] through face
            phi_n = u_eff * face.area_m2 * n_up
            phi_e = phi_n * e_spec
            dN[li] -= phi_n
            dN[ri] += phi_n
            dU[li] -= phi_e
            dU[ri] += phi_e

        # Fusion + fueling in chamber cells (uniform share)
        n_he = float(y[L.idx_n_he])
        f_d = max(cfg.plasma.deuterium_fraction * (1.0 - n_he / max(n_ch, 1.0)), 0.0)
        f_t = max(cfg.plasma.tritium_fraction * (1.0 - n_he / max(n_ch, 1.0)), 0.0)
        r_fusion = p_fusion = p_alpha = p_neut = 0.0
        if cfg.fusion.enabled and ch_cells:
            r_fusion = fusion_rate_per_second(
                dens_c * f_d, dens_c * f_t, v_ch, temp_c, self.reactivity
            )
            p_fusion = r_fusion * DT_FUSION_TOTAL_J
            p_alpha = r_fusion * DT_ALPHA_J
            p_neut = r_fusion * DT_NEUTRON_J
        fuel = self._control.fueling_rate_s
        if ch_cells:
            share = 1.0 / len(ch_cells)
            for ci in ch_cells:
                dN[ci] += share * (fuel - 2.0 * r_fusion)
        dydt[L.idx_n_he] = r_fusion + cfg.faults.helium_source_rate_s - n_he * 0.01

        # Losses
        wall_coeff = 0.0 if cfg.faults.cooling_loss else cfg.losses.wall_loss_coeff_s
        p_rad = p_trans = p_wall = p_exh = 0.0
        for i, cell in enumerate(mesh.cells):
            if cell.is_chamber:
                losses = compute_zone_losses(
                    n_e_m3=dens[i],
                    t_e_k=temps[i],
                    volume_m3=cell.volume_m3,
                    internal_energy_j=float(Us[i]),
                    tau_e_s=cfg.plasma.confinement_time_s,
                    confinement_factor=cfg.plasma.confinement_factor,
                    enabled_bremsstrahlung=cfg.losses.bremsstrahlung,
                    enabled_transport=cfg.losses.transport,
                    enabled_wall=cfg.losses.wall,
                    enabled_exhaust=cfg.losses.exhaust,
                    wall_loss_coeff_s=wall_coeff,
                    exhaust_loss_coeff_s=cfg.losses.exhaust_loss_coeff_s,
                    z_eff=cfg.losses.impurity_z_eff,
                    anisotropic_transport=cfg.losses.anisotropic_transport,
                    tau_parallel_s=cfg.losses.tau_parallel_s,
                    tau_perp_s=cfg.losses.tau_perp_s,
                )
                p_rad += losses.bremsstrahlung_w
                p_trans += losses.transport_w
                p_wall += losses.wall_w
                p_exh += losses.exhaust_w
                dU[i] -= (
                    losses.bremsstrahlung_w + losses.transport_w + losses.wall_w + losses.exhaust_w
                )
            elif cfg.losses.bremsstrahlung:
                losses = compute_zone_losses(
                    n_e_m3=dens[i],
                    t_e_k=temps[i],
                    volume_m3=cell.volume_m3,
                    internal_energy_j=float(Us[i]),
                    tau_e_s=cfg.plasma.confinement_time_s,
                    confinement_factor=cfg.plasma.confinement_factor,
                    enabled_bremsstrahlung=True,
                    enabled_transport=False,
                    enabled_wall=False,
                    enabled_exhaust=False,
                    wall_loss_coeff_s=0.0,
                    exhaust_loss_coeff_s=0.0,
                    z_eff=cfg.losses.impurity_z_eff,
                )
                p_rad += losses.bremsstrahlung_w
                dU[i] -= losses.bremsstrahlung_w

        p_rec = cfg.losses.recovery_fraction * p_exh
        p_ext = self._control.external_heater_w
        p_syn = cfg.drive.synthetic_heat_w
        if cfg.drive.synthetic_heat_modulation_hz > 0.0:
            p_syn += cfg.drive.synthetic_heat_modulation_amp * math.sin(
                2.0 * math.pi * cfg.drive.synthetic_heat_modulation_hz * t
            )
            p_syn = max(p_syn, 0.0)
        heat = p_alpha + p_ext + p_syn + p_rec
        if ch_cells:
            share = heat / len(ch_cells)
            for ci in ch_cells:
                dU[ci] += share

        for i in range(L.n_cells):
            dydt[L.idx_n(i)] = float(dN[i])
            dydt[L.idx_u(i)] = float(dU[i])

        # Momentum / throttles (Milestone 8 coupling modes)
        ra = cfg.throttle_a.resistance_ohm
        rb = cfg.throttle_b.resistance_ohm
        if cfg.faults.force_quench_a or self.throttle_a.status == ThrottleStatus.QUENCH:
            ra = max(ra, cfg.throttle_a.quench_resistance_ohm)
            self.throttle_a.status = ThrottleStatus.QUENCH
        if cfg.faults.force_quench_b or self.throttle_b.status == ThrottleStatus.QUENCH:
            rb = max(rb, cfg.throttle_b.quench_resistance_ohm)
            self.throttle_b.status = ThrottleStatus.QUENCH

        from ouroboros.core.dynamics import dual_path_throttle_step

        def zone_pressure(zid: str, fallback: float) -> float:
            dens_z, temp_ev = self._zone_mean(y, zid)
            if dens_z <= 0.0:
                return fallback
            t_k = ev_to_kelvin(temp_ev)
            return pressure_pa(dens_z, t_k, dens_z, t_k)

        p_c = pressure_pa(dens_c, temp_c, dens_c, temp_c) if dens_c > 0 else 0.0
        p_a = zone_pressure("branch_a", p_c)
        p_b = zone_pressure("branch_b", p_c)
        p_r = zone_pressure("return_channel", p_c)

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
        dydt[L.idx_v_a] = da.dv_dt
        dydt[L.idx_v_b] = db.dv_dt
        dydt[L.idx_i_a] = da.dI_dt
        dydt[L.idx_i_b] = db.dI_dt
        if ch_cells and step.plasma_heating_w != 0.0:
            share = step.plasma_heating_w / len(ch_cells)
            for ci in ch_cells:
                dydt[L.idx_u(ci)] += share
        if abs(i_a) > 1e8 or abs(i_b) > 1e8:
            raise NonPhysicalStateError(f"Throttle current overflow at t={t}")

        p_mag_loss = (da.ohmic_power_w + db.ohmic_power_w) if cfg.losses.magnetic else 0.0
        p_friction = (
            cfg.plasma.friction_coeff_kg_s * (v_a * v_a + v_b * v_b) + step.dissipative_power_w
        )
        p_drive_work = cfg.drive.drive_force_a_n * v_a + cfg.drive.drive_force_b_n * v_b

        dydt[L.idx_acc_ext] = p_ext + p_syn
        dydt[L.idx_acc_fus] = p_fusion
        dydt[L.idx_acc_alpha] = p_alpha
        dydt[L.idx_acc_neut] = p_neut
        from ouroboros.core.blanket_integration import apply_blanket_ode

        dEb, _d_legacy, d_leak, d_cool, bpow = apply_blanket_ode(
            cfg=cfg, neutron_power_w=p_neut, e_blanket_j=float(y[L.idx_e_blanket])
        )
        dydt[L.idx_e_blanket] = dEb
        dydt[L.idx_acc_neut_leak] = d_leak
        dydt[L.idx_acc_coolant] = d_cool
        dydt[L.idx_acc_rad] = p_rad
        dydt[L.idx_acc_trans] = p_trans
        dydt[L.idx_acc_wall] = p_wall
        dydt[L.idx_acc_exh] = p_exh
        dydt[L.idx_acc_magloss] = p_mag_loss
        dydt[L.idx_acc_rec] = p_rec
        dydt[L.idx_acc_friction] = p_friction
        dydt[L.idx_acc_drive] = p_drive_work

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
            },
        )
        return dydt

    def ledger_from_state(self, y: np.ndarray) -> EnergyLedger:
        cfg = self.config
        L = self.layout
        m_eff = cfg.plasma.effective_inertia_kg
        from ouroboros.core.blanket_integration import fill_neutron_ledger_fields

        ledger = EnergyLedger(
            e_internal_j=float(sum(y[L.idx_u(i)] for i in range(L.n_cells))),
            e_kinetic_j=0.5 * m_eff * (float(y[L.idx_v_a]) ** 2 + float(y[L.idx_v_b]) ** 2),
            e_magnetic_j=(
                0.5 * cfg.throttle_a.inductance_h * float(y[L.idx_i_a]) ** 2
                + 0.5 * cfg.throttle_b.inductance_h * float(y[L.idx_i_b]) ** 2
            ),
            e_external_input_j=float(y[L.idx_acc_ext]),
            e_fusion_total_j=float(y[L.idx_acc_fus]),
            e_alpha_to_plasma_j=float(y[L.idx_acc_alpha]),
            e_recovered_j=float(y[L.idx_acc_rec]),
            e_radiation_j=float(y[L.idx_acc_rad]),
            e_transport_j=float(y[L.idx_acc_trans]),
            e_wall_j=float(y[L.idx_acc_wall]),
            e_exhaust_j=float(y[L.idx_acc_exh]),
            e_magnetic_loss_j=float(y[L.idx_acc_magloss]),
            e_friction_j=float(y[L.idx_acc_friction]),
            e_drive_work_j=float(y[L.idx_acc_drive]),
            e_state_initial_j=self.e_state_initial,
        )
        fill_neutron_ledger_fields(
            ledger,
            cfg=cfg,
            e_blanket_j=float(y[L.idx_e_blanket]),
            acc_neut_produced_j=float(y[L.idx_acc_neut]),
            acc_neut_legacy_out_j=float(y[L.idx_acc_neut]),
            acc_leak_j=float(y[L.idx_acc_neut_leak]),
            acc_coolant_j=float(y[L.idx_acc_coolant]),
        )
        ledger.compute_residual()
        ledger.relative_error(cfg.energy.absolute_floor_j)
        if ledger.relative_residual > cfg.energy.relative_tolerance:
            ledger.trusted = False
            self._energy_trusted = False
        return ledger

    def _zone_mean(self, y: np.ndarray, zid: str) -> tuple[float, float]:
        idxs = self.mesh.zone_cell_indices.get(zid, [])
        if not idxs:
            return 0.0, 0.0
        L = self.layout
        n_sum = u_sum = v_sum = 0.0
        for i in idxs:
            n_sum += float(y[L.idx_n(i)])
            u_sum += float(y[L.idx_u(i)])
            v_sum += self.mesh.cells[i].volume_m3
        dens = n_sum / v_sum
        temp = kelvin_to_ev(_temperature_from_energy(n_sum, u_sum, v_sum))
        return dens, temp

    def sample_series(self, t: float, y: np.ndarray) -> dict[str, float]:
        cfg = self.config
        L = self.layout
        ledger = self.ledger_from_state(y)
        dens_a, temp_a = self._zone_mean(y, "branch_a")
        dens_b, temp_b = self._zone_mean(y, "branch_b")
        dens_c, temp_c = self._zone_mean(y, "reaction_chamber")
        A = cfg.geometry.branch_cross_section_m2
        m = cfg.plasma.mean_particle_mass_kg
        v_a = float(y[L.idx_v_a])
        v_b = float(y[L.idx_v_b])
        diag = self._last_diag
        out: dict[str, float] = {
            "density_a": dens_a,
            "density_b": dens_b,
            "density_chamber": dens_c,
            "temp_a_ev": temp_a,
            "temp_b_ev": temp_b,
            "temp_chamber_ev": temp_c,
            "flow_a": v_a,
            "flow_b": v_b,
            "mass_flow_a": dens_a * m * A * v_a,
            "mass_flow_b": dens_b * m * A * v_b,
            "current_throttle_a": float(y[L.idx_i_a]),
            "current_throttle_b": float(y[L.idx_i_b]),
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
            "n_cells": float(L.n_cells),
        }
        for zid in self.mesh.zone_cell_indices:
            dens, temp = self._zone_mean(y, zid)
            out[f"zone_density:{zid}"] = dens
            out[f"zone_temp_ev:{zid}"] = temp
        # Optional per-cell series (kept modest: density only for chamber + branches)
        for zid in ("branch_a", "branch_b", "reaction_chamber"):
            for i in self.mesh.zone_cell_indices.get(zid, []):
                cell = self.mesh.cells[i]
                n = float(y[L.idx_n(i)])
                out[f"cell_density:{zid}:{cell.local_index}"] = n / cell.volume_m3
        return out

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

    def zone_snapshot_segments(self, y: np.ndarray) -> list[dict[str, Any]]:
        L = self.layout
        segs = []
        for zid, idxs in self.mesh.zone_cell_indices.items():
            dens, temp = self._zone_mean(y, zid)
            cell0 = self.mesh.cells[idxs[0]]
            if cell0.path == "a":
                vel = float(y[L.idx_v_a])
            elif cell0.path == "b":
                vel = float(y[L.idx_v_b])
            else:
                vel = 0.5 * (float(y[L.idx_v_a]) + float(y[L.idx_v_b]))
            bfield = 0.0
            if cell0.throttle_name == "throttle_a":
                self.throttle_a.current_a = float(y[L.idx_i_a])
                bfield = self.throttle_a.estimated_field_t()
            elif cell0.throttle_name == "throttle_b":
                self.throttle_b.current_a = float(y[L.idx_i_b])
                bfield = self.throttle_b.estimated_field_t()
            segs.append(
                {
                    "id": zid,
                    "density": dens,
                    "temperature": temp,
                    "flow_velocity": vel,
                    "magnetic_field": bfield,
                }
            )
        return segs

    def cell_snapshot(self, y: np.ndarray) -> list[dict[str, Any]]:
        """Optional per-cell fields for snapshot schema 1.1.0."""
        L = self.layout
        out = []
        for cell in self.mesh.cells:
            n = float(y[L.idx_n(cell.global_index)])
            u = float(y[L.idx_u(cell.global_index)])
            dens = n / cell.volume_m3
            temp = kelvin_to_ev(_temperature_from_energy(n, u, cell.volume_m3))
            if cell.path == "a":
                vel = float(y[L.idx_v_a])
            elif cell.path == "b":
                vel = float(y[L.idx_v_b])
            else:
                vel = 0.5 * (float(y[L.idx_v_a]) + float(y[L.idx_v_b]))
            out.append(
                {
                    "segment_id": cell.zone_id,
                    "local_index": cell.local_index,
                    "density": dens,
                    "temperature": temp,
                    "flow_velocity": vel,
                }
            )
        return out
