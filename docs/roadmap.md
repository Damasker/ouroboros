# Roadmap

## Milestone 1 — Foundation

- ADR-001 technology stack
- Repository layout, units, domain entities
- Integrator wrapper + EnergyLedger
- Passive circulation scenario
- Unit / property / integration tests

## Milestone 2 — Dual branch dynamics

- Branches A/B with asymmetry
- Magnetic throttles
- External drive
- CSV/JSON export + matplotlib plots

## Milestone 3 — Fusion channel

- Reaction chamber
- Bosch–Hale D–T reactivity
- α-heating + neutron blanket bin
- Q metric + modular losses

## Milestone 4 — Control & faults

- Controller interface (No / PID / SlowSupervisor)
- Fault scenarios
- Phase portraits
- Stability report artifact

## Milestone 5 — External clients

- Simulation API
- Geometry model + snapshot protocol
- Schematic visualization
- Docker / Makefile / CI

See `docs/milestones/REPORT.md` for verification notes.

## Milestone 6 — Multi-zone 0D

- Zone network from loop geometry
- `simulation.model: multizone` dispatcher
- Per-zone series + richer JSONL snapshots
- Passive / driven multizone configs
- Energy ledger closure on the zone network

## Milestone 7 — 1D loop discretization

- `simulation.model: oned`
- Finite-volume cells along segment centerlines
- Upwind advection of \(N\) and \(U\)
- Snapshot schema 1.1.0 with optional `cells`
- Mass/energy conservation tests

## Milestone 8 — Extended physics

- Consistent electromechanical throttle–flow coupling (`coupling_mode: consistent`)
- Anisotropic transport stub (∥/⊥)
- Reduced-MHD placeholder forces
- Multi-zone / 1D D–T burn demo configs

## Milestone 9 — Blanket, campaigns, snapshot server

- Dynamic neutron / blanket thermal channel (`blanket.enabled`)
- Parametric campaign runner (`make campaign`)
- Stdlib HTTP snapshot server (`make serve`)

## Milestone 10 — Energy-consistent reduced MHD

- Split reduced-MHD forces: Alfvén drag (ledger) vs magnetic pressure + \(\Delta p\,A\) (compressional exchange)
- Nonzero `magnetic_pressure_scale` with trusted EnergyLedger when `compressional_exchange: true`
- Demo config `reduced_mhd`

## Milestone 11 — Cell-pressure momentum + snapshot viewer

- `oned.momentum_mode: cell_pressure` — face \(\Delta p\,A\) integrated onto dual paths
- Compressional cell heating for ledger closure
- Browser viewer at `/viewer` (served by `make serve`)

## Milestone 12 — Cell-local axial velocity (1D)

- `oned.momentum_mode: cell_velocity` — per-cell \(V_i\) in the state vector
- Face \(-\nabla p\) forces, distributed friction / drive / throttle coupling
- Advection uses cell velocities; config `oned_cell_velocity`

## Beyond

- Momentum-flux Riemann / wave MHD
- Particle / Monte Carlo neutrons
- Game-engine (Godot/Unity) / WebGPU volumetric client
- Magnetic nozzle / propulsion config (separate product line)
