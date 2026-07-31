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

## Milestone 13 — Magnetic nozzle / thrust channel

**Status:** complete

Implemented: `physics/nozzle.py` extract→jet/waste split; `EnergyLedger.e_thrust_j`; wired into lumped (chamber proxy), multizone, and 1D expansion cells; config `magnetic_nozzle`; series `thrust_n`, `isp_s`, `jet_power_w`.

Verified: jet+waste = extracted enthalpy; multizone demo energy-trusted with nonzero thrust.

Known issues: coefficients are speculative; not a de Laval / MHD nozzle design tool; no vehicle trajectory.

## Milestone 14 — Upwind momentum flux

**Status:** complete

Implemented: `upwind_momentum_flux` in `physics/momentum.py`; optional on `cell_velocity` via `oned.momentum_flux`; numerical-viscosity heating into cell \(U\); config `oned_momentum_flux`.

Verified: flux KE power ≤0 with heating identity; short 1D run energy-trusted.

Known issues: not HLLC/Roe; uses phenomenological cell masses \(m_i\propto V_i\), not \(\rho\) from particle number.

## Milestone 15 — Rusanov Riemann fluxes

**Status:** complete

Implemented: `rusanov_momentum_flux` with \(F=\rho v^2+\kappa p\); `oned.riemann: rusanov` path that skips `cell_grad_p` / upwind to avoid double-counting; signed kin↔int exchange; config `oned_rusanov`.

Verified: heating identity \(P_U=-\sum m v\dot v\); short 1D run energy-trusted.

Known issues: still Local Lax–Friedrichs only; sound speed uses \(\sqrt{\kappa p/\rho}\) without \(\gamma\); not MHD.

## Milestone 16 — HLLC Riemann fluxes

**Status:** complete

Implemented: `hllc_momentum_flux` with Toro-style \(S_L,S_R,S_M\) on \(F=\rho v^2+\kappa p\); `oned.riemann: hllc` path sharing Rusanov’s skip of `cell_grad_p` / upwind; signed kin↔int exchange; config `oned_hllc`.

Verified: heating identity \(P_U=-\sum m v\dot v\); short 1D run energy-trusted.

Known issues: momentum-only HLLC (no total-energy Riemann); sound speed \(\sqrt{\kappa p/\rho}\) without \(\gamma\); phenomenological cell masses; not MHD HLLD.

## Milestone 17 — Riemann total-energy flux

**Status:** complete

Implemented: `rusanov_energy_flux` for \(E=U/V+\tfrac12\rho v^2\); `oned.riemann_energy` applies \(\dot U=\dot E_{\mathrm{flux}}-m v\dot v\) and skips volume-weighted momentum thermalize; demo `oned_energy_flux`.

Verified: closed-mesh identity \(\sum\dot U+\sum m v\dot v=0\); short 1D run energy-trusted.

Known issues (superseded by M18 for HLLC path): originally Rusanov energy only; mass \(N\) still legacy face transport; not Roe/MHD.

## Milestone 18 — HLLC star energy

**Status:** complete

Implemented: `hllc_energy_flux` with Toro \(S_L,S_R,S_M\), \(p^*\), \(E^*_K\); auto-selected when `riemann: hllc` and `riemann_energy`; config `oned_hllc_energy`.

Verified: closed-mesh identity \(\sum\dot U+\sum m v\dot v=0\); short 1D run energy-trusted.

Known issues: phenomenological masses; sound speed without \(\gamma\); mass \(N\) still legacy face transport; not Roe/HLLD/MHD.

## Milestone 19 — Roe + wave MHD

**Status:** complete

Implemented: `roe_momentum_flux` / `roe_energy_flux`; `oned.riemann: roe`; `oned.wave_mhd` adds \(B^2/2\mu_0\) into Riemann pressures; configs `oned_roe`, `oned_wave_mhd`.

Verified: energy identity; short trusted 1D runs.

Known issues: isothermal-like Roe (not full Euler entropy fix); wave-MHD is pressure augmentation only — not HLLD.

## Milestone 20 — Monte Carlo neutrons

**Status:** complete

Implemented: `mc_neutron_capture_fraction` slab MC; `blanket.transport: mc` overrides capture; config `dt_blanket_mc`.

Verified: deterministic seed; DT blanket MC run energy-trusted.

Known issues: pedagogical slab model — not CAD/transport production neutronics.

## Milestone 21 — WebGPU volumetric viewer

**Status:** complete

Implemented: `viewer/webgpu.html` with WebGPU textured loop volume-slice + canvas fallback; link from `viewer/index.html`.

Verified: asset presence / API hooks in tests.

Known issues: not a native game-engine client; volume is a 2D proxy texture, not true 3D tomography.

## Milestone 22 — Nozzle + spacecraft trajectory

**Status:** complete

Implemented: ideal-expansion blend on nozzle; `spacecraft` section; `integrate_trajectory_series` post-process for \(\Delta v\) / mass / accel; config `nozzle_trajectory`.

Verified: energy identity on nozzle channels; trajectory \(\Delta v\) monotonic; scenario trusted.

Known issues: 1D rocket equation only — not orbital 6DOF.

## Milestone 23 — HLLD proxy

**Status:** complete

Implemented: `hlld_momentum_flux` / `hlld_energy_flux` with fast/Alfvén/contact; `oned.riemann: hlld`; config `oned_hlld`.

Verified: energy identity; short trusted 1D run.

Known issues: phenomenological HLLD — not Miyoshi–Kusano / multi-D MHD.

## Milestone 24 — Multi-layer CAD-proxy neutronics

**Status:** complete

Implemented: `zone_mc_capture` layered ray-march; `blanket.transport: zones` + `layers`; config `dt_blanket_zones`.

Verified: deterministic deposits; DT zones run energy-trusted.

Known issues: not OpenMC/CAD BREP import.

## Milestone 25 — Native client bridge

**Status:** complete

Implemented: `ouroboros.client` protocol, `client_stream.jsonl`, HTTP endpoints, Godot/Unity stubs.

Verified: stream written on run export; stubs present.

Known issues: poll JSON only — not live WebSocket plugin.

## Milestone 26 — Planar 3DOF orbit

**Status:** complete

Implemented: `integrate_orbit3dof_series` with μ/r² + thrust; `spacecraft.orbit_3dof`; config `orbit_3dof`.

Verified: finite LEO radius; scenario energy-trusted.

Known issues: planar 3DOF only — no attitude / 6DOF.
