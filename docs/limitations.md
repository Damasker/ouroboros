# Limitations

1. **Not a reactor design tool.** Results must not be interpreted as evidence of engineering feasibility.
2. **0D / multi-zone 0D only.** No 1D advection PDE yet, no MHD stability, no turbulence cascade, no realistic divertor physics. Multi-zone exchange uses phenomenological \(|v|/L\) rates.
3. **Phenomenological throttles.** Mutual inductance coupling to flow is a research toy model.
4. **Fixed geometry volumes.** Compression work terms are simplified or optional.
5. **Single reactivity channel (D–T).** No D–D, T–T, or advanced fuels in v1.
6. **Neutron blanket is an energy bin**, not a transport/activation calculation.
7. **No radiation transport**, no neutrals, no sheath model.
8. **Controllers are academic** (PID / slow supervisor), not plant-grade control.
9. **Numerical residuals** can appear from adaptive stepping and discrete event handling; they are measured, not hidden.
10. **Cross-platform bitwise reproducibility** is not guaranteed due to BLAS/SciPy differences.
11. **3D visualization** consumes snapshots only; it does not validate the physics.
12. **Space-propulsion / magnetic nozzle** configuration is explicitly out of scope for v1.
