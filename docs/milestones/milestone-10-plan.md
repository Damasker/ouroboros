# Milestone 10 Plan — Energy-consistent reduced MHD

## Goals

1. **Split reduced-MHD forces** into dissipative (Alfvén-like drag → friction ledger) and
   quasi-conservative channels (magnetic pressure, hydrodynamic \(\Delta p\,A\)).
2. **Energy consistency**: magnetic-pressure and \(\Delta p\,A\) work exchanges with plasma
   internal energy (compressional / PdV proxy) so the EnergyLedger residual stays trusted
   with nonzero `magnetic_pressure_scale`.
3. **Demo configs + tests** proving closure with MHD terms enabled.

## Non-goals

- Full MHD / Grad–Shafranov / cell-local vector momentum field
- Real Alfvén-wave propagation
- 3D visualization client (still on the beyond list)

## Classification

All reduced-MHD terms remain **phenomenological / simplified** — not a validated MHD model.
