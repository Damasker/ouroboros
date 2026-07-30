#!/usr/bin/env python3
import sys
import time
from ouroboros.io import load_config, write_run_directory
from ouroboros.core import run_simulation

path = sys.argv[1]
run_id = sys.argv[2] if len(sys.argv) > 2 else None
cfg = load_config(path)
t0 = time.time()
r = run_simulation(cfg, run_id=run_id)
dt = time.time() - t0
print(
    f"OK path={path} run={r.run_id} trusted={r.energy_trusted} "
    f"rel={r.ledger_final.relative_residual:.3e} n={len(r.times_s)} "
    f"fus_max={max(r.series['fusion_power_w']):.3e} time={dt:.2f}s "
    f"success={r.metadata.get('integrator_success')} aborted={r.metadata.get('aborted')}"
)
if run_id:
    out = write_run_directory(r, "results")
    print("wrote", out)
