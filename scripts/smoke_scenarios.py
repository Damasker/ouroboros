#!/usr/bin/env python3
from ouroboros.io import load_config
from ouroboros.core import run_simulation

for path in [
    "configs/driven.yaml",
    "configs/synthetic_oscillation.yaml",
    "configs/dt_fusion.yaml",
    "configs/faults/block_branch_a.yaml",
    "configs/faults/quench.yaml",
]:
    cfg = load_config(path)
    cfg.simulation.duration_s = min(cfg.simulation.duration_s, 0.12)
    cfg.simulation.output_interval_s = max(cfg.simulation.output_interval_s, 0.01)
    r = run_simulation(cfg)
    print(
        path,
        "trusted",
        r.energy_trusted,
        "rel",
        f"{r.ledger_final.relative_residual:.3e}",
        "fus_max",
        max(r.series["fusion_power_w"]),
        "n",
        len(r.times_s),
        "ok",
        r.metadata.get("integrator_success"),
    )
