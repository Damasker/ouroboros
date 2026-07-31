# Milestone 14 Plan — Upwind momentum flux (1D cell_velocity)

## Goals

1. **Momentum advection** — upwind face flux of \(\rho v\) for `cell_velocity` mode
   (\(\Phi = u A \rho_{\mathrm{up}} v_{\mathrm{up}}\)).
2. **Energy closure** — thermalize kinetic dissipation from upwinding into cell \(U\)
   when `thermalize_momentum_flux: true` (default).
3. Config `oned_momentum_flux` + tests.

## Non-goals

- Full HLLC / Roe Riemann solvers
- Wave MHD / Alfvén propagation
- Changing dual_path / cell_pressure modes

## Classification

Simplified FV momentum advection with optional numerical-viscosity heating — not a shock-capturing MHD code.
