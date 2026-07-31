"""Path momentum helpers from cell pressures (Milestone 11)."""

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
            # Common path: split between A/B
            fa += 0.5 * f
            fb += 0.5 * f
            u = 0.5 * (v_a + v_b)
        # Work done on kinetic by this face force: F * u
        # Remove equally from adjacent cell internal energies.
        work = f * u
        share = -0.5 * work
        heat[face.left] += share
        heat[face.right] += share

    return PathPressureForces(force_a_n=fa, force_b_n=fb, cell_heating_w=tuple(heat))
