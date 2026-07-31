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

## Beyond

- Full reduced MHD / cell-local momentum field
- Particle / Monte Carlo neutrons
- 3D visualization client on snapshot API
- Magnetic nozzle / propulsion config (separate product line)
