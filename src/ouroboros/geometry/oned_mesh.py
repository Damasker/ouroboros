"""1D mesh built on top of the multi-zone loop network."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ouroboros.domain.config import SimulationConfig
from ouroboros.geometry.network import (
    ZoneNetwork,
    build_zone_network,
    load_geometry,
)


@dataclass
class Cell:
    """Single finite-volume cell along a segment centerline."""

    global_index: int
    zone_id: str
    local_index: int
    volume_m3: float
    length_m: float
    cross_section_m2: float
    path: str | None
    is_chamber: bool
    is_throttle: bool
    throttle_name: str | None


@dataclass
class Face:
    """
    Oriented interface from left_cell → right_cell.
    Positive velocity (path-signed) carries flux left → right.
    """

    left: int
    right: int
    area_m2: float
    path: str
    valve_key: str | None = None
    split_fraction: float = 1.0  # for branching (return → feeds)


@dataclass
class OneDMesh:
    cells: list[Cell]
    faces: list[Face]
    zone_cell_indices: dict[str, list[int]] = field(default_factory=dict)
    chamber_cells: list[int] = field(default_factory=list)
    network: ZoneNetwork | None = None

    @property
    def n_cells(self) -> int:
        return len(self.cells)


def build_oned_mesh(config: SimulationConfig) -> OneDMesh:
    """Discretize each geometry segment into equal cells; connect via network edges."""
    geom = load_geometry(config.oned.geometry_file or config.multizone.geometry_file)
    network = build_zone_network(geom, config)
    n_per = max(int(config.oned.cells_per_segment), 1)

    cells: list[Cell] = []
    zone_cell_indices: dict[str, list[int]] = {}
    chamber_cells: list[int] = []

    for z in network.zones:
        idxs: list[int] = []
        dx = z.length_m / n_per
        dv = z.volume_m3 / n_per
        for j in range(n_per):
            gi = len(cells)
            cells.append(
                Cell(
                    global_index=gi,
                    zone_id=z.id,
                    local_index=j,
                    volume_m3=dv,
                    length_m=dx,
                    cross_section_m2=z.cross_section_m2,
                    path=z.path,
                    is_chamber=z.is_chamber,
                    is_throttle=z.is_throttle,
                    throttle_name=z.throttle_name,
                )
            )
            idxs.append(gi)
            if z.is_chamber:
                chamber_cells.append(gi)
        zone_cell_indices[z.id] = idxs

    faces: list[Face] = []

    # Intra-segment faces (along centerline)
    for z in network.zones:
        idxs = zone_cell_indices[z.id]
        path = z.path or "common"
        for a, b in itertools.pairwise(idxs):
            area = 0.5 * (cells[a].cross_section_m2 + cells[b].cross_section_m2)
            faces.append(Face(left=a, right=b, area_m2=area, path=path))

    # Inter-segment faces from network edges
    for edge in network.edges:
        left_ids = zone_cell_indices[edge.source]
        right_ids = zone_cell_indices[edge.target]
        left = left_ids[-1]
        right = right_ids[0]
        area = 0.5 * (cells[left].cross_section_m2 + cells[right].cross_section_m2)
        split = 0.5 if edge.source == "return_to_split" else 1.0
        faces.append(
            Face(
                left=left,
                right=right,
                area_m2=area,
                path=edge.path,
                valve_key=edge.valve_key,
                split_fraction=split,
            )
        )

    return OneDMesh(
        cells=cells,
        faces=faces,
        zone_cell_indices=zone_cell_indices,
        chamber_cells=chamber_cells,
        network=network,
    )
