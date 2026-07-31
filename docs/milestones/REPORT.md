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

## Milestone 6 — Multi-zone 0D

**Status:** complete

Implemented: `ZoneNetwork` from geometry, `MultiZoneSystem`, `simulation.model` dispatcher (`lumped`|`multizone`), configs `multizone_passive` / `multizone_driven`, per-zone series, multi-segment snapshots, zone profile plot.

Verified: particle conservation without sources; energy residual within tolerance on passive multizone; snapshots contain ≥8 segment IDs.

Known issues: exchange rates remain phenomenological (`|v|/L`); dual-path velocities are still two ODEs (not a full 1D field); 1D advection deferred to Milestone 7.

## Milestone 7 — 1D discretization

**Status:** complete

Implemented: `OneDMesh` / `OneDSystem`, upwind FV fluxes, `simulation.model: oned`, configs `oned_passive` / `oned_driven`, snapshot schema **1.1.0** with optional `cells`, cell density plots, conservation tests.

Verified: closed-loop particle conservation; energy residual trusted on passive 1D; snapshots include segment averages + cells.

Known issues: velocity is still dual-path ODE (not a cell-local momentum field); CFL limited by SciPy adaptive stepping; high \(N_c\) increases stiffness.

## Milestone 8 — Extended physics

**Status:** complete

Implemented: consistent EM coupling (`F=-kI`, \(L I'+RI=-kv\)), anisotropic transport stub, reduced-MHD placeholder forces, configs `coupled_consistent` / `multizone_dt` / `oned_dt`, shared `dual_path_throttle_step`.

Verified: coupling power identity residual ~0; consistent-coupling passive residual trusted; multizone/1D DT demos produce nonzero fusion power.

Known issues: reduced-MHD terms are placeholders; magnetic-pressure scale left at 0 by default to protect the ledger.

## Milestone 9 — Blanket, campaigns, snapshot server

**Status:** complete

Implemented: dynamic blanket ODE (`physics/blanket.py`) with capture/leak/coolant + TBR stub; `EnergyLedger` state bin + residual mapping; wired into lumped / multizone / 1D; config `dt_blanket`; campaign runner (`ouroboros campaign`) with Cartesian sweeps + summary CSV/JSON; stdlib HTTP snapshot server (`ouroboros serve`) for 3D clients.

Verified: dynamic-blanket energy closure (produced ≈ leak + coolant + \(E_b\)); legacy path unchanged when blanket off; campaign + HTTP smoke tests.

Known issues: TBR is a placeholder rate, not inventory transport; HTTP server is read-only and unauthenticated.

## Milestone 10 — Energy-consistent reduced MHD

**Status:** complete

Implemented: force-channel split in `physics/reduced_mhd.py` (Alfvén drag → friction ledger; magnetic-pressure stiffness + hydrodynamic \(\Delta p\,A\) → chamber internal energy via compressional exchange); `DualPathStep` return type; wired into lumped / multizone / 1D; config `reduced_mhd`.

Verified: energy residual trusted with nonzero `magnetic_pressure_scale` when `compressional_exchange: true`; unit tests for force signs and exchange identity.

Known issues: still not a real MHD solver (no waves, no cell-local \(\mathbf{v}\)); pressure drive is lumped phenomenological.

## Milestone 11 — Cell-pressure momentum + snapshot viewer

**Status:** complete

Implemented: `physics/momentum.py` face \(\Delta p\,A\) → path forces with per-cell compressional heating; `oned.momentum_mode: cell_pressure`; config `oned_cell_momentum`; HTML canvas viewer under `viewer/` served at `/viewer` plus `/geometry` endpoint.

Verified: cell-pressure heating identity \(\sum P_{\mathrm{heat}}=-(F_a v_a+F_b v_b)\); 1D energy trusted; viewer + geometry HTTP smoke tests.

Known issues: path velocities remain two ODEs (not per-cell \(v\)); viewer is a 2D schematic, not a full 3D client.

## Milestone 12 — Cell-local axial velocity

**Status:** complete

Implemented: `OneDLayout` cell-velocity packing \((N,U,V)\) per cell; FV \(-\nabla p\) via face pressures; mass-weighted path means for throttle EMF; distributed friction/drive/magnetic force; compressional \(F_i v_i\leftrightarrow U_i\); config `oned_cell_velocity`.

Verified: heating identity; inertia partition; short 1D run energy-trusted with `cell_velocity:*` series.

Known issues: no momentum advection / Riemann fluxes; chamber/return cells lack path-throttle forces by design.
