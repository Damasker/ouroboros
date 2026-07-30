# Milestone reports

## Milestone 1 — Foundation

**Status:** complete

Implemented: ADR-001 (Python), units module, domain entities, EnergyLedger, SciPy LSODA/BDF wrapper, passive scenario, unit/property/integration tests.

Verified: passive flow decays; relative energy residual ~1e-13 with friction + ohmic channels tracked.

Known issues: 0D only; no spatial transport.

## Milestone 2 — Dual branch + throttles

**Status:** complete

Implemented: branches A/B asymmetry, magnetic throttles (RL + optional mutual), driven/synthetic scenarios, CSV/JSON/JSONL export, matplotlib plots + schematic, `coupled_throttle` demo.

Verified: `make run-scenario` / visualize for passive, driven, synthetic-oscillation, coupled-throttle.

Known issues: mutual inductance + independent `F_mag` are phenomenological and not variationally consistent; default coupling is off; enable only with relaxed residual tolerance.

## Milestone 3 — Fusion channel

**Status:** complete

Implemented: reaction chamber fusion term, Bosch–Hale D–T reactivity, α / neutron partition, Q metric, modular losses.

Verified: `dt-fusion` produces nonzero fusion/α/neutron power; energy residual trusted at modest density (1e18 m⁻³ demo point — not a reactor point).

Known issues: high-density 0D burn runs are stiff and capped by `numerics.max_nfev` / temperature ceiling.

## Milestone 4 — Control & faults

**Status:** complete

Implemented: NoController, PIDController, SlowSupervisorController; fault YAMLs (block, quench, heater trip, helium, density spike, cooling loss); phase portraits; stability report CLI.

## Milestone 5 — External client contract

**Status:** complete

Implemented: `SimulationSession` API, `geometry/loop_geometry.json`, snapshot schema v1.0.0 JSONL, Makefile/Dockerfile/CI, docs/3d-visualization-roadmap.md.
