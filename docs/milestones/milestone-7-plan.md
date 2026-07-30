# Milestone 7 Plan — 1D Loop Discretization

## Goal

Introduce a conservative 1D discretization along segment centerlines **without breaking** EnergyLedger, snapshot schema, or the `lumped`/`multizone` models.

## Approach

1. Add `simulation.model: oned` dispatcher.
2. Discretize each geometry segment into \(N_c\) cells (config).
3. Advect density/energy with upwind / finite-volume fluxes; reuse dual-path or local velocity field.
4. Reduce 1D fields → segment averages for JSONL snapshots (schema stays v1.0.0; optional `cells` array later with schema bump).
5. Property tests: discrete mass/energy conservation with periodic/closed loop BCs.

## Non-goals

- Full MHD
- Unstructured 2D/3D mesh
- Changing public CLI for existing scenarios
