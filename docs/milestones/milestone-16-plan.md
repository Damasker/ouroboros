# Milestone 16 Plan — HLLC Riemann momentum+pressure fluxes

## Goals

1. **HLLC** face fluxes for momentum with contact wave \(S_M\) (Toro-style, isothermal-like
   sound speed \(c\sim\sqrt{\kappa p/\rho}\)).
2. Config `oned.riemann: hllc` alongside `rusanov` / `none`.
3. Same kin↔int energy exchange as Rusanov; demo `oned_hllc`.

## Non-goals

- Full Euler energy equation / HLLC for total energy
- MHD HLLD
- Characteristic limiting / high-order reconstruction

## Classification

Simplified HLLC on phenomenological cell masses — research prototype, not a production CFD solver.

## Done

- `hllc_momentum_flux` in `physics/momentum.py`
- `oned.riemann: hllc` wired in `core/oned.py`
- Config `oned_hllc` / scenario `oned-hllc`
- Integration tests + equations / roadmap / REPORT updates
