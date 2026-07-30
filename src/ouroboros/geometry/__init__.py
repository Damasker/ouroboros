"""Spatial loop geometry for visualization (not used in 0D RHS)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

GEOMETRY_SCHEMA_VERSION = "1.0.0"


@dataclass
class Node:
    id: str
    x: float
    y: float
    z: float


@dataclass
class Segment:
    id: str
    start_node: str
    end_node: str
    radius_m: float
    length_m: float
    element_type: str  # branch, throttle, chamber, expansion, separator, return
    orientation: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])


@dataclass
class LoopGeometry:
    schema_version: str
    nodes: list[Node]
    segments: list[Segment]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nodes": [asdict(n) for n in self.nodes],
            "segments": [asdict(s) for s in self.segments],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def default_loop_geometry() -> LoopGeometry:
    """Simple planar schematic coordinates in metres (illustrative)."""
    nodes = [
        Node("a_in", -2.0, 1.0, 0.0),
        Node("a_throttle", -0.5, 1.0, 0.0),
        Node("chamber_in", 0.0, 0.5, 0.0),
        Node("b_in", -2.0, -1.0, 0.0),
        Node("b_throttle", -0.5, -1.0, 0.0),
        Node("chamber_out", 1.0, 0.0, 0.0),
        Node("expand", 2.0, 0.0, 0.0),
        Node("separator", 3.0, 0.0, 0.0),
        Node("return_mid", 2.0, -2.0, 0.0),
        Node("split", -2.0, -2.0, 0.0),
    ]
    segments = [
        Segment("branch_a", "a_in", "a_throttle", 0.15, 1.5, "branch"),
        Segment("throttle_a", "a_throttle", "chamber_in", 0.12, 1.2, "throttle"),
        Segment("branch_b", "b_in", "b_throttle", 0.15, 1.5, "branch"),
        Segment("throttle_b", "b_throttle", "chamber_in", 0.12, 1.2, "throttle"),
        Segment("reaction_chamber", "chamber_in", "chamber_out", 0.4, 1.0, "chamber"),
        Segment("expansion", "chamber_out", "expand", 0.25, 1.0, "expansion"),
        Segment("separator", "expand", "separator", 0.2, 1.0, "separator"),
        Segment("return_channel", "separator", "return_mid", 0.18, 2.2, "return"),
        Segment("return_to_split", "return_mid", "split", 0.18, 4.0, "return"),
        Segment("feed_a", "split", "a_in", 0.15, 3.0, "branch"),
        Segment("feed_b", "split", "b_in", 0.15, 1.0, "branch"),
    ]
    return LoopGeometry(GEOMETRY_SCHEMA_VERSION, nodes, segments)
