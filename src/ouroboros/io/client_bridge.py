"""Native game-engine client bridge protocol (Milestone 25).

Exports a stable JSON envelope that Godot / Unity clients can poll.
Classification: protocol stub — not a full engine plugin.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "1.0.0"


def build_client_frame(
    *,
    run_id: str,
    time_s: float,
    segments: list[dict[str, Any]],
    components: list[dict[str, Any]] | None = None,
    cells: list[dict[str, Any]] | None = None,
    spacecraft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one engine-client frame (Godot/Unity compatible)."""
    return {
        "protocol": "ouroboros.client",
        "version": PROTOCOL_VERSION,
        "run_id": run_id,
        "time": time_s,
        "segments": segments,
        "components": components or [],
        "cells": cells or [],
        "spacecraft": spacecraft or {},
    }


def write_client_stream(
    frames: list[dict[str, Any]],
    path: Path,
) -> Path:
    """Write JSONL stream for native clients."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for fr in frames:
            f.write(json.dumps(fr, separators=(",", ":")) + "\n")
    return path


def protocol_manifest() -> dict[str, Any]:
    """Static manifest advertised at /client/protocol."""
    return {
        "protocol": "ouroboros.client",
        "version": PROTOCOL_VERSION,
        "endpoints": {
            "health": "/health",
            "protocol": "/client/protocol",
            "stream": "/runs/{id}/client-stream",
            "latest": "/runs/{id}/snapshots/latest",
            "geometry": "/geometry",
        },
        "engines": ["godot4", "unity2022+", "webgpu"],
        "frame_fields": [
            "time",
            "segments",
            "components",
            "cells",
            "spacecraft",
        ],
    }
