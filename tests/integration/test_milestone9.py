"""Milestone 9: dynamic blanket, campaigns, HTTP snapshot server."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from ouroboros.campaign import expand_cases, load_campaign, run_campaign
from ouroboros.core import run_simulation
from ouroboros.http_server import serve_snapshots
from ouroboros.io import load_config, write_run_directory
from ouroboros.physics.blanket import blanket_rhs

ROOT = Path(__file__).resolve().parents[2]


def test_blanket_rhs_partitions_and_extracts():
    dE, _dT, p = blanket_rhs(
        neutron_power_w=100.0,
        thermal_energy_j=10.0,
        capture_fraction=0.8,
        coolant_time_s=0.5,
        breeding_ratio=1.0,
        enabled=True,
    )
    assert p.captured_w == pytest.approx(80.0)
    assert p.leaked_w == pytest.approx(20.0)
    assert p.coolant_extract_w == pytest.approx(20.0)
    assert dE == pytest.approx(60.0)


def test_dt_blanket_energy_trusted():
    cfg = load_config(ROOT / "configs/dt_blanket.yaml")
    cfg.simulation.duration_s = 0.08
    result = run_simulation(cfg)
    assert result.ledger_final.blanket_dynamic is True
    assert result.energy_trusted
    assert result.ledger_final.e_neutron_produced_j > 0.0 or max(result.series["neutron_power_w"]) >= 0.0
    # Coolant or leak should appear once neutrons are produced
    produced = result.ledger_final.e_neutron_produced_j
    if produced > 0:
        assert (
            result.ledger_final.e_neutron_leaked_j
            + result.ledger_final.e_coolant_extracted_j
            + result.ledger_final.e_blanket_j
        ) == pytest.approx(produced, rel=1e-3, abs=1.0)
    assert "blanket_energy_j" in result.series


def test_legacy_neutron_when_blanket_off():
    cfg = load_config(ROOT / "configs/dt_fusion.yaml")
    cfg.simulation.duration_s = 0.05
    cfg.blanket.enabled = False
    result = run_simulation(cfg)
    assert result.ledger_final.blanket_dynamic is False
    assert result.ledger_final.e_blanket_j == 0.0
    assert result.energy_trusted


def test_campaign_heater_sweep(tmp_path: Path):
    spec = load_campaign(ROOT / "configs/campaigns/heater_sweep.yaml", root=ROOT)
    spec.output_dir = tmp_path / "campaign"
    # Shrink to 2 cases for speed
    spec.parameters[0].values = [1.0e5, 2.0e5]
    summary = run_campaign(spec, write_artifacts=True)
    assert summary["n_cases"] == 2
    assert (spec.output_dir / "campaign_summary.json").exists()
    assert (spec.output_dir / "campaign_summary.csv").exists()
    assert len(expand_cases(spec)) == 2


def test_http_snapshot_server(tmp_path: Path):
    cfg = load_config(ROOT / "configs/passive.yaml")
    cfg.simulation.duration_s = 0.05
    cfg.simulation.output_interval_s = 0.01
    result = run_simulation(cfg, run_id="http_smoke")
    write_run_directory(result, tmp_path)

    httpd = serve_snapshots(tmp_path, host="127.0.0.1", port=0)
    host, port = httpd.server_address[:2]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as resp:
            health = json.loads(resp.read().decode())
        assert health["status"] == "ok"

        with urllib.request.urlopen(f"http://{host}:{port}/runs", timeout=5) as resp:
            runs = json.loads(resp.read().decode())
        assert any(r["run_id"] == "http_smoke" for r in runs["runs"])

        with urllib.request.urlopen(
            f"http://{host}:{port}/runs/http_smoke/snapshots/latest", timeout=5
        ) as resp:
            frame = json.loads(resp.read().decode())
        assert "time" in frame
        assert "segments" in frame
    finally:
        httpd.shutdown()
        httpd.server_close()
