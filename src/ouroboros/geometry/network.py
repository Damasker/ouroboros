"""Build a zone network from loop geometry for multi-zone 0D."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ouroboros.domain.config import GeometrySection, SimulationConfig
from ouroboros.geometry import LoopGeometry, Segment, default_loop_geometry


@dataclass
class ZoneDef:
    """One lumped zone mapped from a geometry segment."""

    id: str
    element_type: str
    volume_m3: float
    length_m: float
    radius_m: float
    cross_section_m2: float
    # Which dual-path momentum this zone belongs to: "a", "b", "common", or None
    path: str | None
    is_chamber: bool = False
    is_throttle: bool = False
    throttle_name: str | None = None
    fusion_enabled_here: bool = False


@dataclass
class ExchangeEdge:
    """Directed phenomenological exchange i → j."""

    source: str
    target: str
    path: str  # "a", "b", or "common"
    valve_key: str | None = None  # "a" / "b" if subject to branch valve/block


@dataclass
class ZoneNetwork:
    zones: list[ZoneDef]
    edges: list[ExchangeEdge]
    zone_index: dict[str, int] = field(default_factory=dict)
    chamber_id: str = "reaction_chamber"
    throttle_ids: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.zone_index = {z.id: i for i, z in enumerate(self.zones)}

    @property
    def n_zones(self) -> int:
        return len(self.zones)

    def zone(self, zone_id: str) -> ZoneDef:
        return self.zones[self.zone_index[zone_id]]


def _segment_volume(seg: Segment) -> float:
    import math

    return math.pi * seg.radius_m**2 * seg.length_m


def _assign_path(seg: Segment) -> str | None:
    sid = seg.id
    if sid in ("branch_a", "throttle_a", "feed_a"):
        return "a"
    if sid in ("branch_b", "throttle_b", "feed_b"):
        return "b"
    if seg.element_type in ("chamber", "expansion", "separator", "return"):
        return "common"
    return None


def _scale_volumes(
    raw: dict[str, float],
    geom_cfg: GeometrySection,
) -> dict[str, float]:
    """
    Scale geometric volumes so role groups match config totals.
    Preserves relative sizes inside each role group.
    """
    groups: dict[str, list[str]] = {
        "chamber": [],
        "branch_a": [],
        "branch_b": [],
        "return": [],
        "expansion": [],
        "other": [],
    }
    for sid in raw:
        if sid == "reaction_chamber":
            groups["chamber"].append(sid)
        elif sid in ("branch_a", "feed_a", "throttle_a"):
            groups["branch_a"].append(sid)
        elif sid in ("branch_b", "feed_b", "throttle_b"):
            groups["branch_b"].append(sid)
        elif sid in ("return_channel", "return_to_split"):
            groups["return"].append(sid)
        elif sid in ("expansion", "separator"):
            groups["expansion"].append(sid)
        else:
            groups["other"].append(sid)

    targets = {
        "chamber": geom_cfg.chamber_volume_m3,
        "branch_a": geom_cfg.branch_a_volume_m3,
        "branch_b": geom_cfg.branch_b_volume_m3,
        "return": geom_cfg.return_channel_volume_m3,
        "expansion": geom_cfg.expansion_volume_m3,
    }
    out = dict(raw)
    for gname, ids in groups.items():
        if not ids or gname not in targets:
            continue
        total = sum(raw[i] for i in ids)
        if total <= 0.0:
            continue
        scale = targets[gname] / total
        for i in ids:
            out[i] = raw[i] * scale
    return out


def build_zone_network(
    geometry: LoopGeometry | None = None,
    config: SimulationConfig | None = None,
) -> ZoneNetwork:
    """Construct zones + exchange edges from loop geometry."""
    geometry = geometry or default_loop_geometry()
    config = config or SimulationConfig()

    raw_vol = {s.id: max(_segment_volume(s), 1e-9) for s in geometry.segments}
    volumes = _scale_volumes(raw_vol, config.geometry)

    zones: list[ZoneDef] = []
    throttle_ids: dict[str, str] = {}
    for seg in geometry.segments:
        path = _assign_path(seg)
        is_th = seg.element_type == "throttle" or seg.id.startswith("throttle_")
        is_ch = seg.element_type == "chamber" or seg.id == "reaction_chamber"
        th_name = None
        if is_th:
            th_name = "throttle_a" if path == "a" else "throttle_b"
            throttle_ids[th_name] = seg.id
        area = 3.141592653589793 * seg.radius_m**2
        zones.append(
            ZoneDef(
                id=seg.id,
                element_type=seg.element_type,
                volume_m3=volumes[seg.id],
                length_m=seg.length_m,
                radius_m=seg.radius_m,
                cross_section_m2=area,
                path=path,
                is_chamber=is_ch,
                is_throttle=is_th,
                throttle_name=th_name,
                fusion_enabled_here=is_ch,
            )
        )

    # Topology for default dual-branch loop (explicit, documented).
    # Classification: simplified connectivity for 0D multi-zone.
    edges = [
        ExchangeEdge("feed_a", "branch_a", "a", "a"),
        ExchangeEdge("branch_a", "throttle_a", "a", "a"),
        ExchangeEdge("throttle_a", "reaction_chamber", "a", "a"),
        ExchangeEdge("feed_b", "branch_b", "b", "b"),
        ExchangeEdge("branch_b", "throttle_b", "b", "b"),
        ExchangeEdge("throttle_b", "reaction_chamber", "b", "b"),
        ExchangeEdge("reaction_chamber", "expansion", "common"),
        ExchangeEdge("expansion", "separator", "common"),
        ExchangeEdge("separator", "return_channel", "common"),
        ExchangeEdge("return_channel", "return_to_split", "common"),
        ExchangeEdge("return_to_split", "feed_a", "a"),
        ExchangeEdge("return_to_split", "feed_b", "b"),
    ]

    # Keep only edges whose endpoints exist
    ids = {z.id for z in zones}
    edges = [e for e in edges if e.source in ids and e.target in ids]

    return ZoneNetwork(
        zones=zones,
        edges=edges,
        chamber_id="reaction_chamber",
        throttle_ids=throttle_ids,
    )


def load_geometry(path: str | Path | None) -> LoopGeometry:
    if path is None:
        return default_loop_geometry()
    p = Path(path)
    if not p.exists():
        return default_loop_geometry()
    data = __import__("json").loads(p.read_text(encoding="utf-8"))
    from ouroboros.geometry import Node, Segment

    nodes = [Node(**n) for n in data["nodes"]]
    segments = [Segment(**s) for s in data["segments"]]
    return LoopGeometry(data.get("schema_version", "1.0.0"), nodes, segments)
