# Milestone 1 Plan

## Objectives

Answer whether the scaffolding can:

1. integrate a lumped passive loop ODE,
2. account energy with a measurable residual,
3. run a passive decay scenario reproducibly,
4. pass automated tests.

## Deliverables

- `docs/ADR-001-technology-stack.md` and core docs
- `ouroboros.units` with eV↔J conversions
- Domain dataclasses + Pydantic config
- `EnergyLedger` with residual checks
- SciPy `solve_ivp` wrapper (LSODA/BDF capable)
- Config `configs/passive.yaml`
- Tests: units, energy, particles, serialization, passive integration
- CLI entry via Makefile

## Engineering choices (documented assumptions)

- Python 3.11+ / SciPy LSODA default integrator
- Internal energy \(U = \tfrac{3}{2}(N_i k_B T_i + N_e k_B T_e)\) with \(N_e\approx N_i\) for quasineutral pure DT mix approximation in v1 zones
- Passive scenario: fusion off, friction damps flow, magnetic energy exchanges with kinetic via throttle coupling
