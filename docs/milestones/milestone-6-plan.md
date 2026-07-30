# Milestone 6 — Multi-zone 0D

## Goal

Replace the fixed four-zone bookkeeping (A, B, chamber, return) with a **network of lumped zones** derived from the loop geometry, while keeping:

1. strict EnergyLedger closure;
2. the public export / snapshot contract;
3. backward-compatible `lumped` model as default.

## Design

```
geometry segments ──► ZoneNetwork (nodes = zones, edges = exchange)
                              │
                              ▼
                     MultiZoneSystem RHS
                              │
                              ▼
              same integrator / API / JSONL snapshots
```

### Zone roles

| Role | Physics in v1 multi-zone |
|------|--------------------------|
| `branch` / `feed` | particles + energy + optional flow inertia |
| `throttle` | particles + energy; attaches RL throttle current |
| `chamber` | fusion, heater, primary losses |
| `expansion` / `separator` / `return` | particles + energy; return splits to feeds |

### State vector

For `n` zones:

- `N_i`, `U_i` for each zone
- `v_a`, `v_b` path velocities (phenomenological dual-path inertia)
- `I_a`, `I_b` throttle currents
- energy accumulators (same channels as lumped)
- `N_He` in chamber

### Exchange

Adjacent zones exchange particles at rate

\[
\dot N_{i\to j} = \frac{|v_{\mathrm{path}}|}{L_{\mathrm{char}}} N_i \cdot \kappa_{\mathrm{valve}}
\]

with energy carried as specific energy \(U_i/N_i\). Classification: simplified / phenomenological.

### Compatibility

- `simulation.model: lumped` — existing `LoopSystem` (default)
- `simulation.model: multizone` — new `MultiZoneSystem`

## Deliverables

- `ouroboros.core.multizone`
- `ouroboros.geometry.network` zone builder
- config `configs/multizone_passive.yaml`
- tests: particle conservation, energy residual, snapshot segment IDs
- docs update: model, equations, roadmap, report

## Non-goals

- Full 1D advection PDE (Milestone 7)
- MHD
- Changing snapshot schema major version (remain `1.0.0`, extra segment fields ok)
