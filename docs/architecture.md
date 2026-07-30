# Architecture

## Layering

```
┌─────────────────────────────────────────────────────────┐
│  Visualization Layer (matplotlib / future 3D clients)   │
│  - reads only public SimulationResult / snapshots       │
└──────────────────────────▲──────────────────────────────┘
                           │ JSON / CSV / JSONL / API
┌──────────────────────────┴──────────────────────────────┐
│  Data & API Layer                                       │
│  - config load/validate  - export  - step/run control   │
└──────────────────────────▲──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│  Simulation Core                                        │
│  - ODE system  - integrator  - events  - EnergyLedger   │
└──────────────────────────▲──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│  Domain Model + Physics Models + Controllers + Geometry │
└─────────────────────────────────────────────────────────┘
```

## Packages

| Package | Responsibility |
|---------|----------------|
| `ouroboros.units` | SI conversions (eV↔J, MeV, etc.) |
| `ouroboros.domain` | Entities: PlasmaState, branches, chamber, throttles, ledger, config/result |
| `ouroboros.physics` | Fusion, losses, throttle EM model (phenomenological) |
| `ouroboros.core` | ODE RHS (`LoopSystem`, `MultiZoneSystem`), integrator, events |
| `ouroboros.controllers` | NoController, PID, SlowSupervisor |
| `ouroboros.geometry` | Spatial loop + `ZoneNetwork` builder for multi-zone 0D |
| `ouroboros.io` | YAML config, CSV/JSON export, snapshot protocol |
| `ouroboros.api` | Programmatic simulation control surface |
| `ouroboros.viz` | 2D plots and schematic (depends on core **outputs only**) |

## Invariants

1. Simulation Core never imports `matplotlib`, GUI, or game engines.
2. All physical quantities are SI internally; display units convert explicitly.
3. EnergyLedger is updated every accepted step; relative residual above threshold marks the interval untrusted.
4. Geometry exists independently of the 0D equations so 3D clients can bind without touching the RHS.
5. Controllers may only change slow setpoints (heating, fueling, valve coeffs); they do not rewrite state variables directly each micro-step except via those setpoints.

## Data formats

- **YAML** — human-authored simulation configuration.
- **CSV** — columnar time series for analysis and plotting.
- **JSON** — run metadata, energy report, event log summary.
- **JSON Lines (`.jsonl`)** — versioned frame snapshots for external 3D clients.

Rationale: portable, diff-friendly, no binary dependency for v1. HDF5 can be added later for large fields without changing the logical schema.
