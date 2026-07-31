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

## Milestone 8 — Reduced / extended physics (next)

- Stronger consistent throttle–flow coupling
- Multi-zone / 1D D–T burn studies
- Optional reduced MHD or anisotropic transport stubs

## Beyond

- Full reduced MHD
- Particle / Monte Carlo neutrons
- Magnetic nozzle / propulsion config (separate product line)
