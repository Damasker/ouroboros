# Milestone 18 Plan — HLLC star-region energy flux

## Goals

1. **HLLC energy flux** with Toro star states \(E^*_K\), \(p^*\) matching momentum waves.
2. When `oned.riemann: hllc` and `riemann_energy: true`, use HLLC energy (Rusanov energy remains for `riemann: rusanov`).
3. Same \(\dot U=\dot E_{\mathrm{flux}}-m v\dot v\) ledger closure as M17.
4. Demo `oned_hllc_energy`.

## Non-goals

- Roe linearization / entropy fixes
- Wave MHD / HLLD
- Mass continuity from the same Riemann solve

## Classification

Simplified HLLC energy on phenomenological cell masses — not production Euler/MHD.

## Done

- `hllc_energy_flux` in `physics/momentum.py`
- Auto-select in `core/oned.py` when `riemann: hllc` + `riemann_energy`
- Config `oned_hllc_energy` / scenario `oned-hllc-energy`
- Integration tests + equations / roadmap / REPORT updates
