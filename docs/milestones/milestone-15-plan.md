# Milestone 15 Plan — Rusanov Riemann momentum+pressure fluxes

## Goals

1. **Rusanov (Local Lax–Friedrichs)** face fluxes for momentum including scaled pressure:
   \(\Phi=\tfrac12 A[(F_L+F_R)-S(\rho v_R-\rho v_L)]\), \(F=\rho v^2+\kappa p\).
2. When `oned.riemann: rusanov`, **replace** separate `cell_grad_p` + optional upwind
   momentum flux to avoid double-counting pressure.
3. **Energy exchange**: \(\Delta U=-\sum m_i v_i\dot v_i^{\mathrm{flux}}\) so kin+int stay closed
   for the flux channel.
4. Config `oned_rusanov` + tests.

## Non-goals

- Full HLLC / Roe / characteristic MHD
- Wave propagation validation against analytic MHD

## Classification

Simplified FV Rusanov on phenomenological cell masses — not a production Riemann MHD solver.
