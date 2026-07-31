"""Path / cell momentum helpers (Milestones 11–12)."""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.geometry.oned_mesh import OneDMesh


@dataclass(frozen=True)
class PathPressureForces:
    """Integrated Δp·A forces on dual paths + per-cell compressional heating shares."""

    force_a_n: float
    force_b_n: float
    # Heating into cell internal energy [W] (sums to -(F_a v_a + F_b v_b) when applied)
    cell_heating_w: tuple[float, ...]


@dataclass(frozen=True)
class CellPressureForces:
    """Per-cell −∇p forces (Milestone 12) + compressional heating."""

    force_n: tuple[float, ...]
    cell_heating_w: tuple[float, ...]


def path_pressure_forces_from_cells(
    mesh: OneDMesh,
    *,
    pressures_pa: list[float],
    scale: float,
    v_a: float,
    v_b: float,
) -> PathPressureForces:
    """
    Sum face pressure forces along path-a / path-b faces.

    F_face = scale * (p_left - p_right) * A  (positive accelerates left→right).
    Path assignment uses face.path ('a'|'b'|'common').
    Compressional exchange: each face's work F_face * u_path is taken from the two
    adjacent cells equally and returned as cell_heating_w (= −work share).

    Classification: simplified hydro / phenomenological.
    """
    n = mesh.n_cells
    heat = [0.0] * n
    fa = fb = 0.0
    if scale == 0.0:
        return PathPressureForces(0.0, 0.0, tuple(heat))

    for face in mesh.faces:
        p_l = pressures_pa[face.left]
        p_r = pressures_pa[face.right]
        f = scale * (p_l - p_r) * face.area_m2
        path = face.path
        if path == "a":
            fa += f
            u = v_a
        elif path == "b":
            fb += f
            u = v_b
        else:
            fa += 0.5 * f
            fb += 0.5 * f
            u = 0.5 * (v_a + v_b)
        work = f * u
        share = -0.5 * work
        heat[face.left] += share
        heat[face.right] += share

    return PathPressureForces(force_a_n=fa, force_b_n=fb, cell_heating_w=tuple(heat))


def cell_grad_p_forces(
    mesh: OneDMesh,
    *,
    pressures_pa: list[float],
    velocities_m_s: list[float],
    scale: float,
    compressional_exchange: bool,
) -> CellPressureForces:
    """
    Finite-volume −∇p on cells: F_i = scale A (p_{i-1/2} − p_{i+1/2}).

    Face pressure p_f = ½(p_L + p_R). Force on left cell −p_f A, on right +p_f A.
    Compressional heating per cell: −F_i v_i when exchange enabled.

    Classification: simplified 1D hydro.
    """
    n = mesh.n_cells
    forces = [0.0] * n
    if scale == 0.0:
        return CellPressureForces(tuple(forces), tuple(0.0 for _ in range(n)))

    for face in mesh.faces:
        p_face = 0.5 * (pressures_pa[face.left] + pressures_pa[face.right])
        f = scale * p_face * face.area_m2
        forces[face.left] -= f
        forces[face.right] += f

    if compressional_exchange:
        heat = tuple(-forces[i] * velocities_m_s[i] for i in range(n))
    else:
        heat = tuple(0.0 for _ in range(n))
    return CellPressureForces(force_n=tuple(forces), cell_heating_w=heat)


def cell_inertias_kg(mesh: OneDMesh, effective_inertia_kg: float) -> list[float]:
    """Distribute lumped M_eff by cell volume (keeps total inertia = M_eff)."""
    vols = [c.volume_m3 for c in mesh.cells]
    vtot = max(sum(vols), 1e-30)
    m = max(effective_inertia_kg, 1e-30)
    return [m * (v / vtot) for v in vols]


@dataclass(frozen=True)
class MomentumFluxResult:
    """Per-cell dv/dt from upwind momentum flux + optional numerical heating."""

    dv_dt: tuple[float, ...]
    numerical_heating_w: float  # total power to dump into internal energy (≥0)


def upwind_momentum_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    face_speeds_m_s: list[float],
    enabled: bool,
) -> MomentumFluxResult:
    """
    Upwind momentum flux Φ = u_eff * A * (m/V)_up * v_up [kg m/s² = N].

    Updates d(mv)/dt = −∇·(ρ v v); returns dv/dt = (1/m) d(mv)/dt.
    Kinetic power sum m v dv/dt is typically ≤0 (upwind dissipation).

    Classification: simplified FV / phenomenological numerical viscosity.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_speeds_m_s) != len(mesh.faces):
        return MomentumFluxResult(zeros, 0.0)

    d_mom = [0.0] * n
    for face, u_eff in zip(mesh.faces, face_speeds_m_s, strict=True):
        li, ri = face.left, face.right
        if u_eff >= 0.0:
            up = li
        else:
            up = ri
        vol = max(mesh.cells[up].volume_m3, 1e-30)
        rho = masses_kg[up] / vol
        phi = u_eff * face.area_m2 * rho * velocities_m_s[up]
        d_mom[li] -= phi
        d_mom[ri] += phi

    dv = [d_mom[i] / max(masses_kg[i], 1e-30) for i in range(n)]
    p_ke = sum(masses_kg[i] * velocities_m_s[i] * dv[i] for i in range(n))
    heating = max(-p_ke, 0.0)
    return MomentumFluxResult(dv_dt=tuple(dv), numerical_heating_w=heating)


def rusanov_momentum_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    enabled: bool,
) -> MomentumFluxResult:
    """
    Rusanov flux for momentum density: F = ρv² + κp.

    Φ/A = ½(F_L+F_R) − ½ S (ρv_R − ρv_L),  S = max(|v|+c),
    c ≈ √(max(κp/ρ, 0)). face_area_factors multiply A (valve×split).

    Energy exchange: numerical_heating_w = −∑ m v dv (signed; add to ΣU).

    Classification: simplified FV Rusanov / phenomenological.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return MomentumFluxResult(zeros, 0.0)

    kappa = pressure_scale
    d_mom = [0.0] * n
    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = masses_kg[li] / vol_l
        rho_r = masses_kg[ri] / vol_r
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        f_l = rho_l * v_l * v_l + p_l
        f_r = rho_r * v_r * v_r + p_r
        c_l = (max(p_l / max(rho_l, 1e-30), 0.0)) ** 0.5
        c_r = (max(p_r / max(rho_r, 1e-30), 0.0)) ** 0.5
        s_max = max(abs(v_l) + c_l, abs(v_r) + c_r, 1e-12)
        a_eff = face.area_m2 * max(af, 0.0)
        mom_l = rho_l * v_l
        mom_r = rho_r * v_r
        phi = a_eff * (0.5 * (f_l + f_r) - 0.5 * s_max * (mom_r - mom_l))
        d_mom[li] -= phi
        d_mom[ri] += phi

    dv = [d_mom[i] / max(masses_kg[i], 1e-30) for i in range(n)]
    p_ke = sum(masses_kg[i] * velocities_m_s[i] * dv[i] for i in range(n))
    # Full kin↔int exchange for this flux channel
    return MomentumFluxResult(dv_dt=tuple(dv), numerical_heating_w=-p_ke)


def hllc_momentum_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    enabled: bool,
) -> MomentumFluxResult:
    """
    HLLC flux for momentum: F = ρv² + κp (Toro-style star region).

    Wave speeds: S_L = min(v_L−c_L, v_R−c_R), S_R = max(v_L+c_L, v_R+c_R),
    contact S_M from pressure–momentum jump. Sound speed c ≈ √(κp/ρ).

    Energy exchange: numerical_heating_w = −∑ m v dv (signed).

    Classification: simplified HLLC / phenomenological — not full Euler HLLC.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return MomentumFluxResult(zeros, 0.0)

    kappa = pressure_scale
    d_mom = [0.0] * n
    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        c_l = (max(p_l / rho_l, 0.0)) ** 0.5
        c_r = (max(p_r / rho_r, 0.0)) ** 0.5
        s_l = min(v_l - c_l, v_r - c_r)
        s_r = max(v_l + c_l, v_r + c_r)
        # Widen slightly if waves collapse
        if s_r - s_l < 1e-12:
            s_l -= 1e-6
            s_r += 1e-6

        denom = rho_r * (s_r - v_r) - rho_l * (s_l - v_l)
        if abs(denom) < 1e-30:
            s_m = 0.5 * (v_l + v_r)
        else:
            s_m = (
                rho_r * v_r * (s_r - v_r) - rho_l * v_l * (s_l - v_l) + p_l - p_r
            ) / denom

        f_l = rho_l * v_l * v_l + p_l
        f_r = rho_r * v_r * v_r + p_r
        mom_l = rho_l * v_l
        mom_r = rho_r * v_r

        # Star states (density × contact speed)
        if abs(s_l - s_m) < 1e-30:
            mom_star_l = mom_l
        else:
            rho_star_l = rho_l * (s_l - v_l) / (s_l - s_m)
            mom_star_l = rho_star_l * s_m
        if abs(s_r - s_m) < 1e-30:
            mom_star_r = mom_r
        else:
            rho_star_r = rho_r * (s_r - v_r) / (s_r - s_m)
            mom_star_r = rho_star_r * s_m

        if 0.0 <= s_l:
            phi_a = f_l
        elif s_l <= 0.0 <= s_m:
            phi_a = f_l + s_l * (mom_star_l - mom_l)
        elif s_m <= 0.0 <= s_r:
            phi_a = f_r + s_r * (mom_star_r - mom_r)
        else:
            phi_a = f_r

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * phi_a
        d_mom[li] -= phi
        d_mom[ri] += phi

    dv = [d_mom[i] / max(masses_kg[i], 1e-30) for i in range(n)]
    p_ke = sum(masses_kg[i] * velocities_m_s[i] * dv[i] for i in range(n))
    return MomentumFluxResult(dv_dt=tuple(dv), numerical_heating_w=-p_ke)


@dataclass(frozen=True)
class EnergyFluxResult:
    """Per-cell internal-energy rate from Riemann total-energy flux (Milestone 17)."""

    du_dt: tuple[float, ...]  # W into cell U
    # Identity check: sum(du_dt) + sum(m v dv) ≈ 0 on a closed mesh


def rusanov_energy_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    internal_energy_j: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    dv_dt: tuple[float, ...] | list[float],
    enabled: bool,
) -> EnergyFluxResult:
    """
    Rusanov flux for total energy density E = U/V + ½ρv².

    Φ_E/A = ½(F_L+F_R) − ½ S (E_R−E_L),  F = v(E+κp),
    S = max(|v|+c), c ≈ √(κp/ρ).

    Cell internal update: ẊU_i = −(Φ_out−Φ_in) − m_i v_i ẋv_i so that
    total (U+KE) follows the energy flux divergence.

    Classification: simplified Euler LLF / phenomenological — not full HLLC energy.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return EnergyFluxResult(zeros)

    kappa = pressure_scale
    d_e = [0.0] * n
    e_dens = [0.0] * n
    for i in range(n):
        vol = max(mesh.cells[i].volume_m3, 1e-30)
        rho = max(masses_kg[i] / vol, 1e-30)
        e_dens[i] = internal_energy_j[i] / vol + 0.5 * rho * velocities_m_s[i] ** 2

    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        e_l = e_dens[li]
        e_r = e_dens[ri]
        c_l = (max(p_l / rho_l, 0.0)) ** 0.5
        c_r = (max(p_r / rho_r, 0.0)) ** 0.5
        s_max = max(abs(v_l) + c_l, abs(v_r) + c_r, 1e-12)
        f_l = v_l * (e_l + p_l)
        f_r = v_r * (e_r + p_r)
        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * (0.5 * (f_l + f_r) - 0.5 * s_max * (e_r - e_l))
        d_e[li] -= phi
        d_e[ri] += phi

    du = [
        d_e[i] - masses_kg[i] * velocities_m_s[i] * float(dv_dt[i])
        for i in range(n)
    ]
    return EnergyFluxResult(du_dt=tuple(du))


def hllc_energy_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    internal_energy_j: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    dv_dt: tuple[float, ...] | list[float],
    enabled: bool,
) -> EnergyFluxResult:
    """
    HLLC flux for total energy density E = U/V + ½ρv² (Toro star region).

    Wave speeds match hllc_momentum_flux. Star pressure
    p* = p_L + ρ_L (S_L−v_L)(S_M−v_L); star energy
    E*_K = [(S_K−v_K)E_K − p_K v_K + p* S_M] / (S_K−S_M).

    Cell internal update: ẊU_i = −div Φ_E − m_i v_i ẋv_i.

    Classification: simplified HLLC energy / phenomenological — not full Euler/MHD.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return EnergyFluxResult(zeros)

    kappa = pressure_scale
    d_e = [0.0] * n
    e_dens = [0.0] * n
    for i in range(n):
        vol = max(mesh.cells[i].volume_m3, 1e-30)
        rho = max(masses_kg[i] / vol, 1e-30)
        e_dens[i] = internal_energy_j[i] / vol + 0.5 * rho * velocities_m_s[i] ** 2

    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        e_l = e_dens[li]
        e_r = e_dens[ri]
        c_l = (max(p_l / rho_l, 0.0)) ** 0.5
        c_r = (max(p_r / rho_r, 0.0)) ** 0.5
        s_l = min(v_l - c_l, v_r - c_r)
        s_r = max(v_l + c_l, v_r + c_r)
        if s_r - s_l < 1e-12:
            s_l -= 1e-6
            s_r += 1e-6

        denom = rho_r * (s_r - v_r) - rho_l * (s_l - v_l)
        if abs(denom) < 1e-30:
            s_m = 0.5 * (v_l + v_r)
        else:
            s_m = (
                rho_r * v_r * (s_r - v_r) - rho_l * v_l * (s_l - v_l) + p_l - p_r
            ) / denom

        p_star = p_l + rho_l * (s_l - v_l) * (s_m - v_l)

        f_l = v_l * (e_l + p_l)
        f_r = v_r * (e_r + p_r)

        if abs(s_l - s_m) < 1e-30:
            e_star_l = e_l
        else:
            e_star_l = ((s_l - v_l) * e_l - p_l * v_l + p_star * s_m) / (s_l - s_m)
        if abs(s_r - s_m) < 1e-30:
            e_star_r = e_r
        else:
            e_star_r = ((s_r - v_r) * e_r - p_r * v_r + p_star * s_m) / (s_r - s_m)

        if 0.0 <= s_l:
            phi_a = f_l
        elif s_l <= 0.0 <= s_m:
            phi_a = f_l + s_l * (e_star_l - e_l)
        elif s_m <= 0.0 <= s_r:
            phi_a = f_r + s_r * (e_star_r - e_r)
        else:
            phi_a = f_r

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * phi_a
        d_e[li] -= phi
        d_e[ri] += phi

    du = [
        d_e[i] - masses_kg[i] * velocities_m_s[i] * float(dv_dt[i])
        for i in range(n)
    ]
    return EnergyFluxResult(du_dt=tuple(du))


def roe_momentum_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    enabled: bool,
) -> MomentumFluxResult:
    """
    Roe approximate Riemann flux for momentum: F = ρv² + κp.

    Roe averages ρ̃=√(ρ_L ρ_R), ṽ weighted by √ρ; c̃=√(κp̃/ρ̃).
    Two-wave dissipation on [ρ, ρv] (isothermal-like).

    Classification: simplified Roe / phenomenological — not full Euler Roe/MHD.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return MomentumFluxResult(zeros, 0.0)

    kappa = pressure_scale
    d_mom = [0.0] * n
    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        f_l = rho_l * v_l * v_l + p_l
        f_r = rho_r * v_r * v_r + p_r

        w_l = rho_l**0.5
        w_r = rho_r**0.5
        w_sum = w_l + w_r
        rho_roe = w_l * w_r
        v_roe = (w_l * v_l + w_r * v_r) / w_sum
        p_roe = 0.5 * (p_l + p_r)
        c_roe = (max(p_roe / max(rho_roe, 1e-30), 0.0)) ** 0.5
        c_roe = max(c_roe, 1e-12)

        d_rho = rho_r - rho_l
        d_mom_face = rho_r * v_r - rho_l * v_l
        # α for right eigenvectors r1=[1,v-c], r2=[1,v+c]
        a1 = ((v_roe + c_roe) * d_rho - d_mom_face) / (2.0 * c_roe)
        a2 = (-(v_roe - c_roe) * d_rho + d_mom_face) / (2.0 * c_roe)
        lam1 = abs(v_roe - c_roe)
        lam2 = abs(v_roe + c_roe)
        diss = 0.5 * (lam1 * a1 * (v_roe - c_roe) + lam2 * a2 * (v_roe + c_roe))

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * (0.5 * (f_l + f_r) - diss)
        d_mom[li] -= phi
        d_mom[ri] += phi

    dv = [d_mom[i] / max(masses_kg[i], 1e-30) for i in range(n)]
    p_ke = sum(masses_kg[i] * velocities_m_s[i] * dv[i] for i in range(n))
    return MomentumFluxResult(dv_dt=tuple(dv), numerical_heating_w=-p_ke)


def roe_energy_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    internal_energy_j: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    dv_dt: tuple[float, ...] | list[float],
    enabled: bool,
) -> EnergyFluxResult:
    """
    Roe flux for total energy density E = U/V + ½ρv², F_E = v(E+κp).

    Uses same Roe averages as roe_momentum_flux; dissipates on ΔE with |ṽ|±c̃.

    Classification: simplified Roe energy — not full Euler Roe/entropy fix.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return EnergyFluxResult(zeros)

    kappa = pressure_scale
    d_e = [0.0] * n
    e_dens = [0.0] * n
    for i in range(n):
        vol = max(mesh.cells[i].volume_m3, 1e-30)
        rho = max(masses_kg[i] / vol, 1e-30)
        e_dens[i] = internal_energy_j[i] / vol + 0.5 * rho * velocities_m_s[i] ** 2

    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li]
        p_r = kappa * pressures_pa[ri]
        e_l = e_dens[li]
        e_r = e_dens[ri]
        f_l = v_l * (e_l + p_l)
        f_r = v_r * (e_r + p_r)

        w_l = rho_l**0.5
        w_r = rho_r**0.5
        w_sum = w_l + w_r
        rho_roe = w_l * w_r
        v_roe = (w_l * v_l + w_r * v_r) / w_sum
        p_roe = 0.5 * (p_l + p_r)
        c_roe = max((max(p_roe / max(rho_roe, 1e-30), 0.0)) ** 0.5, 1e-12)

        d_rho = rho_r - rho_l
        d_mom_face = rho_r * v_r - rho_l * v_l
        d_e_face = e_r - e_l
        a1 = ((v_roe + c_roe) * d_rho - d_mom_face) / (2.0 * c_roe)
        a2 = (-(v_roe - c_roe) * d_rho + d_mom_face) / (2.0 * c_roe)
        # Energy eigenvector weights: approximate with enthalpy-like projection
        h_l = (e_l + p_l) / rho_l
        h_r = (e_r + p_r) / rho_r
        h_roe = (w_l * h_l + w_r * h_r) / w_sum
        # Dissipate ΔE with acoustic + contact-ish |v| mode residual
        a_e = d_e_face - a1 * (h_roe - v_roe * c_roe) - a2 * (h_roe + v_roe * c_roe)
        diss = 0.5 * (
            abs(v_roe - c_roe) * a1 * (h_roe - v_roe * c_roe)
            + abs(v_roe + c_roe) * a2 * (h_roe + v_roe * c_roe)
            + abs(v_roe) * a_e
        )

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * (0.5 * (f_l + f_r) - diss)
        d_e[li] -= phi
        d_e[ri] += phi

    du = [
        d_e[i] - masses_kg[i] * velocities_m_s[i] * float(dv_dt[i])
        for i in range(n)
    ]
    return EnergyFluxResult(du_dt=tuple(du))


def hlld_momentum_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    magnetic_pressures_pa: list[float] | None = None,
    enabled: bool,
) -> MomentumFluxResult:
    """
    Simplified HLLD-like momentum flux with fast / Alfvén / contact waves.

    Total pressure p_t = κp + p_mag. Fast speed c_f = √(c_s² + v_A²),
    Alfvén speed v_A = √(p_mag/ρ). Star region uses contact S_M like HLLC
    with p_t^*; Alfvén intermediate states blend momenta.

    Classification: phenomenological HLLD proxy — not Miyoshi–Kusano MHD HLLD.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return MomentumFluxResult(zeros, 0.0)

    kappa = pressure_scale
    pmag = magnetic_pressures_pa or [0.0] * n
    d_mom = [0.0] * n
    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li] + max(pmag[li], 0.0)
        p_r = kappa * pressures_pa[ri] + max(pmag[ri], 0.0)
        va_l = (max(pmag[li], 0.0) / rho_l) ** 0.5
        va_r = (max(pmag[ri], 0.0) / rho_r) ** 0.5
        cs_l = (max(kappa * pressures_pa[li] / rho_l, 0.0)) ** 0.5
        cs_r = (max(kappa * pressures_pa[ri] / rho_r, 0.0)) ** 0.5
        cf_l = (cs_l * cs_l + va_l * va_l) ** 0.5
        cf_r = (cs_r * cs_r + va_r * va_r) ** 0.5

        s_l = min(v_l - cf_l, v_r - cf_r)
        s_r = max(v_l + cf_l, v_r + cf_r)
        if s_r - s_l < 1e-12:
            s_l -= 1e-6
            s_r += 1e-6

        denom = rho_r * (s_r - v_r) - rho_l * (s_l - v_l)
        if abs(denom) < 1e-30:
            s_m = 0.5 * (v_l + v_r)
        else:
            s_m = (
                rho_r * v_r * (s_r - v_r) - rho_l * v_l * (s_l - v_l) + p_l - p_r
            ) / denom

        # Alfvén waves in star region
        s_al = s_m - max(0.5 * (va_l + va_r), 1e-12)
        s_ar = s_m + max(0.5 * (va_l + va_r), 1e-12)

        f_l = rho_l * v_l * v_l + p_l
        f_r = rho_r * v_r * v_r + p_r
        mom_l = rho_l * v_l
        mom_r = rho_r * v_r

        if abs(s_l - s_m) < 1e-30:
            mom_star_l = mom_l
        else:
            rho_star_l = rho_l * (s_l - v_l) / (s_l - s_m)
            mom_star_l = rho_star_l * s_m
        if abs(s_r - s_m) < 1e-30:
            mom_star_r = mom_r
        else:
            rho_star_r = rho_r * (s_r - v_r) / (s_r - s_m)
            mom_star_r = rho_star_r * s_m

        # Intermediate Alfvén states: blend toward contact momentum
        mom_al = 0.5 * (mom_star_l + rho_l * s_m)
        mom_ar = 0.5 * (mom_star_r + rho_r * s_m)

        if 0.0 <= s_l:
            phi_a = f_l
        elif s_l <= 0.0 <= s_al:
            phi_a = f_l + s_l * (mom_star_l - mom_l)
        elif s_al <= 0.0 <= s_m:
            phi_a = f_l + s_l * (mom_star_l - mom_l) + s_al * (mom_al - mom_star_l)
        elif s_m <= 0.0 <= s_ar:
            phi_a = f_r + s_r * (mom_star_r - mom_r) + s_ar * (mom_ar - mom_star_r)
        elif s_ar <= 0.0 <= s_r:
            phi_a = f_r + s_r * (mom_star_r - mom_r)
        else:
            phi_a = f_r

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * phi_a
        d_mom[li] -= phi
        d_mom[ri] += phi

    dv = [d_mom[i] / max(masses_kg[i], 1e-30) for i in range(n)]
    p_ke = sum(masses_kg[i] * velocities_m_s[i] * dv[i] for i in range(n))
    return MomentumFluxResult(dv_dt=tuple(dv), numerical_heating_w=-p_ke)


def hlld_energy_flux(
    mesh: OneDMesh,
    *,
    masses_kg: list[float],
    velocities_m_s: list[float],
    pressures_pa: list[float],
    internal_energy_j: list[float],
    face_area_factors: list[float],
    pressure_scale: float,
    dv_dt: tuple[float, ...] | list[float],
    magnetic_pressures_pa: list[float] | None = None,
    enabled: bool,
) -> EnergyFluxResult:
    """
    HLLD-like energy flux using fast/Alfvén/contact speeds from hlld_momentum_flux.

    E includes magnetic: E = U/V + ½ρv² + p_mag. F_E = v(E + p_t).

    Classification: phenomenological HLLD energy proxy.
    """
    n = mesh.n_cells
    zeros = tuple(0.0 for _ in range(n))
    if not enabled or len(face_area_factors) != len(mesh.faces):
        return EnergyFluxResult(zeros)

    kappa = pressure_scale
    pmag = magnetic_pressures_pa or [0.0] * n
    d_e = [0.0] * n
    e_dens = [0.0] * n
    for i in range(n):
        vol = max(mesh.cells[i].volume_m3, 1e-30)
        rho = max(masses_kg[i] / vol, 1e-30)
        e_dens[i] = (
            internal_energy_j[i] / vol
            + 0.5 * rho * velocities_m_s[i] ** 2
            + max(pmag[i], 0.0)
        )

    for face, af in zip(mesh.faces, face_area_factors, strict=True):
        li, ri = face.left, face.right
        vol_l = max(mesh.cells[li].volume_m3, 1e-30)
        vol_r = max(mesh.cells[ri].volume_m3, 1e-30)
        rho_l = max(masses_kg[li] / vol_l, 1e-30)
        rho_r = max(masses_kg[ri] / vol_r, 1e-30)
        v_l = velocities_m_s[li]
        v_r = velocities_m_s[ri]
        p_l = kappa * pressures_pa[li] + max(pmag[li], 0.0)
        p_r = kappa * pressures_pa[ri] + max(pmag[ri], 0.0)
        e_l = e_dens[li]
        e_r = e_dens[ri]
        va_l = (max(pmag[li], 0.0) / rho_l) ** 0.5
        va_r = (max(pmag[ri], 0.0) / rho_r) ** 0.5
        cs_l = (max(kappa * pressures_pa[li] / rho_l, 0.0)) ** 0.5
        cs_r = (max(kappa * pressures_pa[ri] / rho_r, 0.0)) ** 0.5
        cf_l = (cs_l * cs_l + va_l * va_l) ** 0.5
        cf_r = (cs_r * cs_r + va_r * va_r) ** 0.5
        s_l = min(v_l - cf_l, v_r - cf_r)
        s_r = max(v_l + cf_l, v_r + cf_r)
        if s_r - s_l < 1e-12:
            s_l -= 1e-6
            s_r += 1e-6
        denom = rho_r * (s_r - v_r) - rho_l * (s_l - v_l)
        if abs(denom) < 1e-30:
            s_m = 0.5 * (v_l + v_r)
        else:
            s_m = (
                rho_r * v_r * (s_r - v_r) - rho_l * v_l * (s_l - v_l) + p_l - p_r
            ) / denom
        s_al = s_m - max(0.5 * (va_l + va_r), 1e-12)
        s_ar = s_m + max(0.5 * (va_l + va_r), 1e-12)
        p_star = p_l + rho_l * (s_l - v_l) * (s_m - v_l)
        f_l = v_l * (e_l + p_l)
        f_r = v_r * (e_r + p_r)
        if abs(s_l - s_m) < 1e-30:
            e_star_l = e_l
        else:
            e_star_l = ((s_l - v_l) * e_l - p_l * v_l + p_star * s_m) / (s_l - s_m)
        if abs(s_r - s_m) < 1e-30:
            e_star_r = e_r
        else:
            e_star_r = ((s_r - v_r) * e_r - p_r * v_r + p_star * s_m) / (s_r - s_m)
        e_al = 0.5 * (e_star_l + e_l)
        e_ar = 0.5 * (e_star_r + e_r)

        if 0.0 <= s_l:
            phi_a = f_l
        elif s_l <= 0.0 <= s_al:
            phi_a = f_l + s_l * (e_star_l - e_l)
        elif s_al <= 0.0 <= s_m:
            phi_a = f_l + s_l * (e_star_l - e_l) + s_al * (e_al - e_star_l)
        elif s_m <= 0.0 <= s_ar:
            phi_a = f_r + s_r * (e_star_r - e_r) + s_ar * (e_ar - e_star_r)
        elif s_ar <= 0.0 <= s_r:
            phi_a = f_r + s_r * (e_star_r - e_r)
        else:
            phi_a = f_r

        a_eff = face.area_m2 * max(af, 0.0)
        phi = a_eff * phi_a
        d_e[li] -= phi
        d_e[ri] += phi

    du = [
        d_e[i] - masses_kg[i] * velocities_m_s[i] * float(dv_dt[i])
        for i in range(n)
    ]
    return EnergyFluxResult(du_dt=tuple(du))
