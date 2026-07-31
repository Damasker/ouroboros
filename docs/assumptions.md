# Assumptions

Statements are classified so that research honesty is preserved.

## Established physics

- D–T fusion releases 17.6 MeV per reaction, partitioned ≈3.5 MeV (α) + ≈14.1 MeV (n).
- Ideal-gas-like thermal energy scaling \(U \sim \tfrac{3}{2}(n_i T_i + n_e T_e)V\) used as a baseline internal-energy relation (with explicit unit conversion K↔J).
- Inductor energy \(\tfrac{1}{2}LI^2\) for a lumped coil.
- Bosch–Hale reactivity fit for thermal D–T \(\langle\sigma v\rangle\) within its published temperature range.

## Simplified physics

- 0D well-mixed zones (no spatial gradients inside a zone).
- Single ion temperature and single electron temperature per zone.
- Neutrons deposit entirely in a separate blanket energy sink (no scattering back to plasma).
- Linear friction drag on flow.
- Bremsstrahlung formula with effective charge correction, not full atomic physics.
- Constant zone volumes (no MHD equilibrium solver).
- Reduced-MHD-like path forces with compressional kin↔int exchange (Milestone 10) — not wave MHD.

## Phenomenological model

- Effective flow inertia \(M_{\mathrm{eff}}\).
- Mapping from plasma flow to “plasma current” proxy for mutual inductance.
- Magnetic force on flow proportional to throttle current / coupling coefficient.
- Transport confinement time \(\tau_E\) and wall-loss coefficients.
- Recovery fraction of exhaust enthalpy.
- Slow supervisor and PID gains for external actuators.

## Placeholder

- Synthetic heat source profiles used in Scenario 3.
- Placeholder reactivity model (Gaussian-in-temperature demo) when Bosch–Hale is disabled.
- Quench resistance jump magnitude.
- Branch blockage orifice coefficient.

## Speculative concept

- The dual-branch closed plasma loop with passive magnetic throttles as a reactor architecture.
- That passive throttles can autonomously sustain useful oscillatory energy exchange in a real device.
- Any implication of net electricity or propulsion performance from this 0D model.
