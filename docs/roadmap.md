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

## Milestone 13 — Magnetic nozzle / thrust channel

- Phenomenological nozzle extract from expansion zone (chamber proxy in lumped)
- Ledger `e_thrust_j` + waste→exhaust; series thrust / I_sp / jet power
- Config `magnetic_nozzle`

## Milestone 14 — Upwind momentum flux (1D)

- `oned.momentum_flux` on `cell_velocity`: \(\Phi=u A\rho_{\mathrm{up}}v_{\mathrm{up}}\)
- Thermalize upwind KE sink into cell \(U\) (`thermalize_momentum_flux`)
- Config `oned_momentum_flux`

## Milestone 15 — Rusanov Riemann fluxes

- `oned.riemann: rusanov` — Local Lax–Friedrichs flux with \(\rho v^2+\kappa p\)
- Replaces separate \(\nabla p\) + upwind momentum flux when enabled
- Config `oned_rusanov`

## Milestone 16 — HLLC Riemann fluxes

- `oned.riemann: hllc` — Toro-style HLLC on \(F=\rho v^2+\kappa p\) with contact \(S_M\)
- Same kin↔int exchange / double-count avoidance as Rusanov
- Config `oned_hllc`

## Milestone 17 — Riemann total-energy flux

- `oned.riemann_energy` — Rusanov LLF on \(F_E=v(E+\kappa p)\), \(E=U/V+\tfrac12\rho v^2\)
- \(\dot U_i=\dot E_i^{\mathrm{flux}}-m_i v_i\dot v_i\) replaces volume-weighted thermalize
- Config `oned_energy_flux` (HLLC momentum + energy flux)

## Milestone 18 — HLLC star energy

- `hllc_energy_flux` with \(E^*_K\), \(p^*\) (Toro); selected when `riemann: hllc` + `riemann_energy`
- Rusanov energy retained for `riemann: rusanov`
- Config `oned_hllc_energy`

## Beyond

- Roe / wave MHD / HLLD
- Particle / Monte Carlo neutrons
- Game-engine (Godot/Unity) / WebGPU volumetric client
- Higher-fidelity nozzle / spacecraft trajectory coupling
