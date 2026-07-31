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
