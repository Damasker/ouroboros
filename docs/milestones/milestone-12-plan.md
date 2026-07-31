# Milestone 12 Plan — Cell-local axial velocity (1D)

## Goals

1. **`oned.momentum_mode: cell_velocity`** — per-cell axial velocity in the 1D state vector.
2. Face-based \(-\nabla p\) forces, distributed friction/drive/throttle coupling.
3. Compressional \(F_i v_i \leftrightarrow U_i\) exchange so the EnergyLedger stays trusted.
4. Advection fluxes use upwind **cell** velocity (not dual-path ODE).

## Non-goals

- Full momentum-flux Riemann solver / shock capturing
- Multi-dimensional MHD / Alfvén waves
- Changing default `dual_path` / `cell_pressure` behaviour

## Classification

Simplified 1D finite-volume momentum on path-oriented cells — still not a validated MHD model.
