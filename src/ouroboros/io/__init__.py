"""I/O: configuration, export, snapshots."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

import yaml

from ouroboros.domain import SimulationResult
from ouroboros.domain.config import SimulationConfig

logger = logging.getLogger(__name__)

SNAPSHOT_SCHEMA_VERSION = "1.1.0"
RESULT_FORMAT_VERSION = "1.0.0"


def load_config(path: str | Path) -> SimulationConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise TypeError(f"Config root must be a mapping: {path}")
    return SimulationConfig.model_validate(raw)


def save_config_copy(config: SimulationConfig, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(), f, sort_keys=False)


def export_timeseries_csv(result: SimulationResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["time_s", *result.series.keys()]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, t in enumerate(result.times_s):
            row: dict[str, Any] = {"time_s": t}
            for k, vals in result.series.items():
                row[k] = vals[i] if i < len(vals) else ""
            writer.writerow(row)


def export_energy_report(result: SimulationResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "format_version": RESULT_FORMAT_VERSION,
        "run_id": result.run_id,
        "energy_trusted": result.energy_trusted,
        "ledger": result.ledger_final.to_dict(),
        "metadata": result.metadata,
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def export_events(result: SimulationResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "time_s": e.time_s,
            "kind": e.kind,
            "message": e.message,
            "severity": e.severity.value,
            "data": e.data,
        }
        for e in result.events
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def export_result_json(result: SimulationResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": RESULT_FORMAT_VERSION,
        "run_id": result.run_id,
        "times_s": result.times_s,
        "series": result.series,
        "energy_trusted": result.energy_trusted,
        "ledger_final": result.ledger_final.to_dict(),
        "metadata": result.metadata,
        "config": result.config_dict,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _segments_from_sample(sample: dict[str, float]) -> list[dict[str, Any]]:
    """Build segment list from lumped keys or multizone zone_* series."""
    zone_ids = sorted(
        {k.split("zone_density:", 1)[1] for k in sample if k.startswith("zone_density:")}
    )
    if zone_ids:
        segs = []
        for zid in zone_ids:
            if zid.startswith("branch_a") or zid in ("feed_a", "throttle_a"):
                vel = sample.get("flow_a", 0.0)
            elif zid.startswith("branch_b") or zid in ("feed_b", "throttle_b"):
                vel = sample.get("flow_b", 0.0)
            else:
                vel = 0.5 * (sample.get("flow_a", 0.0) + sample.get("flow_b", 0.0))
            segs.append(
                {
                    "id": zid,
                    "density": sample.get(f"zone_density:{zid}", 0.0),
                    "temperature": sample.get(f"zone_temp_ev:{zid}", 0.0),
                    "flow_velocity": vel,
                    "magnetic_field": 0.0,
                }
            )
        return segs
    return [
        {
            "id": "branch_a",
            "density": sample.get("density_a", 0.0),
            "temperature": sample.get("temp_a_ev", 0.0),
            "flow_velocity": sample.get("flow_a", 0.0),
            "magnetic_field": 0.0,
        },
        {
            "id": "branch_b",
            "density": sample.get("density_b", 0.0),
            "temperature": sample.get("temp_b_ev", 0.0),
            "flow_velocity": sample.get("flow_b", 0.0),
            "magnetic_field": 0.0,
        },
        {
            "id": "reaction_chamber",
            "density": sample.get("density_chamber", 0.0),
            "temperature": sample.get("temp_chamber_ev", 0.0),
            "flow_velocity": 0.0,
            "magnetic_field": 0.0,
        },
        {
            "id": "return_channel",
            "density": 0.5 * (sample.get("density_a", 0.0) + sample.get("density_b", 0.0)),
            "temperature": 0.5 * (sample.get("temp_a_ev", 0.0) + sample.get("temp_b_ev", 0.0)),
            "flow_velocity": 0.5 * (sample.get("flow_a", 0.0) + sample.get("flow_b", 0.0)),
            "magnetic_field": 0.0,
        },
    ]


def build_snapshot_frame(
    time_s: float,
    sample: dict[str, float],
    components_status: dict[str, str],
    segments: list[dict[str, Any]] | None = None,
    cells: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Versioned snapshot for external 3D clients (v1.1.0 adds optional cells)."""
    frame: dict[str, Any] = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "time": time_s,
        "segments": segments if segments is not None else _segments_from_sample(sample),
        "components": [
            {
                "id": "throttle_a",
                "current": sample.get("current_throttle_a", 0.0),
                "stored_energy": 0.5 * sample.get("magnetic_energy", 0.0),
                "status": components_status.get("throttle_a", "normal"),
            },
            {
                "id": "throttle_b",
                "current": sample.get("current_throttle_b", 0.0),
                "stored_energy": 0.5 * sample.get("magnetic_energy", 0.0),
                "status": components_status.get("throttle_b", "normal"),
            },
        ],
    }
    if cells is not None:
        frame["cells"] = cells
    return frame


def export_snapshots_jsonl(result: SimulationResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    final_segs = result.metadata.get("final_zone_segments")
    final_cells = result.metadata.get("final_cells")
    with path.open("w", encoding="utf-8") as f:
        for i, t in enumerate(result.times_s):
            sample = {k: result.series[k][i] for k in result.series}
            segs = _segments_from_sample(sample)
            if len(segs) <= 4 and final_segs and i == len(result.times_s) - 1:
                segs = final_segs
            cells = None
            cell_keys = [k for k in sample if k.startswith("cell_density:")]
            if cell_keys:
                cells = []
                for k in sorted(cell_keys):
                    parts = k.split(":")
                    zid, loc = parts[1], parts[2]
                    flow_key = "flow_a" if "a" in zid else ("flow_b" if "b" in zid else "flow_a")
                    cells.append(
                        {
                            "segment_id": zid,
                            "local_index": int(loc),
                            "density": sample[k],
                            "temperature": sample.get(f"zone_temp_ev:{zid}", 0.0),
                            "flow_velocity": sample.get(flow_key, 0.0),
                        }
                    )
            # Prefer full mesh cell dump on the final frame when available
            if final_cells and i == len(result.times_s) - 1:
                cells = final_cells
            frame = build_snapshot_frame(t, sample, {}, segments=segs, cells=cells)
            f.write(json.dumps(frame) + "\n")


def write_run_directory(result: SimulationResult, root: str | Path) -> Path:
    root = Path(root)
    run_dir = root / result.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    save_config_copy(SimulationConfig.model_validate(result.config_dict), run_dir / "config.yaml")
    export_timeseries_csv(result, run_dir / "timeseries.csv")
    export_energy_report(result, run_dir / "energy_report.json")
    export_events(result, run_dir / "events.json")
    export_result_json(result, run_dir / "result.json")
    export_snapshots_jsonl(result, run_dir / "snapshots.jsonl")
    logger.info("Wrote run artifacts to %s", run_dir)
    return run_dir
