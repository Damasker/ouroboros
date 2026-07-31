"""Milestone 11: cell-pressure momentum + snapshot viewer."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.http_server import serve_snapshots
from ouroboros.io import load_config, write_run_directory
from ouroboros.physics.momentum import path_pressure_forces_from_cells

ROOT = Path(__file__).resolve().parents[2]


def test_path_pressure_forces_energy_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    pressures = [1.0e3 + 10.0 * i for i in range(mesh.n_cells)]
    v_a, v_b = 20.0, 15.0
    ppf = path_pressure_forces_from_cells(
        mesh, pressures_pa=pressures, scale=1e-6, v_a=v_a, v_b=v_b
    )
    work = ppf.force_a_n * v_a + ppf.force_b_n * v_b
    assert sum(ppf.cell_heating_w) == pytest.approx(-work, rel=1e-12, abs=1e-12)


def test_oned_cell_momentum_energy_trusted():
    cfg = load_config(ROOT / "configs/oned_cell_momentum.yaml")
    cfg.simulation.duration_s = 0.12
    cfg.oned.cells_per_segment = 2
    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3


def test_viewer_and_geometry_endpoints(tmp_path: Path):
    cfg = load_config(ROOT / "configs/passive.yaml")
    cfg.simulation.duration_s = 0.04
    cfg.simulation.output_interval_s = 0.01
    result = run_simulation(cfg, run_id="viewer_smoke")
    write_run_directory(result, tmp_path)

    httpd = serve_snapshots(
        tmp_path, host="127.0.0.1", port=0, project_root=ROOT, viewer_dir=ROOT / "viewer"
    )
    host, port = httpd.server_address[:2]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{host}:{port}/viewer", timeout=5) as resp:
            html = resp.read().decode()
        assert "Ouroboros" in html
        assert "snapshot viewer" in html.lower()

        with urllib.request.urlopen(f"http://{host}:{port}/geometry", timeout=5) as resp:
            geom = json.loads(resp.read().decode())
        assert "segments" in geom or "nodes" in geom or "elements" in geom or len(geom) > 0

        with urllib.request.urlopen(f"http://{host}:{port}/runs/viewer_smoke/snapshots/latest", timeout=5) as resp:
            frame = json.loads(resp.read().decode())
        assert "segments" in frame
    finally:
        httpd.shutdown()
        httpd.server_close()
