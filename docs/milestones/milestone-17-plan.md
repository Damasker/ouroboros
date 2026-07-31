# Milestone 17 Plan — Riemann total-energy flux

## Goals

1. **Rusanov energy flux** for cell total energy density
   \(E = U/V + \tfrac12\rho v^2\), face flux \(F_E=v(E+\kappa p)\).
2. Config `oned.riemann_energy: true` (requires `riemann` ≠ `none`).
3. Update cell \(U\) via \(\dot U_i=\dot E_i^{\mathrm{flux}}-m_i v_i\dot v_i\) so the
   ledger stays closed without volume-weighted `numerical_heating_w`.
4. Demo `oned_energy_flux` (HLLC momentum + Rusanov energy).

## Non-goals

- Full HLLC star-region energy states
- Roe solver / wave MHD
- Mass continuity from Riemann (N still uses existing face transport)

## Classification

Simplified Euler-like energy LLF on phenomenological cell masses — not production CFD.

## Done

- `rusanov_energy_flux` in `physics/momentum.py`
- `oned.riemann_energy` wired in `core/oned.py`
- Config `oned_energy_flux` / scenario `oned-energy-flux`
- Integration tests + equations / roadmap / REPORT updates
