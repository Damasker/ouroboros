"""Milestone 12: cell-local axial velocity."""

from __future__ import annotations

from pathlib import Path

import pytest

from ouroboros.core import run_simulation
from ouroboros.core.oned import OneDSystem
from ouroboros.geometry.oned_mesh import build_oned_mesh
from ouroboros.io import load_config
from ouroboros.physics.momentum import cell_grad_p_forces, cell_inertias_kg

ROOT = Path(__file__).resolve().parents[2]


def test_cell_grad_p_heating_identity():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    pressures = [800.0 + 20.0 * i for i in range(mesh.n_cells)]
    velocities = [10.0 + 0.1 * i for i in range(mesh.n_cells)]
    gpf = cell_grad_p_forces(
        mesh,
        pressures_pa=pressures,
        velocities_m_s=velocities,
        scale=1e-6,
        compressional_exchange=True,
    )
    work = sum(gpf.force_n[i] * velocities[i] for i in range(mesh.n_cells))
    assert sum(gpf.cell_heating_w) == pytest.approx(-work, rel=1e-12, abs=1e-12)


def test_cell_inertias_sum_to_meff():
    cfg = load_config(ROOT / "configs/oned_passive.yaml")
    cfg.oned.cells_per_segment = 2
    mesh = build_oned_mesh(cfg)
    masses = cell_inertias_kg(mesh, 1.0e-4)
    assert sum(masses) == pytest.approx(1.0e-4)


def test_oned_cell_velocity_layout_and_energy():
    cfg = load_config(ROOT / "configs/oned_cell_velocity.yaml")
    cfg.simulation.duration_s = 0.1
    cfg.oned.cells_per_segment = 2
    sys = OneDSystem(cfg)
    assert sys.layout.cell_velocity is True
    y0 = sys.initial_state()
    assert y0.shape == (sys.layout.n_state,)
    # State has V per cell
    assert abs(y0[sys.layout.idx_v(0)]) > 0.0

    result = run_simulation(cfg)
    assert result.metadata.get("model") == "oned"
    assert result.energy_trusted
    assert result.ledger_final.relative_residual < 1e-3
    assert any(k.startswith("cell_velocity:") for k in result.series)
    assert max(abs(x) for x in result.series["flow_a"]) > 0.0
